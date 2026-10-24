from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.services.cleaning import normalise_actuals, normalise_forecasts
from app.services.metrics import compute_metrics
from app.services.policy import DecisionPolicy
from app.services.selection import (
    MATCHED, MISSING_ACTUAL, MISSING_FORECAST, NO_DATA, build_period_frame, select_forecasts,
)

from .factories import actual, forecast

POLICY = DecisionPolicy()  # 09:00 London, day before
TARGET = "2026-01-15T12:00:00Z"


def _select(records):
    clean, _ = normalise_forecasts(pd.DataFrame(records))
    return select_forecasts(clean, POLICY)


def test_latest_forecast_before_cutoff_is_selected():
    selected, _ = _select([
        forecast(TARGET, "2026-01-13T20:00:00Z", 100),
        forecast(TARGET, "2026-01-14T06:00:00Z", 200),
        forecast(TARGET, "2026-01-14T08:59:00Z", 300),  # latest eligible
    ])
    assert len(selected) == 1
    row = selected.iloc[0]
    assert row["forecast_mw"] == 300
    assert row["publish_time"] == pd.Timestamp("2026-01-14T08:59:00Z")
    assert row["cutoff_utc"] == pd.Timestamp("2026-01-14T09:00:00Z")


def test_forecast_published_after_cutoff_is_excluded_even_if_it_is_newer():
    selected, report = _select([
        forecast(TARGET, "2026-01-14T08:00:00Z", 100),
        forecast(TARGET, "2026-01-14T09:00:01Z", 999),  # one second late
        forecast(TARGET, "2026-01-15T06:00:00Z", 555),  # published on the delivery day
    ])
    assert selected.iloc[0]["forecast_mw"] == 100
    assert report.excluded_after_cutoff == 2


def test_forecast_published_exactly_at_cutoff_is_eligible():
    selected, _ = _select([forecast(TARGET, "2026-01-14T09:00:00Z", 42)])
    assert selected.iloc[0]["forecast_mw"] == 42


def test_target_with_only_late_forecasts_gets_no_forecast_instead_of_a_future_one():
    selected, report = _select([forecast(TARGET, "2026-01-14T10:00:00Z", 1)])
    assert selected.empty
    assert report.targets_with_forecast == 0


def test_identical_publish_times_tie_break_is_deterministic():
    rows = [
        forecast(TARGET, "2026-01-14T08:00:00Z", 100),
        forecast(TARGET, "2026-01-14T08:00:00Z", 140),
        forecast(TARGET, "2026-01-14T08:00:00Z", 120),
    ]
    results = {_select(order)[0].iloc[0]["forecast_mw"] for order in (rows, rows[::-1], rows[1:] + rows[:1])}
    assert results == {140.0}


def test_each_target_is_selected_independently():
    selected, _ = _select([
        forecast("2026-01-15T12:00:00Z", "2026-01-14T08:00:00Z", 1),
        forecast("2026-01-15T13:00:00Z", "2026-01-14T08:00:00Z", 2),
        forecast("2026-01-15T13:00:00Z", "2026-01-14T07:00:00Z", 99),
        forecast("2026-01-16T00:00:00Z", "2026-01-14T08:00:00Z", 3),  # next delivery day: cutoff Jan 15 09:00
        forecast("2026-01-16T00:00:00Z", "2026-01-15T08:30:00Z", 4),
    ])
    assert dict(zip(selected["start_time"].astype(str), selected["forecast_mw"])) == {
        "2026-01-15 12:00:00+00:00": 1.0,
        "2026-01-15 13:00:00+00:00": 2.0,
        "2026-01-16 00:00:00+00:00": 4.0,
    }


def test_summer_cutoff_uses_bst():
    # delivery 2026-07-02 -> cutoff 2026-07-01 09:00 BST == 08:00 UTC
    clean, _ = normalise_forecasts(pd.DataFrame([
        forecast("2026-07-02T12:00:00Z", "2026-07-01T07:59:00Z", 1),
        forecast("2026-07-02T12:00:00Z", "2026-07-01T08:30:00Z", 2),  # 09:30 BST: too late
    ]))
    selected, _ = select_forecasts(clean, POLICY)
    assert selected.iloc[0]["forecast_mw"] == 1


def test_empty_forecasts_give_empty_selection():
    selected, report = select_forecasts(normalise_forecasts(pd.DataFrame())[0], POLICY)
    assert selected.empty and report.candidate_forecasts == 0


def _frame(actuals, forecasts, day=date(2026, 1, 15)):
    a, _ = normalise_actuals(pd.DataFrame(actuals))
    f, _ = normalise_forecasts(pd.DataFrame(forecasts))
    s, _ = select_forecasts(f, POLICY)
    return build_period_frame(a, s, day, day, POLICY)


def test_forecasts_and_actuals_are_matched_on_target_period_and_error_is_forecast_minus_actual():
    frame = _frame(
        [actual("2026-01-15T12:00:00Z", 1000), actual("2026-01-15T13:00:00Z", 2000)],
        [forecast("2026-01-15T12:00:00Z", "2026-01-14T08:00:00Z", 1200),
         forecast("2026-01-15T13:00:00Z", "2026-01-14T08:00:00Z", 1500)],
    )
    m = frame[frame["status"] == MATCHED].set_index("start_time")
    assert m.loc[pd.Timestamp("2026-01-15T12:00:00Z"), "error_mw"] == 200   # over
    assert m.loc[pd.Timestamp("2026-01-15T13:00:00Z"), "error_mw"] == -500  # under
    assert m.loc[pd.Timestamp("2026-01-15T13:00:00Z"), "abs_error_mw"] == 500
    assert m.loc[pd.Timestamp("2026-01-15T12:00:00Z"), "lead_time_hours"] == 28


def test_missing_forecast_and_missing_actual_are_flagged_not_filled():
    frame = _frame(
        [actual("2026-01-15T12:00:00Z", 1000), actual("2026-01-15T12:30:00Z", 1010)],
        [forecast("2026-01-15T12:00:00Z", "2026-01-14T08:00:00Z", 1100),
         forecast("2026-01-15T14:00:00Z", "2026-01-14T08:00:00Z", 1300)],
    )
    by_time = frame.set_index("start_time")["status"]
    assert by_time[pd.Timestamp("2026-01-15T12:00:00Z")] == MATCHED
    assert by_time[pd.Timestamp("2026-01-15T12:30:00Z")] == MISSING_FORECAST
    assert by_time[pd.Timestamp("2026-01-15T14:00:00Z")] == MISSING_ACTUAL
    assert by_time[pd.Timestamp("2026-01-15T03:00:00Z")] == NO_DATA
    row = frame[frame["status"] == MISSING_FORECAST].iloc[0]
    assert np.isnan(row["forecast_mw"]) and np.isnan(row["error_mw"])
    assert len(frame) == 48
    m = compute_metrics(frame["forecast_mw"], frame["actual_mw"])
    assert m.n == 1  # only the single fully matched period counts


def test_period_frame_covers_every_half_hour_even_with_no_data():
    frame = _frame([], [])
    assert len(frame) == 48
    assert (frame["status"] == NO_DATA).all()
