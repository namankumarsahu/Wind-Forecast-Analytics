from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

UNIT = "MW"


class PolicyInfo(BaseModel):
    """How the purchase-decision cutoff was applied (shown in the UI for transparency)."""

    timezone: str
    cutoff_local_time: str = Field(description="HH:MM on the decision day, in `timezone`")
    days_ahead: int
    description: str
    example_delivery_date: date
    example_decision_cutoff_utc: datetime


class Metrics(BaseModel):
    """Accuracy metrics computed by the backend. Null = undefined (e.g. no valid pairs)."""

    n: int = Field(description="Valid matched forecast/actual periods used")
    n_dropped: int = 0
    mae_mw: float | None = None
    rmse_mw: float | None = None
    mbe_mw: float | None = Field(None, description="Mean of (forecast - actual); >0 = over-forecast")
    wape_pct: float | None = None
    unit: str = UNIT


class Coverage(BaseModel):
    expected_periods: int = Field(description="30-minute periods in the selected range")
    actual_periods: int
    forecast_periods: int = Field(description="Periods with an eligible forecast")
    matched_periods: int = Field(description="Periods with both forecast and actual")
    forecast_coverage_pct: float | None
    matched_coverage_pct: float | None
    note: str


class GenerationSummary(BaseModel):
    n: int
    mean_mw: float | None = None
    min_mw: float | None = None
    max_mw: float | None = None
    total_mwh: float | None = Field(None, description="Energy = sum(MW) x 0.5 h (actuals only)")
    unit: str = UNIT


class OverUnder(BaseModel):
    overestimated_n: int
    underestimated_n: int
    exact_n: int
    overestimated_pct: float | None
    underestimated_pct: float | None
    mean_overestimate_mw: float | None = Field(None, description="Mean error over over-forecast periods (>0)")
    mean_underestimate_mw: float | None = Field(None, description="Mean error over under-forecast periods (<0)")
    max_overestimate_mw: float | None = None
    max_underestimate_mw: float | None = None
    unit: str = UNIT


class QualityReport(BaseModel):
    """What the pipeline discarded; lets users trust (or challenge) the numbers."""

    actual_rows_raw: int
    actual_rows_non_wind: int
    actual_rows_invalid: int
    actual_duplicates_removed: int
    forecast_rows_raw: int
    forecast_rows_invalid: int
    forecast_duplicates_removed: int
    forecast_conflicting_duplicates: int
    forecasts_excluded_after_cutoff: int


class DataStatusOut(BaseModel):
    source: str = Field(description="'elexon-live', 'cache' or 'mixed'")
    retrieved_at: datetime | None = Field(None, description="Oldest retrieval time of any chunk used")
    chunks_total: int
    chunks_from_cache: int
    chunks_fetched: int
    offline_mode: bool
