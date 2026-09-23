"""产线回放求解器。

给定 4..20 个事件（各自带设备、设备内序号、观测位次、位置闭区间）以及显式先后
关系，求满足以下全部约束的排列（回放）：

  * 同设备事件按设备内序号升序排列；
  * 所有显式先后关系（before 在 after 之前）；
  * 每个事件的实际位置落在其闭区间 [lo, hi] 内（位置从 1 起算）。

目标：最小化 sum(|实际位置 - 观测位次|)。

实现：按位置分层的事件子集 DP（n <= 20，2^n 状态，numpy 向量化）。
  dp[S]  = 恰好把集合 S 安排在位置 1..|S| 的最小代价
  cnt[S] = 取得 dp[S] 的方案数（封顶 2，用于区分唯一/多最优）
  g[S]   = 在 S 已占位置 1..|S| 后，完成剩余事件的最小追加代价（用于见证提取）
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

INF = 1 << 30
CAP = 2  # 方案数封顶：只需区分 1 与 >1


@dataclass(frozen=True)
class EventSpec:
    id: str
    device: str
    seq: int
    observed: int
    lo: int
    hi: int


@lru_cache(maxsize=4)
def _bit_layers(n: int) -> tuple[tuple[np.ndarray, ...], ...]:
    """bit_layers[k][x] = 大小为 k 且包含事件 x 的掩码数组（int32）。

    同层不同 x 的掩码互不相交；后缀 DP 复用同一结构（异或去位即得补集侧）。
    """
    size = 1 << n
    idx = np.arange(size, dtype=np.int32)
    pc = np.zeros(size, dtype=np.int32)
    for b in range(n):
        pc += (idx >> b) & 1
    layers: list[tuple[np.ndarray, ...]] = []
    for k in range(n + 1):
        layer = idx[pc == k]
        layers.append(
            tuple(layer[((layer >> x) & 1) != 0].astype(np.int32) for x in range(n))
        )
    return tuple(layers)


def _forward(n, preds, los, his, obs, bit_layers):
    """前缀 DP：dp[S] 最小代价，cnt[S] 最优方案数（封顶 CAP）。"""
    size = 1 << n
    dp = np.full(size, INF, dtype=np.int64)
    cnt = np.zeros(size, dtype=np.int64)
    dp[0] = 0
    cnt[0] = 1
    for k in range(1, n + 1):
        for x in range(n):
            if not (los[x] <= k <= his[x]):
                continue
            dst = bit_layers[k][x]
            pm = preds[x]
            if pm:
                dst = dst[(dst & pm) == pm]
                if dst.size == 0:
                    continue
            src = dst ^ (1 << x)
            cand = dp[src] + abs(k - obs[x])
            cur = dp[dst]
            better = cand < cur
            equal = cand == cur
            if not (better.any() or equal.any()):
                continue
            csrc = cnt[src]
            newcnt = np.where(better, csrc, cnt[dst])
            newcnt = np.where(equal, newcnt + csrc, newcnt)
            np.minimum(newcnt, CAP, out=newcnt)
            dp[dst] = np.where(better, cand, cur)
            cnt[dst] = newcnt
    return dp, cnt


def _backward(n, preds, los, his, obs, bit_layers):
    """后缀 DP：g[S] = 在 S 之后完成全部剩余事件的最小追加代价。"""
    size = 1 << n
    g = np.full(size, INF, dtype=np.int64)
    g[size - 1] = 0
    for k in range(n - 1, -1, -1):
        p = k + 1
        for x in range(n):
            if not (los[x] <= p <= his[x]):
                continue
            src = bit_layers[k + 1][x]  # 层 k+1 含 x
            dst = src ^ (1 << x)  # 层 k 不含 x
            pm = preds[x]
            if pm:
                m = (dst & pm) == pm
                src = src[m]
                dst = dst[m]
                if dst.size == 0:
                    continue
            cand = g[src] + abs(p - obs[x])
            cur = g[dst]
            better = cand < cur
            if not better.any():
                continue
            g[dst] = np.where(better, cand, cur)
    return g


def _complete(n, by_letter, preds, los, his, obs, g, opt, state, cost, pos):
    """从 (state, cost, pos) 出发，贪心地取字典序最小且仍可达成最优的事件。"""
    order = []
    for p in range(pos, n + 1):
        for x in by_letter:
            bit = 1 << x
            if state & bit:
                continue
            if not (los[x] <= p <= his[x]):
                continue
            if (state & preds[x]) != preds[x]:
                continue
            c = abs(p - obs[x])
            if cost + c + int(g[state | bit]) == opt:
                order.append(x)
                state |= bit
                cost += c
                break
        else:  # pragma: no cover - 最优解存在时必然能续上
            raise RuntimeError("无法构造最优见证")
    return order


def _witnesses(n, ids, preds, los, his, obs, g, opt, count):
    """返回按事件编号序列字母序最小的 1~2 份最优见证（事件下标序列）。"""
    by_letter = sorted(range(n), key=lambda i: ids[i])
    w1 = _complete(n, by_letter, preds, los, his, obs, g, opt, 0, 0, 1)
    if count < 2:
        return [w1]

    # 第二小：在 w1 上找最迟的可偏离位置，取该处字母序最小的更大候选，再贪心续完。
    prefix_state = [0] * (n + 1)
    prefix_cost = [0] * (n + 1)
    for p in range(1, n + 1):
        x = w1[p - 1]
        prefix_state[p] = prefix_state[p - 1] | (1 << x)
        prefix_cost[p] = prefix_cost[p - 1] + abs(p - obs[x])
    for p in range(n, 0, -1):
        state = prefix_state[p - 1]
        cost = prefix_cost[p - 1]
        cur = w1[p - 1]
        for x in by_letter:
            if ids[x] <= ids[cur]:
                continue
            bit = 1 << x
            if state & bit:
                continue
            if not (los[x] <= p <= his[x]):
                continue
            if (state & preds[x]) != preds[x]:
                continue
            c = abs(p - obs[x])
            if cost + c + int(g[state | bit]) == opt:
                rest = _complete(
                    n, by_letter, preds, los, his, obs, g, opt,
                    state | bit, cost + c, p + 1,
                )
                return [w1, w1[: p - 1] + [x] + rest]
    return [w1]  # pragma: no cover - count>=2 时必然存在第二见证


def solve_replay(events: list[EventSpec], precedences: list[tuple[str, str]]) -> dict:
    """求解一轮回放。输入须已通过 validation 校验。"""
    n = len(events)
    ids = [e.id for e in events]
    index = {eid: i for i, eid in enumerate(ids)}
    los = [e.lo for e in events]
    his = [e.hi for e in events]
    obs = [e.observed for e in events]

    preds = [0] * n
    # 同设备按设备内序号排序 → 隐式先后链
    by_device: dict[str, list[int]] = {}
    for i, e in enumerate(events):
        by_device.setdefault(e.device, []).append(i)
    for members in by_device.values():
        members.sort(key=lambda i: events[i].seq)
        for a, b in zip(members, members[1:]):
            preds[b] |= 1 << a
    # 显式先后关系
    for before, after in precedences:
        preds[index[after]] |= 1 << index[before]

    bit_layers = _bit_layers(n)
    dp, cnt = _forward(n, preds, los, his, obs, bit_layers)
    full = (1 << n) - 1
    opt = int(dp[full])
    if opt >= INF:
        return {"status": "infeasible", "timelines": []}

    g = _backward(n, preds, los, his, obs, bit_layers)
    count = int(cnt[full])
    witnesses = _witnesses(n, ids, preds, los, his, obs, g, opt, count)
    return {
        "status": "unique" if count == 1 else "multiple",
        "cost": opt,
        "timelines": [{"order": [ids[x] for x in w]} for w in witnesses],
    }
