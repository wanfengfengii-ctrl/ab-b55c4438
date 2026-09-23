"""Input validation with precise error location.

Every validation error carries a JSON-pointer-like ``path`` plus, where
applicable, the offending event id / ordering index so the UI can highlight
the exact input cell or row.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple

from .models import (
    MAX_EVENTS,
    MAX_OBSERVED_POSITION,
    MIN_EVENTS,
    EventIn,
    ErrorItem,
    OrderingIn,
    SolveRequest,
)

ID_PATTERN = re.compile(r"^[A-Z]$")
DETECTABLE_ID_PATTERN = re.compile(r"^[A-Za-z]$")


def _err(
    code: str,
    message: str,
    path: List[str] | None = None,
    *,
    event_id: str | None = None,
    ordering_index: int | None = None,
) -> ErrorItem:
    return ErrorItem(
        code=code,
        message=message,
        path=path or [],
        eventId=event_id,
        orderingIndex=ordering_index,
    )


def validate_request(req: SolveRequest) -> Tuple[List[ErrorItem], Dict[str, EventIn]]:
    """Validate a solve request.

    Returns ``(errors, events_by_id)``. ``events_by_id`` maps every
    syntactically valid, non-duplicated event id to its event and is only
    meaningful when ``errors`` is empty.
    """
    errors: List[ErrorItem] = []
    events: List[EventIn] = list(req.events)
    orderings: List[OrderingIn] = list(req.orderings)

    # ---- count -----------------------------------------------------------
    n = len(events)
    if n == 0:
        errors.append(_err("events.empty", "至少需要 4 个事件", ["events"]))
    elif not (MIN_EVENTS <= n <= MAX_EVENTS):
        errors.append(
            _err(
                "events.count",
                f"每轮事件数必须在 {MIN_EVENTS} 至 {MAX_EVENTS} 之间, 当前为 {n}",
                ["events"],
            )
        )

    # ---- per-event field checks -----------------------------------------
    by_id: Dict[str, EventIn] = {}
    raw_ids: List[str] = []
    serials_by_device: Dict[str, List[Tuple[int, str, int]]] = defaultdict(list)

    for i, ev in enumerate(events):
        base = ["events", str(i)]
        raw_id = ev.id
        raw_ids.append(raw_id)

        if not isinstance(raw_id, str) or not raw_id:
            errors.append(
                _err("event.id.empty", "事件编号不能为空", base + ["id"], ordering_index=None)
            )
        elif not ID_PATTERN.match(raw_id):
            hint = (
                "编号必须是单个大写英文字母 (A-Z)"
                if DETECTABLE_ID_PATTERN.match(raw_id)
                else "编号必须是单个大写英文字母 (A-Z), 不能是多字符或其他符号"
            )
            errors.append(
                _err(
                    "event.id.format",
                    f"事件编号 {raw_id!r} 非法: {hint}",
                    base + ["id"],
                    event_id=raw_id,
                )
            )
        else:
            if raw_id in by_id:
                errors.append(
                    _err(
                        "event.id.duplicate",
                        f"事件编号 {raw_id} 重复, 各事件编号必须互不相同",
                        base + ["id"],
                        event_id=raw_id,
                    )
                )
            else:
                by_id[raw_id] = ev

        if not isinstance(ev.device, str) or not ev.device.strip():
            errors.append(_err("event.device.empty", "设备标识不能为空", base + ["device"], event_id=raw_id or None))

        if not isinstance(ev.serial, int) or isinstance(ev.serial, bool) or ev.serial <= 0:
            errors.append(
                _err(
                    "event.serial.non_positive",
                    f"设备内序号必须为正整数, 当前为 {ev.serial}",
                    base + ["serial"],
                    event_id=raw_id or None,
                )
            )
        elif ev.serial > 10**9:
            errors.append(
                _err(
                    "event.serial.too_large",
                    f"设备内序号过大: {ev.serial}",
                    base + ["serial"],
                    event_id=raw_id or None,
                )
            )
        else:
            if ev.device and isinstance(ev.device, str):
                serials_by_device[ev.device.strip()].append((ev.serial, raw_id, i))

        if (
            not isinstance(ev.observed_rank, int)
            or isinstance(ev.observed_rank, bool)
            or not (1 <= ev.observed_rank <= MAX_OBSERVED_POSITION)
        ):
            errors.append(
                _err(
                    "event.observed_rank.range",
                    f"观测位次必须在 1 至 {MAX_OBSERVED_POSITION} 之间, 当前为 {ev.observed_rank}",
                    base + ["observedRank"],
                    event_id=raw_id or None,
                )
            )

        if not isinstance(ev.window_low, int) or isinstance(ev.window_low, bool):
            errors.append(
                _err("event.window.integer", "区间下界必须为整数", base + ["windowLow"], event_id=raw_id or None)
            )
        if not isinstance(ev.window_high, int) or isinstance(ev.window_high, bool):
            errors.append(
                _err("event.window.integer", "区间上界必须为整数", base + ["windowHigh"], event_id=raw_id or None)
            )
        if isinstance(ev.window_low, int) and isinstance(ev.window_high, int):
            if not (1 <= ev.window_low <= n):
                errors.append(
                    _err(
                        "event.window.out_of_bounds",
                        f"区间下界 {ev.window_low} 越界, 必须位于 1 至事件数 {n} 之间",
                        base + ["windowLow"],
                        event_id=raw_id or None,
                    )
                )
            if not (1 <= ev.window_high <= n):
                errors.append(
                    _err(
                        "event.window.out_of_bounds",
                        f"区间上界 {ev.window_high} 越界, 必须位于 1 至事件数 {n} 之间",
                        base + ["windowHigh"],
                        event_id=raw_id or None,
                    )
                )
            if (
                1 <= ev.window_low <= n
                and 1 <= ev.window_high <= n
                and ev.window_low > ev.window_high
            ):
                errors.append(
                    _err(
                        "event.window.reversed",
                        f"区间上下界颠倒: [{ev.window_low}, {ev.window_high}]",
                        base + ["windowLow"],
                        event_id=raw_id or None,
                    )
                )

    # ---- serial uniqueness within a device ------------------------------
    for device, entries in serials_by_device.items():
        seen: Dict[int, int] = {}
        for serial, ev_id, idx in entries:
            if serial in seen:
                errors.append(
                    _err(
                        "event.serial.duplicate",
                        f"设备 {device!r} 内序号 {serial} 同时出现在事件 "
                        f"{raw_ids[seen[serial]]} 与 {ev_id} 上, 同设备序号不得重复",
                        ["events", str(idx), "serial"],
                        event_id=ev_id,
                    )
                )
            else:
                seen[serial] = idx

    # ---- orderings -------------------------------------------------------
    seen_pairs: set[Tuple[str, str]] = set()
    for j, ord_ in enumerate(orderings):
        base = ["orderings", str(j)]
        before, after = ord_.before, ord_.after
        local_problem = False

        for side, ref in (("before", before), ("after", after)):
            if not isinstance(ref, str) or not ref:
                errors.append(
                    _err(
                        "ordering.ref.empty",
                        f"先后关系第 {j + 1} 行的 {side} 端编号为空",
                        base + [side],
                        ordering_index=j,
                    )
                )
                local_problem = True
            elif not ID_PATTERN.match(ref):
                errors.append(
                    _err(
                        "ordering.ref.format",
                        f"先后关系第 {j + 1} 行的 {side} 端 {ref!r} 不是合法的大写字母编号",
                        base + [side],
                        ordering_index=j,
                    )
                )
                local_problem = True
            elif ref not in by_id:
                errors.append(
                    _err(
                        "ordering.ref.unknown",
                        f"先后关系第 {j + 1} 行引用了不存在的事件编号 {ref}",
                        base + [side],
                        ordering_index=j,
                    )
                )
                local_problem = True

        if (
            isinstance(before, str)
            and isinstance(after, str)
            and before
            and before == after
        ):
            errors.append(
                _err(
                    "ordering.self_loop",
                    f"先后关系 {before} -> {after} 构成自环, 显式先后关系不得自环",
                    base,
                    ordering_index=j,
                )
            )
            local_problem = True

        if not local_problem:
            if (before, after) in seen_pairs:
                errors.append(
                    _err(
                        "ordering.duplicate",
                        f"先后关系 {before} -> {after} 重复, 显式先后关系不得重复",
                        base,
                        ordering_index=j,
                    )
                )
            else:
                seen_pairs.add((before, after))

    return errors, by_id
