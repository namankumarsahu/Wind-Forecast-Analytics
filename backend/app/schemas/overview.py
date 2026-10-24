from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from .common import Coverage, DataStatusOut, GenerationSummary, Metrics, OverUnder, PolicyInfo, QualityReport


class TimeSeriesPoint(BaseModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    forecast_publish_time: datetime | None


class OverviewResponse(BaseModel):
    start: date
    end: date
    policy: PolicyInfo
    metrics: Metrics
    coverage: Coverage
    forecast_summary: GenerationSummary
    actual_summary: GenerationSummary
    over_under: OverUnder
    earliest_forecast_publish_time: datetime | None
    latest_forecast_publish_time: datetime | None
    series: list[TimeSeriesPoint]
    data_status: DataStatusOut
    quality: QualityReport


class ConfigResponse(BaseModel):
    analysis_start: date
    analysis_end: date
    unit: str
    policy: PolicyInfo
