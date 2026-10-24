"""Forecast selection: the core business rule of the application.

For every target period (`start_time`):

1. work out its delivery date (UK local calendar date),
2. work out the decision cutoff for that delivery date (see `policy.py`),
3. discard every forecast with ``publish_time > cutoff`` (it did not exist yet),
4. keep the forecast with the latest remaining ``publish_time``
   (tie on identical publish time -> highest forecast value; see `cleaning.py`
   for how exact duplicates are collapsed first),
5. join it to the actual for the same `start_time`.

Nothing here touches HTTP, files or the web framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .policy import DecisionPolicy
from .timeutils import delivery_dates, half_hour_index

SELECTED_COLUMNS = ["start_time", "delivery_date", "forecast_mw", "publish_time", "cutoff_utc"]

MATCHED = "matched"
MISSING_FORECAST = "missing_forecast"
MISSING_ACTUAL = "missing_actual"
NO_DATA = "no_data"


@dataclass
class SelectionReport:
    candidate_forecasts: int = 0
    excluded_after_cutoff: int = 0
    eligible_forecasts: int = 0
    targets_with_forecast: int = 0


def select_forecasts(
    forecasts: pd.DataFrame, policy: DecisionPolicy
) -> tuple[pd.DataFrame, SelectionReport]:
    """Pick, per target period, the latest forecast published at or before the cutoff."""
    report = SelectionReport(candidate_forecasts=len(forecasts))
    if forecasts.empty:
        empty = pd.DataFrame({c: [] for c in SELECTED_COLUMNS})
        return empty.astype(
            {
                "start_time": "datetime64[ns, UTC]",
                "forecast_mw": "float64",
                "publish_time": "datetime64[ns, UTC]",
                "cutoff_utc": "datetime64[ns, UTC]",
            }
        ), report

    df = forecasts.copy()
    df["delivery_date"] = delivery_dates(df["start_time"], policy.timezone)
    cutoffs = {d: policy.cutoff_utc(d) for d in df["delivery_date"].unique()}
    df["cutoff_utc"] = pd.to_datetime(df["delivery_date"].map(cutoffs), utc=True).dt.as_unit("ns")

    eligible = df[df["publish_time"] <= df["cutoff_utc"]]
    report.eligible_forecasts = len(eligible)
    report.excluded_after_cutoff = len(df) - len(eligible)

    selected = (
        eligible.sort_values(["start_time", "publish_time", "forecast_mw"], kind="mergesort")
        .drop_duplicates("start_time", keep="last")
        .reset_index(drop=True)
    )
    report.targets_with_forecast = len(selected)
    return selected[SELECTED_COLUMNS], report


def build_period_frame(
    actuals: pd.DataFrame,
    selected: pd.DataFrame,
    start: date,
    end: date,
    policy: DecisionPolicy,
) -> pd.DataFrame:
    """One row per 30-minute target period in [start, end] with actual, forecast and error.

    Periods lacking an actual and/or a forecast are kept (with NaN and a `status`)
    so coverage is visible; errors are computed only where both values exist.
    """
    frame = pd.DataFrame({"start_time": half_hour_index(start, end, policy.timezone)})
    frame["delivery_date"] = delivery_dates(frame["start_time"], policy.timezone)
    frame["cutoff_utc"] = pd.to_datetime(
        frame["delivery_date"].map({d: policy.cutoff_utc(d) for d in frame["delivery_date"].unique()}),
        utc=True,
    ).dt.as_unit("ns")

    frame = frame.merge(actuals, on="start_time", how="left")
    frame = frame.merge(
        selected[["start_time", "forecast_mw", "publish_time"]], on="start_time", how="left"
    )

    has_a = frame["actual_mw"].notna()
    has_f = frame["forecast_mw"].notna()
    frame["status"] = NO_DATA
    frame.loc[has_a & has_f, "status"] = MATCHED
    frame.loc[has_a & ~has_f, "status"] = MISSING_FORECAST
    frame.loc[~has_a & has_f, "status"] = MISSING_ACTUAL

    frame["error_mw"] = frame["forecast_mw"] - frame["actual_mw"]  # + over, - under
    frame["abs_error_mw"] = frame["error_mw"].abs()
    frame["lead_time_hours"] = (frame["start_time"] - frame["publish_time"]) / pd.Timedelta(hours=1)
    return frame
