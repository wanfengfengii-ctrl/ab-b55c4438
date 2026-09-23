"""求解器单元测试 + 与暴力枚举对照的随机性质测试。"""
from __future__ import annotations

import itertools
import random

from app.solver import EventSpec, solve_replay


def ev(id, device, seq, observed, lo, hi):
    return EventSpec(id=id, device=device, seq=seq, observed=observed, lo=lo, hi=hi)


def brute_force(events, precedences):
    """返回 (最优代价|None, 全部最优排列按编号序列字母序排序)。"""
    n = len(events)
    index = {e.id: i for i, e in enumerate(events)}
    best_cost = None
    best: list[tuple[str, ...]] = []
    for perm in itertools.permutations(range(n)):
        pos = [0] * n
        for p, x in enumerate(perm, 1):
            pos[x] = p
        ok = True
        for x in range(n):
            e = events[x]
            if not (e.lo <= pos[x] <= e.hi):
                ok = False
                break
        if not ok:
            continue
        for i in range(n):
            for j in range(n):
                if (
                    events[i].device == events[j].device
                    and events[i].seq < events[j].seq
                    and pos[i] > pos[j]
                ):
                    ok = False
        for b, a in precedences:
            if pos[index[b]] > pos[index[a]]:
                ok = False
        if not ok:
            continue
        cost = sum(abs(pos[x] - events[x].observed) for x in range(n))
        order = tuple(events[x].id for x in perm)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best = [order]
        elif cost == best_cost:
            best.append(order)
    best.sort()
    return best_cost, best


def test_unique_optimum():
    events = [
        ev("A", "M1", 1, 1, 1, 2),
        ev("B", "M1", 2, 2, 1, 4),
        ev("C", "M2", 1, 3, 2, 4),
        ev("D", "M2", 2, 4, 3, 4),
    ]
    res = solve_replay(events, [])
    assert res["status"] == "unique"
    assert res["cost"] == 0
    assert res["timelines"] == [{"order": ["A", "B", "C", "D"]}]


def test_multiple_optima_two_lexicographic_witnesses():
    events = [
        ev("A", "M1", 1, 1, 1, 4),
        ev("B", "M1", 2, 2, 1, 4),
        ev("C", "M2", 1, 1, 1, 4),
        ev("D", "M2", 2, 2, 1, 4),
    ]
    res = solve_replay(events, [])
    assert res["status"] == "multiple"
    assert res["cost"] == 4
    assert [t["order"] for t in res["timelines"]] == [
        ["A", "B", "C", "D"],
        ["A", "C", "B", "D"],
    ]


def test_device_order_follows_seq_not_input_order():
    events = [
        ev("X", "M1", 2, 1, 1, 4),
        ev("Y", "M1", 1, 2, 1, 4),
        ev("P", "M2", 1, 3, 1, 4),
        ev("Q", "M2", 2, 4, 1, 4),
    ]
    res = solve_replay(events, [])
    assert res["status"] == "unique"
    assert res["cost"] == 2
    assert res["timelines"][0]["order"] == ["Y", "X", "P", "Q"]


def test_explicit_precedence_respected():
    events = [
        ev("A", "M1", 1, 1, 1, 4),
        ev("B", "M2", 1, 2, 1, 4),
        ev("C", "M3", 1, 3, 1, 4),
        ev("D", "M4", 1, 4, 1, 4),
    ]
    res = solve_replay(events, [("B", "A")])  # B 必须在 A 前，与观测位次冲突
    assert res["status"] == "unique"
    assert res["timelines"][0]["order"] == ["B", "A", "C", "D"]
    assert res["cost"] == 2


def test_cycle_is_infeasible():
    events = [
        ev("A", "M1", 1, 1, 1, 4),
        ev("B", "M2", 1, 2, 1, 4),
        ev("C", "M3", 1, 3, 1, 4),
        ev("D", "M4", 1, 4, 1, 4),
    ]
    res = solve_replay(events, [("A", "B"), ("B", "A")])
    assert res == {"status": "infeasible", "timelines": []}


def test_mutually_exclusive_windows_are_infeasible():
    events = [
        ev("A", "M1", 1, 1, 1, 1),
        ev("B", "M2", 1, 2, 1, 1),
        ev("C", "M3", 1, 3, 1, 4),
        ev("D", "M4", 1, 4, 1, 4),
    ]
    res = solve_replay(events, [])
    assert res["status"] == "infeasible"


def test_random_against_brute_force():
    rng = random.Random(20260923)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for trial in range(150):
        n = rng.randint(4, 7) if trial < 130 else 8
        ids = rng.sample(letters, n)
        devices = [f"M{d}" for d in range(1, rng.randint(2, 4))]
        assigned = rng.sample(devices * n, n)[:n]
        seq_counters: dict[str, list[int]] = {d: [] for d in devices}
        events = []
        for i in range(n):
            dev = assigned[i]
            pool = seq_counters[dev]
            seq = 1
            while seq in pool:
                seq += 1
            pool.append(seq)
            lo = rng.randint(1, n)
            hi = rng.randint(lo, n)
            events.append(ev(ids[i], dev, seq, rng.randint(1, 20), lo, hi))
        precs = set()
        for _ in range(rng.randint(0, n)):
            a, b = rng.sample(ids, 2)
            precs.add((a, b))
        precs = list(precs)

        res = solve_replay(events, precs)
        cost, orders = brute_force(events, precs)
        if cost is None:
            assert res["status"] == "infeasible", (events, precs, res)
            continue
        assert res["cost"] == cost, (events, precs, res, cost)
        expected_status = "unique" if len(orders) == 1 else "multiple"
        assert res["status"] == expected_status, (events, precs, res, orders)
        got = [tuple(t["order"]) for t in res["timelines"]]
        assert got == orders[:2], (events, precs, res, orders[:2])
