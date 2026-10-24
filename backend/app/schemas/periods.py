from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel

from .common import Coverage, DataStatusOut, Metrics, PolicyInfo

PeriodStatus = Literal["matched", "missing_forecast", "missing_actual", "no_data"]


class PeriodRow(BaseModel):
    settlement_period: int
    start_time: dt.datetime
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    abs_error_mw: float | None
    forecast_publish_time: dt.datetime | None
    lead_time_hours: float | None
    decision_cutoff: dt.datetime
    status: PeriodStatus


class PeriodsResponse(BaseModel):
    date: dt.date
    policy: PolicyInfo
    metrics: Metrics
    coverage: Coverage
    rows: list[PeriodRow]
    data_status: DataStatusOut
