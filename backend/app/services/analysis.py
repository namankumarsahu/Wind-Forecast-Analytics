"""Application service: orchestrates load -> clean -> select -> match -> summarise.

Every endpoint goes through `AnalysisService._prepare`, so the overview, the period
explorer and the accuracy page always apply the *same* forecast-selection policy to
the *same* matched data.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from ..exceptions import ElexonUpstreamError
from ..schemas import (
    AccuracyResponse,
    ConfigResponse,
    Coverage,
    DailySummary,
    DataStatusOut,
    GenerationSummary,
    HistogramBin,
    Metrics,
    OverUnder,
    OverviewResponse,
    PeriodRow,
    PeriodsResponse,
    PolicyInfo,
    QualityReport,
    TimeSeriesPoint,
    TopError,
)
from .cleaning import CleaningReport, normalise_actuals, normalise_forecasts
from .data_provider import DataProvider, DataStatus
from .metrics import AccuracyMetrics, compute_metrics
from .policy import DecisionPolicy
from .selection import MATCHED, SelectionReport, build_period_frame, select_forecasts

UNIT = "MW"
HOURS_PER_PERIOD = 0.5
TOP_N = 10
_BIN_WIDTH_CANDIDATES = (100.0, 250.0, 500.0, 1000.0, 2000.0, 5000.0)
_MAX_BINS = 40
_RESULT_TTL_SECONDS = 300


class ScopeError(ValueError):
    """Requested dates fall outside the documented analysis scope."""


@dataclass
class Prepared:
    frame: pd.DataFrame
    status: DataStatus
    actual_report: CleaningReport
    forecast_report: CleaningReport
    selection: SelectionReport


# ----------------------------------------------------------------- tiny helpers
def _num(x) -> float | None:
    """NaN/inf/None -> None, numpy scalar -> float."""
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _ts(x) -> datetime | None:
    if x is None or pd.isna(x):
        return None
    return pd.Timestamp(x).to_pydatetime()


def _pct(part: int, whole: int) -> float | None:
    return None if whole == 0 else part / whole * 100.0


def _metrics_out(m: AccuracyMetrics) -> Metrics:
    return Metrics(n=m.n, n_dropped=m.n_dropped, mae_mw=m.mae, rmse_mw=m.rmse, mbe_mw=m.mbe, wape_pct=m.wape_pct)


def _summary(values: pd.Series, with_energy: bool = False) -> GenerationSummary:
    v = values.dropna()
    if v.empty:
        return GenerationSummary(n=0)
    return GenerationSummary(
        n=int(v.size),
        mean_mw=_num(v.mean()),
        min_mw=_num(v.min()),
        max_mw=_num(v.max()),
        total_mwh=_num(v.sum() * HOURS_PER_PERIOD) if with_energy else None,
    )


def _over_under(errors: pd.Series) -> OverUnder:
    e = errors.dropna()
    over, under = e[e > 0], e[e < 0]
    return OverUnder(
        overestimated_n=int(over.size),
        underestimated_n=int(under.size),
        exact_n=int((e == 0).sum()),
        overestimated_pct=_pct(int(over.size), int(e.size)),
        underestimated_pct=_pct(int(under.size), int(e.size)),
        mean_overestimate_mw=_num(over.mean()) if not over.empty else None,
        mean_underestimate_mw=_num(under.mean()) if not under.empty else None,
        max_overestimate_mw=_num(over.max()) if not over.empty else None,
        max_underestimate_mw=_num(under.min()) if not under.empty else None,
    )


def _coverage(frame: pd.DataFrame) -> Coverage:
    expected = len(frame)
    actual = int(frame["actual_mw"].notna().sum())
    forecast = int(frame["forecast_mw"].notna().sum())
    matched = int((frame["status"] == MATCHED).sum())
    return Coverage(
        expected_periods=expected,
        actual_periods=actual,
        forecast_periods=forecast,
        matched_periods=matched,
        forecast_coverage_pct=_pct(forecast, expected),
        matched_coverage_pct=_pct(matched, expected),
        note=(
            "Elexon WINDFOR publishes one forecast value per hour, while FUELHH actuals are "
            "half-hourly, so about half of all 30-minute periods have no forecast to compare. "
            "Metrics use only periods where both values exist; no values are interpolated."
        ),
    )


def _histogram(errors: pd.Series) -> tuple[list[HistogramBin], float | None]:
    e = errors.dropna().to_numpy(dtype="float64")
    if e.size == 0:
        return [], None
    span = float(e.max() - e.min())
    width = next((w for w in _BIN_WIDTH_CANDIDATES if span / w <= _MAX_BINS), _BIN_WIDTH_CANDIDATES[-1])
    lo = math.floor(e.min() / width) * width
    hi = (math.floor(e.max() / width) + 1) * width
    edges = np.arange(lo, hi + width, width)
    counts, edges = np.histogram(e, bins=edges)
    bins = [
        HistogramBin(lower_mw=float(edges[i]), upper_mw=float(edges[i + 1]), count=int(counts[i]))
        for i in range(len(counts))
    ]
    return bins, width


# ------------------------------------------------------------------- service
class AnalysisService:
    def __init__(
        self,
        provider: DataProvider,
        policy: DecisionPolicy,
        scope_start: date,
        scope_end: date,
    ) -> None:
        self._provider = provider
        self.policy = policy
        self.scope_start = scope_start
        self.scope_end = scope_end
        self._results: dict[tuple[date, date], tuple[float, Prepared]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ validation
    def validate_range(self, start: date, end: date) -> None:
        if start > end:
            raise ScopeError("`start` must be on or before `end`.")
        if start < self.scope_start or end > self.scope_end:
            raise ScopeError(
                f"Dates must lie within the analysis scope {self.scope_start} to {self.scope_end} "
                "(delivery dates whose purchase decisions are analysed)."
            )

    # --------------------------------------------------------------- pipeline
    def _prepare(self, start: date, end: date) -> Prepared:
        self.validate_range(start, end)
        key = (start, end)
        with self._lock:
            hit = self._results.get(key)
            if hit and time.monotonic() - hit[0] < _RESULT_TTL_SECONDS:
                return hit[1]

        loaded = self._provider.load(start, end)
        try:
            actuals, actual_report = normalise_actuals(loaded.actuals_raw)
            forecasts, forecast_report = normalise_forecasts(loaded.forecasts_raw)
        except ValueError as exc:  # unexpected Elexon schema (missing columns)
            raise ElexonUpstreamError(f"Unexpected response structure from Elexon: {exc}") from exc
        selected, selection = select_forecasts(forecasts, self.policy)
        frame = build_period_frame(actuals, selected, start, end, self.policy)
        prepared = Prepared(frame, loaded.status, actual_report, forecast_report, selection)

        with self._lock:
            if len(self._results) >= 64:
                self._results.pop(next(iter(self._results)))
            self._results[key] = (time.monotonic(), prepared)
        return prepared

    # ------------------------------------------------------------- shared bits
    def policy_info(self, example: date) -> PolicyInfo:
        return PolicyInfo(
            timezone=self.policy.timezone,
            cutoff_local_time=self.policy.cutoff_time.strftime("%H:%M"),
            days_ahead=self.policy.days_ahead,
            description=self.policy.describe(),
            example_delivery_date=example,
            example_decision_cutoff_utc=self.policy.cutoff_utc(example).to_pydatetime(),
        )

    @staticmethod
    def _data_status(status: DataStatus) -> DataStatusOut:
        if status.chunks_fetched == 0:
            source = "cache"
        elif status.chunks_from_cache == 0:
            source = "elexon-live"
        else:
            source = "mixed"
        return DataStatusOut(
            source=source,
            retrieved_at=status.oldest_retrieval,
            chunks_total=status.chunks_total,
            chunks_from_cache=status.chunks_from_cache,
            chunks_fetched=status.chunks_fetched,
            offline_mode=status.offline,
        )

    @staticmethod
    def _quality(p: Prepared) -> QualityReport:
        a, f = p.actual_report, p.forecast_report
        return QualityReport(
            actual_rows_raw=a.raw_rows,
            actual_rows_non_wind=a.non_wind_rows,
            actual_rows_invalid=a.invalid_timestamp_rows + a.invalid_value_rows,
            actual_duplicates_removed=a.duplicate_rows_removed,
            forecast_rows_raw=f.raw_rows,
            forecast_rows_invalid=f.invalid_timestamp_rows + f.invalid_value_rows,
            forecast_duplicates_removed=f.duplicate_rows_removed,
            forecast_conflicting_duplicates=f.conflicting_duplicate_groups,
            forecasts_excluded_after_cutoff=p.selection.excluded_after_cutoff,
        )

    @staticmethod
    def _matched(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["status"] == MATCHED]

    # ----------------------------------------------------------------- public
    def config(self) -> ConfigResponse:
        return ConfigResponse(
            analysis_start=self.scope_start,
            analysis_end=self.scope_end,
            unit=UNIT,
            policy=self.policy_info(self.scope_start),
        )

    def overview(self, start: date, end: date) -> OverviewResponse:
        p = self._prepare(start, end)
        frame, matched = p.frame, self._matched(p.frame)
        metrics = compute_metrics(matched["forecast_mw"], matched["actual_mw"])
        selected_pub = frame["publish_time"].dropna()
        series = [
            TimeSeriesPoint(
                start_time=_ts(r.start_time),
                actual_mw=_num(r.actual_mw),
                forecast_mw=_num(r.forecast_mw),
                forecast_publish_time=_ts(r.publish_time),
            )
            for r in frame.itertuples(index=False)
        ]
        return OverviewResponse(
            start=start,
            end=end,
            policy=self.policy_info(start),
            metrics=_metrics_out(metrics),
            coverage=_coverage(frame),
            forecast_summary=_summary(frame["forecast_mw"]),
            actual_summary=_summary(frame["actual_mw"], with_energy=True),
            over_under=_over_under(matched["error_mw"]),
            earliest_forecast_publish_time=_ts(selected_pub.min()) if not selected_pub.empty else None,
            latest_forecast_publish_time=_ts(selected_pub.max()) if not selected_pub.empty else None,
            series=series,
            data_status=self._data_status(p.status),
            quality=self._quality(p),
        )

    def periods(self, day: date) -> PeriodsResponse:
        p = self._prepare(day, day)
        frame, matched = p.frame, self._matched(p.frame)
        metrics = compute_metrics(matched["forecast_mw"], matched["actual_mw"])
        rows = [
            PeriodRow(
                settlement_period=i + 1,  # position since local midnight (46/50 on DST days)
                start_time=_ts(r.start_time),
                forecast_mw=_num(r.forecast_mw),
                actual_mw=_num(r.actual_mw),
                error_mw=_num(r.error_mw),
                abs_error_mw=_num(r.abs_error_mw),
                forecast_publish_time=_ts(r.publish_time),
                lead_time_hours=_num(r.lead_time_hours),
                decision_cutoff=_ts(r.cutoff_utc),
                status=r.status,
            )
            for i, r in enumerate(frame.itertuples(index=False))
        ]
        return PeriodsResponse(
            date=day,
            policy=self.policy_info(day),
            metrics=_metrics_out(metrics),
            coverage=_coverage(frame),
            rows=rows,
            data_status=self._data_status(p.status),
        )

    def accuracy(self, start: date, end: date) -> AccuracyResponse:
        p = self._prepare(start, end)
        frame, matched = p.frame, self._matched(p.frame)
        metrics = compute_metrics(matched["forecast_mw"], matched["actual_mw"])

        by_day = {d: g for d, g in matched.groupby("delivery_date")}
        daily: list[DailySummary] = []
        d = start
        while d <= end:
            g = by_day.get(d)
            if g is None or g.empty:
                daily.append(
                    DailySummary(
                        date=d, n=0, mae_mw=None, rmse_mw=None, mbe_mw=None, wape_pct=None,
                        mean_actual_mw=None, mean_forecast_mw=None,
                    )
                )
            else:
                m = compute_metrics(g["forecast_mw"], g["actual_mw"])
                daily.append(
                    DailySummary(
                        date=d, n=m.n, mae_mw=m.mae, rmse_mw=m.rmse, mbe_mw=m.mbe, wape_pct=m.wape_pct,
                        mean_actual_mw=_num(g["actual_mw"].mean()),
                        mean_forecast_mw=_num(g["forecast_mw"].mean()),
                    )
                )
            d += timedelta(days=1)

        bins, width = _histogram(matched["error_mw"])
        worst = matched.sort_values(["abs_error_mw", "start_time"], ascending=[False, True]).head(TOP_N)
        top = [
            TopError(
                start_time=_ts(r.start_time),
                forecast_mw=float(r.forecast_mw),
                actual_mw=float(r.actual_mw),
                error_mw=float(r.error_mw),
                abs_error_mw=float(r.abs_error_mw),
                forecast_publish_time=_ts(r.publish_time),
                direction="over" if r.error_mw > 0 else "under",
            )
            for r in worst.itertuples(index=False)
        ]
        return AccuracyResponse(
            start=start,
            end=end,
            policy=self.policy_info(start),
            metrics=_metrics_out(metrics),
            coverage=_coverage(frame),
            over_under=_over_under(matched["error_mw"]),
            daily=daily,
            histogram=bins,
            histogram_bin_width_mw=width,
            top_errors=top,
            data_status=self._data_status(p.status),
            quality=self._quality(p),
        )
