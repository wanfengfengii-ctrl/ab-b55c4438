# 产线回放工作台

停机前最后一轮记录散落在多台控制器里：各机（设备）内部顺序可靠，混在一起却不能直接作为
产线回放。本工作台允许编辑事件与显式先后关系，由业务 API 重建最优回放，页面逐条核对约束
与代价；多最优时可切换时间线，输入一改动便清除旧结果。

## 问题定义

一轮包含 **4–20 个事件**，每个事件给出：

| 字段 | 含义 | 约束 |
| --- | --- | --- |
| `id` | 事件编号 | 不同的单个大写英文字母（A–Z） |
| `device` | 设备 | 非空字符串 |
| `seq` | 设备内序号 | 正整数；同设备内不得重复 |
| `observed` | 观测位次 | 1–20 的整数 |
| `window` | 位置闭区间 `[lo, hi]` | `1 ≤ lo ≤ hi ≤ 事件数` |

外加若干**显式先后关系**（`before` 先于 `after`，不得自环、不得重复）。

**回放**是所有事件的一个排列（位置从 1 起算），须满足：

1. 同设备事件按设备内序号升序排列；
2. 全部显式先后关系；
3. 每个事件的实际位置落在其闭区间内。

目标（唯一）：最小化 `Σ|实际位置 − 观测位次|`。

求解结果有三种：

- **无解**（`infeasible`）：先后关系成环、窗口互斥等；
- **唯一最优**（`unique`）：返回最优代价与时间线；
- **多最优**（`multiple`）：返回最优代价，并按事件编号序列字母序给出最小的两份见证。

格式、编号引用、区间越界等输入错误以 422 返回，并定位到具体输入
（如 `events[2].observed`、`precedences[0].after`）。

## 目录结构

```
backend/            FastAPI 后端（求解器：子集 DP，numpy 向量化）
  app/solver.py       回放求解（最优代价、唯一/多最优、字典序最小两份见证）
  app/validation.py   输入校验（错误定位到具体输入）
  app/main.py         路由：GET /api/health，POST /api/solve
  tests/              pytest：单元测试 + 与暴力枚举对照的随机性质测试
frontend/           React + TypeScript（Vite）
  src/checks.ts       页面侧逐条核对逻辑（窗口/设备序/先后/代价）
  src/components/     事件编辑器、先后关系编辑器、结果面板
verify/             一次性验收服务（测试 + 构建 + API 冒烟，退出码表成败）
docker-compose.yml  前后端 + verify 编排，端口可配，含健康检查
```

## 快速开始（Docker Compose）

```bash
# 构建并启动前后端（前台）
docker compose up --build

# 或后台启动
docker compose up --build -d
```

- 前端：<http://localhost:8080>（nginx 托管静态页并反代 `/api` 到后端）
- 后端：<http://localhost:8000/api/health>

**宿主机端口配置**（环境变量，均有默认值）：

```bash
FRONTEND_PORT=9000 BACKEND_PORT=9001 docker compose up --build -d
```

**健康检查**：后端 `GET /api/health`、前端 `GET /healthz`，均已在 Dockerfile 与
compose 中配置；`frontend`、`verify` 通过 `depends_on: service_healthy` 等待后端就绪。

## 一次性验收（verify）

`verify` 服务依次执行：后端 pytest、前端单元测试与生产构建（镜像构建阶段）、
对运行中后端的 API 冒烟，随后**自行退出**，以退出码表示成败：

```bash
docker compose up --build --exit-code-from verify verify
echo $?   # 0 = 全部通过，非 0 = 失败
```

## 本地开发

```bash
# 后端
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd backend && ../.venv/bin/pytest -q            # 测试
../.venv/bin/uvicorn app.main:app --reload      # 服务（:8000）

# 前端
cd frontend && npm ci
npm test          # vitest 单元测试
npm run build     # tsc 类型检查 + 生产构建
npm run dev       # 开发服务器（:5173，/api 代理到 :8000）
```

## API

### `POST /api/solve`

请求：

```json
{
  "events": [
    {"id": "A", "device": "M1", "seq": 1, "observed": 1, "window": {"lo": 1, "hi": 4}}
  ],
  "precedences": [{"before": "C", "after": "E"}]
}
```

响应（200）：

```json
// 无解
{"status": "infeasible", "timelines": []}
// 唯一最优 / 多最优（多最优时 timelines 为字母序最小的两份见证）
{"status": "unique",   "cost": 0, "timelines": [{"order": ["A", "B", "C", "D"]}]}
{"status": "multiple", "cost": 4, "timelines": [{"order": [...]}, {"order": [...]}]}
```

输入错误（422），`loc` 定位到具体输入：

```json
{"detail": [{"loc": "events[2].observed", "msg": "观测位次须为 1..20 的整数"}]}
```

## 求解方法

事件数 `n ≤ 20`，按位置分层做事件子集 DP（numpy 向量化，2ⁿ 状态）：

- `dp[S]`：恰好把集合 S 安排在位置 1..|S| 的最小代价，同时统计最优方案数（封顶 2，
  用于区分唯一/多最优）；同设备序号链与显式先后关系统一为前驱掩码；
- `g[S]`：后缀 DP，用于在 `O(n²)` 内贪心地取出字典序最小的最优见证，以及在
  最晚可偏离位置构造第二小见证；
- 成环或窗口互斥时 `dp[全集]` 不可达，即判无解。

n = 20 全窗口最坏情况约 0.5s。
