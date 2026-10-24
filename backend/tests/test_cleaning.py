import pandas as pd
import pytest

from app.services.cleaning import normalise_actuals, normalise_forecasts

from .factories import actual, forecast


def test_actuals_are_filtered_to_wind_only():
    raw = pd.DataFrame([
        actual("2026-01-14T00:00:00Z", 1000, "WIND"),
        actual("2026-01-14T00:00:00Z", 7000, "CCGT"),
        actual("2026-01-14T00:00:00Z", 300, "NUCLEAR"),
        actual("2026-01-14T00:30:00Z", 1100, " wind "),
    ])
    df, report = normalise_actuals(raw)
    assert list(df["actual_mw"]) == [1000.0, 1100.0]
    assert report.non_wind_rows == 2


def test_actual_timestamps_are_utc_aware_and_sorted():
    raw = pd.DataFrame([
        actual("2026-01-14T01:00:00Z", 3),
        actual("2026-01-14T00:00:00Z", 1),
        actual("2026-01-14T00:30:00+00:00", 2),
    ])
    df, _ = normalise_actuals(raw)
    assert str(df["start_time"].dt.tz) == "UTC"
    assert list(df["actual_mw"]) == [1.0, 2.0, 3.0]


def test_invalid_actual_rows_are_dropped_and_counted_not_zeroed():
    raw = pd.DataFrame([
        actual("2026-01-14T00:00:00Z", None),
        actual("2026-01-14T00:30:00Z", "abc"),
        actual("2026-01-14T01:00:00Z", -5),
        actual("bad-time", 10),
        actual("2026-01-14T02:00:00Z", 0),  # zero is a legitimate wind value
    ])
    df, report = normalise_actuals(raw)
    assert list(df["actual_mw"]) == [0.0]
    assert report.invalid_value_rows == 3
    assert report.invalid_timestamp_rows == 1


def test_duplicate_actuals_latest_publish_time_wins_regardless_of_row_order():
    rows = [
        actual("2026-01-14T00:00:00Z", 1000, publish="2026-01-14T00:30:00Z"),
        actual("2026-01-14T00:00:00Z", 1111, publish="2026-01-14T06:00:00Z"),
    ]
    for ordering in (rows, rows[::-1]):
        df, report = normalise_actuals(pd.DataFrame(ordering))
        assert list(df["actual_mw"]) == [1111.0]
        assert report.duplicate_rows_removed == 1


def test_empty_inputs_return_typed_empty_frames():
    a, ra = normalise_actuals(pd.DataFrame())
    f, rf = normalise_forecasts(pd.DataFrame())
    assert a.empty and f.empty
    assert list(a.columns) == ["start_time", "actual_mw"]
    assert list(f.columns) == ["start_time", "publish_time", "forecast_mw"]


def test_missing_columns_raise_clear_error():
    with pytest.raises(ValueError, match="fuelType"):
        normalise_actuals(pd.DataFrame([{"startTime": "2026-01-14T00:00:00Z", "generation": 1}]))
    with pytest.raises(ValueError, match="publishTime"):
        normalise_forecasts(pd.DataFrame([{"startTime": "2026-01-14T00:00:00Z", "generation": 1}]))


def test_forecast_without_publish_time_is_dropped():
    raw = pd.DataFrame([
        forecast("2026-01-14T00:00:00Z", "2026-01-13T08:00:00Z", 10),
        {"startTime": "2026-01-14T00:00:00Z", "publishTime": None, "generation": 20},
    ])
    df, report = normalise_forecasts(raw)
    assert list(df["forecast_mw"]) == [10.0]
    assert report.invalid_timestamp_rows == 1


def test_exact_duplicate_forecasts_collapse_without_conflict():
    r = forecast("2026-01-14T00:00:00Z", "2026-01-13T08:00:00Z", 10)
    df, report = normalise_forecasts(pd.DataFrame([r, dict(r)]))
    assert len(df) == 1
    assert report.duplicate_rows_removed == 1
    assert report.conflicting_duplicate_groups == 0


def test_conflicting_duplicates_keep_highest_value_deterministically():
    rows = [
        forecast("2026-01-14T00:00:00Z", "2026-01-13T08:00:00Z", 10),
        forecast("2026-01-14T00:00:00Z", "2026-01-13T08:00:00Z", 30),
        forecast("2026-01-14T00:00:00Z", "2026-01-13T08:00:00Z", 20),
    ]
    for ordering in (rows, rows[::-1]):
        df, report = normalise_forecasts(pd.DataFrame(ordering))
        assert list(df["forecast_mw"]) == [30.0]
        assert report.conflicting_duplicate_groups == 1
