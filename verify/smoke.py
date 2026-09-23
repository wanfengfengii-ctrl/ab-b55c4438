"""Live API smoke checks run by the one-shot verify service."""
from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("BACKEND_URL", "http://backend:8000")
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not cond:
        failures.append(name)


def event(ev_id, **kw):
    base = {
        "id": ev_id,
        "device": f"dev-{ev_id}",
        "serial": 1,
        "observedRank": 1,
        "windowLow": 1,
        "windowHigh": 4,
    }
    base.update(kw)
    return base


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=30.0)

    r = client.get("/health")
    check("health 200", r.status_code == 200 and r.json().get("status") == "ok")

    # Unique optimum, zero cost: observed order is achievable as-is.
    r = client.post(
        "/api/solve",
        json={
            "events": [
                event("A", observedRank=1),
                event("B", observedRank=2),
                event("C", observedRank=3),
                event("D", observedRank=4),
            ],
            "orderings": [],
        },
    )
    body = r.json()
    check(
        "unique optimum cost 0",
        r.status_code == 200
        and body["status"] == "unique"
        and body["optimalCost"] == 0
        and body["witnesses"][0]["timeline"] == ["A", "B", "C", "D"],
        str(body),
    )

    # Two optima: A/B tie on observed rank 1.
    r = client.post(
        "/api/solve",
        json={
            "events": [
                event("A", observedRank=1),
                event("B", observedRank=1),
                event("C", observedRank=3),
                event("D", observedRank=4),
            ],
            "orderings": [],
        },
    )
    body = r.json()
    wits = [w["timeline"] for w in body.get("witnesses", [])]
    check(
        "multiple optima + lex witnesses",
        body["status"] == "multiple"
        and body["optimalCost"] == 1
        and wits == [["A", "B", "C", "D"], ["B", "A", "C", "D"]],
        str(body),
    )

    # Cyclic explicit ordering -> infeasible, reason cycle.
    r = client.post(
        "/api/solve",
        json={
            "events": [event(c, observedRank=i + 1) for i, c in enumerate("ABCD")],
            "orderings": [
                {"before": "A", "after": "B"},
                {"before": "B", "after": "C"},
                {"before": "C", "after": "A"},
            ],
        },
    )
    body = r.json()
    check(
        "cycle infeasible",
        body["status"] == "infeasible" and body.get("reason") == "cycle",
        str(body),
    )

    # Window mutex -> infeasible, reason window.
    r = client.post(
        "/api/solve",
        json={
            "events": [
                event("A", windowLow=1, windowHigh=1),
                event("B", windowLow=1, windowHigh=1),
                event("C", observedRank=3, windowLow=2, windowHigh=4),
                event("D", observedRank=4, windowLow=2, windowHigh=4),
            ],
            "orderings": [],
        },
    )
    body = r.json()
    check(
        "window mutex infeasible",
        body["status"] == "infeasible" and body.get("reason") == "window",
        str(body),
    )

    # Located input error: window high above event count.
    r = client.post(
        "/api/solve",
        json={
            "events": [
                event("A", windowHigh=9),
                event("B"),
                event("C"),
                event("D"),
            ],
            "orderings": [],
        },
    )
    body = r.json()
    located = any(
        e["code"] == "event.window.out_of_bounds"
        and e["path"] == ["events", "0", "windowHigh"]
        for e in body.get("errors", [])
    )
    check("window error located to cell", body["status"] == "invalid_input" and located, str(body))

    if failures:
        print(f"\nSMOKE FAILED: {len(failures)} check(s): {failures}")
        return 1
    print("\nSMOKE OK: all live API checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print(f"SMOKE FAILED: cannot reach API at {BASE}: {exc}")
        sys.exit(1)
