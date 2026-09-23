"""Pytest suite: validation, solver semantics and API smoke tests."""
from __future__ import annotations

import itertools
import random
from collections import defaultdict

from fastapi.testclient import TestClient

from app.main import app
from app.models import EventIn, OrderingIn, SolveRequest
from app.solver import solve
from app.validation import validate_request

client = TestClient(app)


def ev(ev_id, device, serial, rank, low, high) -> EventIn:
    return EventIn(
        id=ev_id,
        device=device,
        serial=serial,
        observedRank=rank,
        windowLow=low,
        windowHigh=high,
    )


# --------------------------------------------------------------------------
# Hand-built scenarios
# --------------------------------------------------------------------------

def test_zero_cost_unique():
    req = SolveRequest(
        events=[
            ev("A", "d1", 1, 1, 1, 4),
            ev("B", "d2", 1, 2, 1, 4),
            ev("C", "d3", 1, 3, 1, 4),
            ev("D", "d4", 1, 4, 1, 4),
        ]
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, cost, witnesses, reason = solve(by_id, req.orderings)
    assert status == "unique"
    assert cost == 0
    assert witnesses == [["A", "B", "C", "D"]]


def test_two_optima_tied_observed_ranks():
    # A and B both observed at rank 1; they can swap positions 1/2 for cost 1.
    req = SolveRequest(
        events=[
            ev("A", "d1", 1, 1, 1, 4),
            ev("B", "d2", 1, 1, 1, 4),
            ev("C", "d3", 1, 3, 1, 4),
            ev("D", "d4", 1, 4, 1, 4),
        ]
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, cost, witnesses, reason = solve(by_id, req.orderings)
    assert status == "multiple"
    assert cost == 1
    assert witnesses == [["A", "B", "C", "D"], ["B", "A", "C", "D"]]


def test_cycle_is_infeasible():
    req = SolveRequest(
        events=[ev(c, f"d{c}", 1, 1, 1, 4) for c in "ABCD"],
        orderings=[
            OrderingIn(before="A", after="B"),
            OrderingIn(before="B", after="C"),
            OrderingIn(before="C", after="A"),
        ],
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, cost, witnesses, reason = solve(by_id, req.orderings)
    assert status == "infeasible"
    assert cost is None
    assert witnesses == []
    assert reason == "cycle"


def test_window_mutex_is_infeasible():
    req = SolveRequest(
        events=[
            ev("A", "d1", 1, 1, 1, 1),
            ev("B", "d2", 1, 1, 1, 1),
            ev("C", "d3", 1, 3, 2, 4),
            ev("D", "d4", 1, 4, 2, 4),
        ]
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, _, _, reason = solve(by_id, req.orderings)
    assert status == "infeasible"
    assert reason == "window"


def test_cycle_via_device_chain_and_edge():
    # Same-device chain A -> B, explicit B? no: edge B...A closes loop via A->B + B->?->A
    # X(serial1) -> Y(serial2) on line1, plus edge Y -> X closes the loop.
    req = SolveRequest(
        events=[
            ev("X", "line1", 1, 1, 1, 4),
            ev("Y", "line1", 2, 2, 1, 4),
            ev("Z", "d2", 1, 3, 1, 4),
            ev("W", "d3", 1, 4, 1, 4),
        ],
        orderings=[OrderingIn(before="Y", after="X")],
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, _, _, reason = solve(by_id, req.orderings)
    assert status == "infeasible"
    assert reason == "cycle"


def test_observed_rank_twenty_accepted():
    req = SolveRequest(
        events=[
            ev("A", "d1", 1, 20, 1, 4),
            ev("B", "d2", 1, 1, 1, 4),
            ev("C", "d3", 1, 2, 1, 4),
            ev("D", "d4", 1, 3, 1, 4),
        ]
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, cost, witnesses, reason = solve(by_id, req.orderings)
    assert status == "unique"
    # A wants rank 20 but windows end at 4: push A to 4, B/C/D keep 1/2/3
    # -> |4-20| = 16.
    assert cost == 16
    assert witnesses[0] == ["B", "C", "D", "A"]


def test_device_serial_order_forced():
    req = SolveRequest(
        events=[
            ev("X", "line1", 1, 4, 1, 4),
            ev("Y", "line1", 2, 1, 1, 4),
            ev("Z", "d2", 1, 3, 1, 4),
            ev("W", "d3", 1, 2, 1, 4),
        ]
    )
    errors, by_id = validate_request(req)
    assert not errors
    status, cost, witnesses, reason = solve(by_id, req.orderings)
    # X must precede Y; brute force: X1 Y2 Z3 W4 -> |1-4|+|2-1|+|3-3|+|4-2|=6
    assert status in {"unique", "multiple"}
    for timeline in witnesses:
        assert timeline.index("X") < timeline.index("Y")
    assert cost == 6


# --------------------------------------------------------------------------
# Validation locations
# --------------------------------------------------------------------------

def request_post(events, orderings=None):
    return client.post(
        "/api/solve",
        json={
            "orderings": orderings or [],
            # Defaults: each event on its own device with a distinct serial so
            # that individual tests only declare the fields they perturb.
            "events": [
                {
                    "id": e["id"],
                    "device": e.get("device", f"d{idx}"),
                    "serial": e.get("serial", idx + 1),
                    "observedRank": e.get("rank", 1),
                    "windowLow": e.get("low", 1),
                    "windowHigh": e.get("high", 4),
                }
                for idx, e in enumerate(events)
            ],
        },
    )


def test_bad_event_id_format_located():
    resp = request_post(
        [
            {"id": "a"},
            {"id": "B"},
            {"id": "C"},
            {"id": "D"},
        ]
    )
    body = resp.json()
    assert body["status"] == "invalid_input"
    err = next(e for e in body["errors"] if e["code"] == "event.id.format")
    assert err["path"] == ["events", "0", "id"]
    assert err["eventId"] == "a"


def test_window_out_of_bounds_located():
    resp = request_post(
        [
            {"id": "A", "low": 1, "high": 5},
            {"id": "B"},
            {"id": "C"},
            {"id": "D"},
        ]
    )
    body = resp.json()
    codes = {e["code"] for e in body["errors"]}
    assert "event.window.out_of_bounds" in codes
    err = next(e for e in body["errors"] if e["code"] == "event.window.out_of_bounds")
    assert err["path"] == ["events", "0", "windowHigh"]


def test_duplicate_serial_located():
    resp = request_post(
        [
            {"id": "A", "device": "line9", "serial": 7},
            {"id": "B", "device": "line9", "serial": 7},
            {"id": "C"},
            {"id": "D"},
        ]
    )
    body = resp.json()
    err = next(e for e in body["errors"] if e["code"] == "event.serial.duplicate")
    assert err["eventId"] == "B"
    assert err["path"] == ["events", "1", "serial"]


def test_self_loop_and_duplicate_edge_located():
    events = [{"id": c} for c in "ABCD"]
    resp = request_post(
        events,
        orderings=[
            {"before": "A", "after": "A"},
            {"before": "A", "after": "B"},
            {"before": "A", "after": "B"},
        ],
    )
    body = resp.json()
    codes = {e["code"]: e for e in body["errors"]}
    assert "ordering.self_loop" in codes
    assert codes["ordering.self_loop"]["orderingIndex"] == 0
    assert codes["ordering.duplicate"]["orderingIndex"] == 2


def test_unknown_reference_located():
    events = [{"id": c} for c in "ABCD"]
    resp = request_post(events, orderings=[{"before": "A", "after": "Z"}])
    body = resp.json()
    err = next(e for e in body["errors"] if e["code"] == "ordering.ref.unknown")
    assert err["path"] == ["orderings", "0", "after"]
    assert err["orderingIndex"] == 0


def test_empty_ordering_endpoints_and_rank_range_located():
    events = [{"id": c} for c in "ABCD"]
    resp = request_post(
        events,
        orderings=[{"before": "", "after": ""}],
    )
    body = resp.json()
    codes = [e["code"] for e in body["errors"]]
    assert "ordering.ref.empty" in codes
    # Two empty ends are not additionally reported as a self loop.
    assert "ordering.self_loop" not in codes

    resp2 = request_post([{"id": c, "rank": 21} for c in "ABCD"])
    body2 = resp2.json()
    err = next(e for e in body2["errors"] if e["code"] == "event.observed_rank.range")
    assert err["path"] == ["events", "0", "observedRank"]


def test_event_count_bounds():
    for n, ok in ((3, False), (4, True), (20, True), (21, False)):
        ids = [chr(ord("A") + i) for i in range(n)]
        resp = request_post(
            [{"id": i, "low": 1, "high": max(n, 1)} for i in ids]
        )
        body = resp.json()
        if ok:
            assert body["status"] != "invalid_input", body["errors"]
        else:
            assert body["status"] == "invalid_input"
            assert any(e["code"] == "events.count" for e in body["errors"])


# --------------------------------------------------------------------------
# API smoke
# --------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_solve_roundtrip():
    resp = request_post([{"id": c, "rank": i + 1} for i, c in enumerate("ABCD")])
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unique"
    assert body["optimalCost"] == 0
    assert body["witnesses"][0]["timeline"] == ["A", "B", "C", "D"]


# --------------------------------------------------------------------------
# Exhaustive cross-check against brute force on random small instances
# --------------------------------------------------------------------------

def brute_force(ids, events_by_id, orderings):
    n = len(ids)
    by_device = defaultdict(list)
    for k in ids:
        e = events_by_id[k]
        by_device[e.device].append((e.serial, k))
    device_before = {}
    for entries in by_device.values():
        entries.sort()
        for (_, a), (__, b) in zip(entries, entries[1:]):
            device_before[(a, b)] = True
    edges = {(o.before, o.after) for o in orderings}

    feasible = []
    for perm in itertools.permutations(ids):
        pos = {k: i + 1 for i, k in enumerate(perm)}
        ok = True
        for k in ids:
            e = events_by_id[k]
            if not (e.window_low <= pos[k] <= e.window_high):
                ok = False
                break
        if not ok:
            continue
        for a, b in set(list(device_before) + list(edges)):
            if not (pos[a] < pos[b]):
                ok = False
                break
        if not ok:
            continue
        cost = sum(abs(pos[k] - events_by_id[k].observed_rank) for k in ids)
        feasible.append((cost, list(perm)))

    if not feasible:
        return "infeasible", None, [], None
    best = min(c for c, _ in feasible)
    opts = sorted(p for c, p in feasible if c == best)
    if len(opts) == 1:
        return "unique", best, [opts[0]], None
    return "multiple", best, opts[:2], None


def test_solver_matches_brute_force_random():
    rng = random.Random(424242)
    for trial in range(120):
        n = rng.randint(4, 8)
        ids = [chr(ord("A") + i) for i in range(n)]
        devices_pool = [f"d{i}" for i in range(rng.randint(1, 4))]
        serial_counter = defaultdict(int)
        events = []
        for k in ids:
            d = rng.choice(devices_pool)
            serial_counter[d] += 1
            low = rng.randint(1, n)
            high = rng.randint(low, min(n, low + rng.randint(0, 3)))
            events.append(ev(k, d, serial_counter[d], rng.randint(1, 20), low, high))
        orderings = []
        for _ in range(rng.randint(0, 3)):
            a, b = rng.sample(ids, 2)
            edge = OrderingIn(before=a, after=b)
            if (a, b) not in {(o.before, o.after) for o in orderings}:
                orderings.append(edge)

        req = SolveRequest(events=events, orderings=orderings)
        errors, by_id = validate_request(req)
        assert not errors
        got = solve(by_id, orderings)
        expected = brute_force(ids, by_id, orderings)
        assert got[:3] == expected[:3], f"trial {trial}: {got} != {expected}"
        if got[0] == "infeasible":
            assert got[3] in {"cycle", "window"}
