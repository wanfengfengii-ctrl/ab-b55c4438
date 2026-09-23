"""API 冒烟测试：对运行中的后端执行健康检查与求解校验，失败以非零码退出。"""
from __future__ import annotations

import os
import sys
import time

import httpx

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def wait_for_health(timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/api/health", timeout=3)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1.5)
    return False


def post(payload: dict) -> httpx.Response:
    return httpx.post(f"{BASE}/api/solve", json=payload, timeout=30)


def ev(i, d, s, o, lo, hi):
    return {"id": i, "device": d, "seq": s, "observed": o, "window": {"lo": lo, "hi": hi}}


def verify_consistency(payload: dict, order: list[str], cost: int) -> bool:
    """客户端视角复核：位置、窗口、设备序、显式先后、总代价。"""
    pos = {eid: p + 1 for p, eid in enumerate(order)}
    if sorted(pos) != sorted(e["id"] for e in payload["events"]):
        return False
    total = 0
    for e in payload["events"]:
        p = pos[e["id"]]
        if not (e["window"]["lo"] <= p <= e["window"]["hi"]):
            return False
        total += abs(p - e["observed"])
    if total != cost:
        return False
    by_dev: dict[str, list[dict]] = {}
    for e in payload["events"]:
        by_dev.setdefault(e["device"], []).append(e)
    for members in by_dev.values():
        members.sort(key=lambda e: e["seq"])
        for a, b in zip(members, members[1:]):
            if pos[a["id"]] >= pos[b["id"]]:
                return False
    for pre in payload.get("precedences", []):
        if pos[pre["before"]] >= pos[pre["after"]]:
            return False
    return True


def main() -> int:
    print(f"目标后端: {BASE}")
    check("健康检查 /api/health", wait_for_health(), "后端在 60s 内未就绪")

    # 1) 多最优：代价与两份见证均已知
    multi = {
        "events": [
            ev("A", "M1", 1, 1, 1, 4),
            ev("B", "M1", 2, 2, 1, 4),
            ev("C", "M2", 1, 1, 1, 4),
            ev("D", "M2", 2, 2, 1, 4),
        ],
        "precedences": [],
    }
    r = post(multi)
    ok = r.status_code == 200
    check("多最优用例 HTTP 200", ok, f"got {r.status_code}: {r.text[:200]}")
    if ok:
        body = r.json()
        check("多最优 status", body.get("status") == "multiple", str(body))
        check("多最优 cost == 4", body.get("cost") == 4, str(body))
        orders = [t.get("order") for t in body.get("timelines", [])]
        check(
            "多最优见证为字母序最小两份",
            orders == [["A", "B", "C", "D"], ["A", "C", "B", "D"]],
            str(orders),
        )

    # 2) 先后成环 → 无解
    cyc = {
        "events": [
            ev("A", "M1", 1, 1, 1, 4),
            ev("B", "M2", 1, 2, 1, 4),
            ev("C", "M3", 1, 3, 1, 4),
            ev("D", "M4", 1, 4, 1, 4),
        ],
        "precedences": [
            {"before": "A", "after": "B"},
            {"before": "B", "after": "A"},
        ],
    }
    r = post(cyc)
    check(
        "成环返回 infeasible",
        r.status_code == 200 and r.json().get("status") == "infeasible",
        f"{r.status_code} {r.text[:200]}",
    )

    # 3) 校验错误定位：观测位次越界 → 422 且 loc 指向具体输入
    bad = {
        "events": [
            ev("A", "M1", 1, 1, 1, 4),
            ev("B", "M1", 2, 2, 1, 4),
            ev("C", "M2", 1, 21, 1, 4),
            ev("D", "M2", 2, 4, 1, 4),
        ],
        "precedences": [{"before": "A", "after": "ZZ"}],
    }
    r = post(bad)
    locs = []
    if r.status_code == 422:
        locs = [e.get("loc", "") for e in r.json().get("detail", [])]
    check("非法输入返回 422", r.status_code == 422, f"got {r.status_code}")
    check(
        "错误定位到具体输入",
        "events[2].observed" in locs and "precedences[0].after" in locs,
        f"locs={locs}",
    )

    # 4) 较大实例：结果自洽性复核
    big = {
        "events": [
            ev("A", "炉1", 1, 2, 1, 4),
            ev("B", "炉1", 2, 6, 3, 7),
            ev("C", "炉2", 1, 1, 1, 3),
            ev("D", "炉2", 2, 6, 4, 8),
            ev("E", "机3", 1, 4, 2, 6),
            ev("F", "机3", 2, 7, 5, 8),
            ev("G", "机4", 1, 3, 1, 5),
            ev("H", "机4", 2, 8, 6, 7),
        ],
        "precedences": [{"before": "C", "after": "E"}],
    }
    r = post(big)
    ok = r.status_code == 200 and r.json().get("status") in ("unique", "multiple")
    check("8 事件实例可解", ok, f"{r.status_code} {r.text[:200]}")
    if ok:
        body = r.json()
        for t in body["timelines"]:
            check(
                "见证自洽（窗口/设备序/先后/代价）",
                verify_consistency(big, t["order"], body["cost"]),
                str(t),
            )

    if FAILURES:
        print(f"\n冒烟失败 {len(FAILURES)} 项: {FAILURES}")
        return 1
    print("\n冒烟全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
