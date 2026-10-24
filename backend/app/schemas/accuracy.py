from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from .common import Coverage, DataStatusOut, Metrics, OverUnder, PolicyInfo, QualityReport


class DailySummary(BaseModel):
    date: dt.date
    n: int
    mae_mw: float | None
    rmse_mw: float | None
    mbe_mw: float | None
    wape_pct: float | None
    mean_actual_mw: float | None
    mean_forecast_mw: float | None


class HistogramBin(BaseModel):
    lower_mw: float
    upper_mw: float
    count: int


class TopError(BaseModel):
    start_time: dt.datetime
    forecast_mw: float
    actual_mw: float
    error_mw: float
    abs_error_mw: float
    forecast_publish_time: dt.datetime
    direction: str  # "over" | "under"


class AccuracyResponse(BaseModel):
    start: dt.date
    end: dt.date
    policy: PolicyInfo
    metrics: Metrics
    coverage: Coverage
    over_under: OverUnder
    daily: list[DailySummary]
    histogram: list[HistogramBin]
    histogram_bin_width_mw: float | None
    top_errors: list[TopError]
    data_status: DataStatusOut
    quality: QualityReport
