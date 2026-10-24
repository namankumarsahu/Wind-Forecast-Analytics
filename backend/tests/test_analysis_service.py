from datetime import date

import pytest

from app.services.analysis import AnalysisService, ScopeError
from app.services.policy import DecisionPolicy

from .factories import FakeProvider


def make_service(**kwargs):
    return AnalysisService(FakeProvider(**kwargs), DecisionPolicy(), date(2026, 1, 1), date(2026, 1, 31))


def test_overview_uses_only_forecasts_available_at_the_cutoff():
    # eligible forecast = actual + 500 ; late forecast (published 09:00:01) = actual - 2000 must be ignored
    o = make_service(forecast_error=500.0).overview(date(2026, 1, 15), date(2026, 1, 15))
    m = o.metrics
    assert m.n == 24                       # hourly forecasts matched to half-hourly actuals
    assert m.mae_mw == pytest.approx(500.0)
    assert m.rmse_mw == pytest.approx(500.0)
    assert m.mbe_mw == pytest.approx(500.0)
    assert o.over_under.overestimated_n == 24 and o.over_under.underestimated_n == 0
    assert o.quality.forecasts_excluded_after_cutoff == 24
    assert o.coverage.expected_periods == 48 and o.coverage.matched_periods == 24
    assert o.coverage.forecast_coverage_pct == pytest.approx(50.0)


def test_wape_matches_hand_calculation():
    o = make_service(forecast_error=500.0).overview(date(2026, 1, 15), date(2026, 1, 15))
    # sum|err| = 24*500 ; sum actual over hourly periods = sum(10000+100h) for h in 0..23
    denom = sum(10_000 + 100 * h for h in range(24))
    assert o.metrics.wape_pct == pytest.approx(24 * 500 / denom * 100)


def test_selected_publish_time_is_exposed_for_verification():
    p = make_service().periods(date(2026, 1, 15))
    matched = [r for r in p.rows if r.status == "matched"]
    assert matched[0].forecast_publish_time.isoformat() == "2026-01-14T08:00:00+00:00"
    assert matched[0].decision_cutoff.isoformat() == "2026-01-14T09:00:00+00:00"
    assert matched[0].lead_time_hours == pytest.approx(16.0)
    assert [r.settlement_period for r in p.rows][:3] == [1, 2, 3]
    assert len(p.rows) == 48


def test_underestimates_are_negative_and_counted():
    o = make_service(forecast_error=-300.0).overview(date(2026, 1, 15), date(2026, 1, 15))
    assert o.metrics.mbe_mw == pytest.approx(-300.0)
    assert o.over_under.underestimated_n == 24
    assert o.over_under.max_underestimate_mw == pytest.approx(-300.0)


def test_accuracy_daily_histogram_and_top_errors_are_consistent_with_aggregate():
    a = make_service(forecast_error=500.0).accuracy(date(2026, 1, 10), date(2026, 1, 12))
    assert a.metrics.n == 72
    assert [d.date.isoformat() for d in a.daily] == ["2026-01-10", "2026-01-11", "2026-01-12"]
    assert all(d.n == 24 and d.mae_mw == pytest.approx(500.0) for d in a.daily)
    assert sum(b.count for b in a.histogram) == a.metrics.n
    assert len(a.top_errors) == 10 and a.top_errors[0].abs_error_mw == pytest.approx(500.0)
    assert a.top_errors[0].direction == "over"
    # ties are ordered by time: deterministic output
    times = [t.start_time for t in a.top_errors]
    assert times == sorted(times)


def test_overview_and_accuracy_agree_on_the_same_range():
    s = make_service()
    o = s.overview(date(2026, 1, 1), date(2026, 1, 5))
    a = s.accuracy(date(2026, 1, 1), date(2026, 1, 5))
    assert o.metrics == a.metrics


def test_scope_is_january_2026_only():
    s = make_service()
    for start, end in [
        (date(2025, 12, 31), date(2026, 1, 2)),
        (date(2026, 1, 31), date(2026, 2, 1)),
        (date(2026, 2, 10), date(2026, 2, 10)),
    ]:
        with pytest.raises(ScopeError):
            s.accuracy(start, end)
    with pytest.raises(ScopeError):
        s.accuracy(date(2026, 1, 10), date(2026, 1, 9))
    s.accuracy(date(2026, 1, 1), date(2026, 1, 31))  # full scope is fine


def test_no_data_yields_none_metrics_not_zero():
    class Empty:
        def load(self, start, end):
            import pandas as pd
            from app.services.data_provider import DataStatus, LoadedData
            return LoadedData(pd.DataFrame(), pd.DataFrame(), DataStatus())

    s = AnalysisService(Empty(), DecisionPolicy(), date(2026, 1, 1), date(2026, 1, 31))
    o = s.overview(date(2026, 1, 15), date(2026, 1, 15))
    assert o.metrics.n == 0
    assert o.metrics.mae_mw is None and o.metrics.wape_pct is None
    assert o.coverage.matched_periods == 0
    assert o.forecast_summary.n == 0 and o.forecast_summary.mean_mw is None
    a = s.accuracy(date(2026, 1, 15), date(2026, 1, 16))
    assert a.histogram == [] and a.top_errors == [] and all(d.n == 0 for d in a.daily)


def test_results_are_cached_between_calls():
    s = make_service()
    s.overview(date(2026, 1, 15), date(2026, 1, 15))
    s.periods(date(2026, 1, 15))
    assert len(s._provider.calls) == 1
