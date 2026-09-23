"""Replay solver built on CP-SAT.

Model
-----
Events occupy positions 1..n (a permutation). For every event ``e``:

* ``p[e][k]`` is true iff event ``e`` sits at 0-based rank ``k``;
* only ranks inside its closed window ``[windowLow, windowHigh]`` are allowed;
* each event occupies exactly one rank and each rank hosts one event;
* an integer ``pos[e] = 1 + sum k*p[e][k]`` drives ordering constraints.

Ordering constraints come from two sources:

* events on the same device must follow that device's ascending serial order;
* every explicit ``before -> after`` edge.

The unique objective is ``sum_e |pos[e] - observedRank[e]|``.

Witness selection
-----------------
After the optimal cost ``C`` is known, the lexicographically smallest
event-id sequence among optimal solutions minimizes the base-(n+1) number
whose digits are the event index at each rank. Since one such number may
exceed int64, ranks are covered in segments of at most 13 digits (two
segments at n=20), each optimized once and then pinned. A second solve
forbids that exact permutation; because lexicographic order is total, the
smallest remaining solution is precisely the second-smallest witness. If it
is infeasible, the optimum is unique.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from .models import EventIn, OrderingIn


def _build_permutation_model(
    event_ids: List[str],
    events_by_id: Dict[str, EventIn],
    orderings: List[OrderingIn],
):
    """Build the base CP model. Returns (model, p, pos, cost, ids)."""
    n = len(event_ids)
    idx = {ev_id: i for i, ev_id in enumerate(event_ids)}
    model = cp_model.CpModel()

    # p[i][k]: event i is placed at 0-based rank k.
    p: List[List[cp_model.IntVar]] = [[None] * n for _ in range(n)]  # type: ignore
    pos: List[cp_model.IntVar] = []

    for i, ev_id in enumerate(event_ids):
        ev = events_by_id[ev_id]
        row: List[cp_model.IntVar] = []
        for k in range(n):
            position = k + 1
            if ev.window_low <= position <= ev.window_high:
                var = model.NewBoolVar(f"p_{ev_id}_{position}")
            else:
                var = model.NewConstant(0)
            row.append(var)
            p[i][k] = var
        model.AddExactlyOne(row)
        pi = model.NewIntVar(ev.window_low, ev.window_high, f"pos_{ev_id}")
        model.Add(pi == 1 + sum(k * row[k] for k in range(n)))
        pos.append(pi)

    for k in range(n):
        model.AddExactlyOne(p[i][k] for i in range(n))

    # Device serial order.
    by_device: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for ev_id in event_ids:
        ev = events_by_id[ev_id]
        by_device[ev.device.strip()].append((ev.serial, ev_id))
    for entries in by_device.values():
        entries.sort()
        for (_, a), (__, b) in zip(entries, entries[1:]):
            model.Add(pos[idx[a]] < pos[idx[b]])

    # Explicit precedence edges.
    for edge in orderings:
        model.Add(pos[idx[edge.before]] < pos[idx[edge.after]])

    # Objective: total absolute deviation from observed ranks.
    # Observed ranks reach 20 while positions only reach n, so an individual
    # deviation can be as large as max(n, 20) - 1.
    dev_bound = max(n, 20) - 1
    abs_vars: List[cp_model.IntVar] = []
    for i, ev_id in enumerate(event_ids):
        dev = model.NewIntVar(0, dev_bound, f"dev_{ev_id}")
        model.AddAbsEquality(dev, pos[i] - events_by_id[ev_id].observed_rank)
        abs_vars.append(dev)
    cost = model.NewIntVar(0, n * max(n, 20), "cost")
    model.Add(cost == sum(abs_vars))

    return model, p, pos, cost


def _new_solver() -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 20260923
    solver.parameters.max_time_in_seconds = 30.0
    return solver


def _permutation_from_solution(
    solver: cp_model.CpSolver, p: List[List[cp_model.IntVar]], event_ids: List[str]
) -> List[str]:
    n = len(event_ids)
    timeline = [""] * n
    for i, ev_id in enumerate(event_ids):
        for k in range(n):
            if solver.Value(p[i][k]) == 1:
                timeline[k] = ev_id
                break
    return timeline


def _lex_min_timeline(
    model: cp_model.CpModel,
    p: List[List[cp_model.IntVar]],
    event_ids: List[str],
    forbidden: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Lexicographically smallest timeline (by event id) under the model.

    When ``forbidden`` is given the solution must differ from that exact
    permutation. The lexicographic order is encoded as a base-(n+1) number
    over event indices; with n <= 20 a single number can exceed 64 bits, so
    the ranks are covered in segments of at most 13 digits (two segments at
    n=20), each minimized once and then pinned. Returns ``None`` only when
    the model is proved infeasible (e.g. no second optimal permutation
    exists); other non-optimal statuses such as a timeout raise.
    """
    n = len(event_ids)
    base = n + 1
    # 13 base-21 digits keep the sum of objective coefficients
    # (n(n-1)/2 * (b^13-1)/(b-1) ~= 1.4e18 at n=20) inside int64.
    segment_len = 13

    if forbidden is not None:
        # At least one rank must host a different event than the forbidden one.
        fid = {ev_id: i for i, ev_id in enumerate(event_ids)}
        model.Add(sum(p[fid[forbidden[k]]][k] for k in range(n)) <= n - 1)

    def segment_expr(seg_start: int, seg_end: int):
        terms = []
        for k in range(seg_start, seg_end):
            digit = sum(i * p[i][k] for i in range(n))
            terms.append(digit * (base ** (seg_end - 1 - k)))
        return sum(terms)

    solver = _new_solver()
    for seg_no, seg_start in enumerate(range(0, n, segment_len)):
        seg_end = min(n, seg_start + segment_len)
        expr = segment_expr(seg_start, seg_end)
        model.Minimize(expr)
        status = solver.Solve(model)
        if status == cp_model.INFEASIBLE:
            if seg_no == 0:
                return None  # no witness at all (e.g. optimum is unique)
            raise RuntimeError("lexicographic enumeration became infeasible after a pinned prefix")
        if status != cp_model.OPTIMAL:
            raise RuntimeError(f"lexicographic enumeration status: {solver.StatusName(status)}")
        # Pin the just-optimized segment by its exact boolean values;
        # reading the objective (a double) would lose integer precision.
        for k in range(seg_start, seg_end):
            picked = next(i for i in range(n) if solver.Value(p[i][k]) == 1)
            model.Add(p[picked][k] == 1)

    return _permutation_from_solution(solver, p, event_ids)


def _has_cycle(event_ids: List[str], events_by_id, orderings) -> bool:
    """Cycle check over device-serial chains plus explicit edges (Kahn)."""
    adj: Dict[str, List[str]] = {k: [] for k in event_ids}
    indeg = {k: 0 for k in event_ids}

    def add_edge(a: str, b: str) -> None:
        adj[a].append(b)
        indeg[b] += 1

    by_device: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for ev_id in event_ids:
        ev = events_by_id[ev_id]
        by_device[ev.device.strip()].append((ev.serial, ev_id))
    for entries in by_device.values():
        entries.sort()
        for (_, a), (__, b) in zip(entries, entries[1:]):
            add_edge(a, b)
    for edge in orderings:
        add_edge(edge.before, edge.after)

    queue = [k for k in event_ids if indeg[k] == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for nxt in adj[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return seen < len(event_ids)


def solve(
    events_by_id: Dict[str, EventIn], orderings: List[OrderingIn]
) -> Tuple[str, Optional[int], List[List[str]], Optional[str]]:
    """Solve a validated request.

    Returns ``(status, optimal_cost, witnesses, reason)`` where status is one
    of ``infeasible | unique | multiple``, reason is ``cycle`` when the
    precedence graph is cyclic and ``window`` when acyclic constraints still
    cannot fit the position windows; it is ``None`` for feasible results.
    """
    event_ids = sorted(events_by_id)
    n = len(event_ids)

    cyclic = _has_cycle(event_ids, events_by_id, orderings)

    # ---- phase 0: feasibility + optimal cost -----------------------------
    model, p, _, cost = _build_permutation_model(event_ids, events_by_id, orderings)
    model.Minimize(cost)
    solver = _new_solver()
    status = solver.Solve(model)
    if status == cp_model.INFEASIBLE:
        return "infeasible", None, [], ("cycle" if cyclic else "window")
    if status != cp_model.OPTIMAL:
        raise RuntimeError(f"CP-SAT unexpected status while optimizing cost: {status}")
    optimal_cost = int(solver.Value(cost))

    # ---- enumeration models pinned to the optimal cost -------------------
    def _fresh_enum_model():
        m, pp, _, cc = _build_permutation_model(event_ids, events_by_id, orderings)
        m.Add(cc == optimal_cost)
        return m, pp

    m1, p_e1 = _fresh_enum_model()
    first = _lex_min_timeline(m1, p_e1, event_ids)
    if first is None:
        raise RuntimeError("lexicographic enumeration failed unexpectedly at witness 1")

    m2, p_e2 = _fresh_enum_model()
    second = _lex_min_timeline(m2, p_e2, event_ids, forbidden=first)
    if second is None:
        return "unique", optimal_cost, [first], None
    return "multiple", optimal_cost, [first, second], None
