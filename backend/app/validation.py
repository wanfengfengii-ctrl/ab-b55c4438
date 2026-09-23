"""输入校验：格式、编号引用、区间越界等错误均定位到具体输入。

错误形如 {"loc": "events[2].observed", "msg": "..."}，由 API 层以 422 返回。
"""
from __future__ import annotations

import re
from typing import Any

from .solver import EventSpec

MIN_EVENTS = 4
MAX_EVENTS = 20
MAX_OBSERVED = 20

_ID_RE = re.compile(r"[A-Z]")


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def validate_payload(data: Any) -> list[dict]:
    """返回错误列表；空列表表示通过。"""
    errors: list[dict] = []

    def err(loc: str, msg: str) -> None:
        errors.append({"loc": loc, "msg": msg})

    if not isinstance(data, dict):
        err("body", "请求体须为 JSON 对象")
        return errors

    events = data.get("events")
    if not isinstance(events, list):
        err("events", "events 须为数组")
        return errors

    n = len(events)
    if not (MIN_EVENTS <= n <= MAX_EVENTS):
        err("events", f"事件数量须为 {MIN_EVENTS}..{MAX_EVENTS}，当前为 {n}")

    seen_ids: dict[str, int] = {}
    seen_dev_seq: dict[tuple[str, int], int] = {}

    for i, e in enumerate(events):
        loc = f"events[{i}]"
        if not isinstance(e, dict):
            err(loc, "事件须为对象")
            continue

        eid = e.get("id")
        id_ok = isinstance(eid, str) and _ID_RE.fullmatch(eid) is not None
        if not id_ok:
            err(f"{loc}.id", "编号须为单个大写英文字母（A-Z）")
        elif eid in seen_ids:
            err(f"{loc}.id", f"编号 {eid} 与 events[{seen_ids[eid]}] 重复")
        else:
            seen_ids[eid] = i

        dev = e.get("device")
        dev_ok = isinstance(dev, str) and bool(dev.strip())
        if not dev_ok:
            err(f"{loc}.device", "设备须为非空字符串")

        seq = e.get("seq")
        seq_ok = _is_int(seq) and seq >= 1
        if not seq_ok:
            err(f"{loc}.seq", "设备内序号须为正整数")

        obs = e.get("observed")
        if not (_is_int(obs) and 1 <= obs <= MAX_OBSERVED):
            err(f"{loc}.observed", f"观测位次须为 1..{MAX_OBSERVED} 的整数")

        w = e.get("window")
        if not isinstance(w, dict):
            err(f"{loc}.window", "window 须为对象，含整数 lo、hi")
        else:
            lo, hi = w.get("lo"), w.get("hi")
            lo_ok = _is_int(lo)
            hi_ok = _is_int(hi)
            if not lo_ok:
                err(f"{loc}.window.lo", "区间下界须为整数")
            elif not (1 <= lo <= n):
                err(f"{loc}.window.lo", f"区间下界越界：须在 1..{n} 内")
            if not hi_ok:
                err(f"{loc}.window.hi", "区间上界须为整数")
            elif not (1 <= hi <= n):
                err(f"{loc}.window.hi", f"区间上界越界：须在 1..{n} 内")
            if lo_ok and hi_ok and 1 <= lo and hi <= n and lo > hi:
                err(f"{loc}.window", f"区间下界 {lo} 不得大于上界 {hi}")

        if dev_ok and seq_ok:
            key = (dev.strip(), seq)
            if key in seen_dev_seq:
                err(
                    f"{loc}.seq",
                    f"设备 {dev.strip()} 的序号 {seq} 与 events[{seen_dev_seq[key]}] 重复",
                )
            else:
                seen_dev_seq[key] = i

    precs = data.get("precedences", [])
    if not isinstance(precs, list):
        err("precedences", "precedences 须为数组")
        return errors

    seen_pairs: set[tuple[str, str]] = set()
    for j, p in enumerate(precs):
        loc = f"precedences[{j}]"
        if not isinstance(p, dict):
            err(loc, "先后关系须为对象，含 before、after")
            continue
        before, after = p.get("before"), p.get("after")
        refs_ok = True
        for name, v in (("before", before), ("after", after)):
            if not isinstance(v, str) or v not in seen_ids:
                err(f"{loc}.{name}", f"引用了不存在的编号 {v!r}")
                refs_ok = False
        if refs_ok:
            if before == after:
                err(loc, f"先后关系不得自环（{before}→{after}）")
            elif (before, after) in seen_pairs:
                err(loc, f"先后关系 {before}→{after} 重复")
            else:
                seen_pairs.add((before, after))

    return errors


def to_event_specs(events: list[dict]) -> list[EventSpec]:
    """把校验通过的原始事件转换为求解器输入。"""
    return [
        EventSpec(
            id=e["id"],
            device=e["device"].strip(),
            seq=int(e["seq"]),
            observed=int(e["observed"]),
            lo=int(e["window"]["lo"]),
            hi=int(e["window"]["hi"]),
        )
        for e in events
    ]
