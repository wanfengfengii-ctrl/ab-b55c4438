"""Pydantic models for the production-line replay workbench."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

MAX_EVENTS = 20
MIN_EVENTS = 4
MAX_OBSERVED_POSITION = 20
MAX_DEVICE = 100  # serial numbers are positive integers, bounded for sanity


class EventIn(BaseModel):
    """A single recorded event.

    Attributes mirror the problem statement:
      id                unique uppercase-letter code
      device           device identifier (non-empty string)
      serial           positive integer, unique within one device
      observed_rank    1..20; where the event was observed
      window_low       inclusive lower bound of the allowed final position
      window_high      inclusive upper bound of the allowed final position
    """

    id: str = Field(..., description="事件编号, 单个大写英文字母")
    device: str = Field(..., description="设备标识, 非空字符串")
    serial: int = Field(..., description="设备内正整数序号")
    observed_rank: int = Field(..., alias="observedRank", description="观测位次 1..20")
    window_low: int = Field(..., alias="windowLow", description="位置闭区间下界")
    window_high: int = Field(..., alias="windowHigh", description="位置闭区间上界")

    model_config = {"populate_by_name": True}


class OrderingIn(BaseModel):
    """An explicit precedence: event ``before`` must be replayed before ``after``."""

    before: str
    after: str


class SolveRequest(BaseModel):
    events: List[EventIn]
    orderings: List[OrderingIn] = Field(default_factory=list)


class ErrorItem(BaseModel):
    """One located input error."""

    code: str
    message: str
    path: List[str] = Field(default_factory=list)
    event_id: Optional[str] = Field(default=None, alias="eventId")
    ordering_index: Optional[int] = Field(default=None, alias="orderingIndex")

    model_config = {"populate_by_name": True}


class Witness(BaseModel):
    """One optimal timeline: event ids in final replay order (position 1..n)."""

    timeline: List[str]


class SolveResponse(BaseModel):
    status: str = Field(..., description="invalid_input | infeasible | unique | multiple")
    reason: Optional[str] = Field(
        default=None, description="infeasible 时: cycle(先后关系成环) 或 window(窗口互斥/冲突)"
    )
    optimal_cost: Optional[int] = Field(default=None, alias="optimalCost")
    witnesses: List[Witness] = Field(default_factory=list)
    errors: List[ErrorItem] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
