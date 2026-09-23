# 停机回放工作台 (Replay Workbench)

停机前最后一轮记录散落在多台控制器中:每台控制器内部事件顺序可靠,混在一起
却不能直接用于产线回放。本工作台用于编辑事件与显式先后关系,由业务 API 重建
最优回放排列,并在页面上逐条核对约束与代价。

## 问题定义

每轮包含 **4–20 个事件**,每个事件:

- 编号:互不相同的单个大写英文字母 `A–Z`;
- 设备 + 设备内序号(正整数,同设备内不得重复);
- 观测位次 `observedRank` ∈ [1, 20];
- 允许的最终位置闭区间 `[windowLow, windowHigh]`,端点 ∈ [1, 事件数]。

另有若干显式先后关系 `before → after`,不得自环、不得重复。

**回放**是全部事件的一个排列(位置从 1 起算),满足:

1. 同设备事件按设备内序号升序出现;
2. 满足全部显式先后关系;
3. 每个事件位于自己的位置闭区间内。

唯一优化目标:

```
最小化  Σ |事件实际位置 − 观测位次|
```

业务 API 返回:

- **无解**(`infeasible`,并区分 `cycle` 成环 / `window` 窗口互斥两类原因);
- **唯一最优**(`unique`)及最优代价;
- **多最优**(`multiple`)及最优代价,并按"事件编号序列字母序"给出最小的
  两份见证,页面可在两条时间线之间切换;
- **输入错误**(`invalid_input`):格式、编号引用、区间越界等错误均定位到
  具体表格行与字段。

## 目录结构

```
backend/          FastAPI + OR-Tools CP-SAT 业务 API
  app/
    models.py       请求/响应模型
    validation.py   精确定位的输入校验
    solver.py       排列 CP 模型 + 最优代价 + 字典序两份见证
    main.py         /api/solve、/health
  tests/            pytest(含 120 组随机实例对拍暴力枚举)
frontend/         React + TypeScript + Vite
  src/
    App.tsx                 编辑器(输入一改即清除旧结果)
    verifier.ts             页面侧独立复核每条约束与代价
    components/ResultPanel  无解/唯一/多最优展示与时间线切换
verify/           一次性验证服务(测试 + 构建 + 在线冒烟)
docker-compose.yml
```

## 一键启动

```bash
docker compose up -d --build
```

- 前端: http://localhost:8080
- 后端: http://localhost:8000 (健康检查 `GET /health`)

### 宿主机端口配置

复制 `.env.example` 为 `.env` 后修改,或直接带环境变量:

```bash
BACKEND_PORT=18000 FRONTEND_PORT=18080 docker compose up -d
```

两个容器均定义了健康检查;`frontend` 会等待 `backend` 健康后再启动。

## 一次性验证服务 verify

verify 是 **one-shot** 服务:启动后顺序执行后端测试 → 前端生产构建 → 在线
API 冒烟,随后自行退出,以容器退出码表示成败(0 成功,非 0 失败):

```bash
docker compose --profile verify build verify
docker compose --profile verify run --rm verify
echo "exit code = $?"
docker compose down          # 停止为冒烟而启动的 backend
```

冒烟覆盖:健康检查、唯一最优(代价 0)、多最优 + 字母序两份见证、
成环无解(`cycle`)、窗口互斥无解(`window`)、区间越界错误定位到单元格。

## 本地开发(不使用 Docker)

后端:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q
```

前端:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173,/api 代理到 http://localhost:8000
npm run build
```

## 求解器要点

- 布尔变量 `p[i][k]` 表示事件 `i` 占据 0 位次 `k`,两组 ExactlyOne 保证是排列;
  窗口外位置直接固定为 0;`pos[i] = 1 + Σ k·p[i][k]`。
- 设备序号链与显式边均表示为严格位置不等式;代价用 `AddAbsEquality` 线性化。
- 最优代价确定后,把事件编号字母序编码为 (n+1) 进制整数(分两段,避开
  int64 溢出),在"代价等于最优值"的可行解中分别求最小、次小两份见证;
  次小不存在即唯一最优。
