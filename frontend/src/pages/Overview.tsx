import { RefreshCw } from "lucide-react";
import CoveragePanel from "../components/CoveragePanel";
import CutoffPanel from "../components/CutoffPanel";
import DateRangePicker from "../components/DateRangePicker";
import ForecastActualChart from "../components/ForecastActualChart";
import MetricKpis from "../components/MetricKpis";
import OverUnderPanel from "../components/OverUnderPanel";
import { Card, DataStatusBadge, EmptyState, ErrorState, Kpi, LoadingState, PageHeader } from "../components/ui";
import { useConfig, useOverview } from "../hooks/useApi";
import { useDateRange } from "../hooks/useDateRange";
import { fmtDateLong, fmtNumber } from "../lib/format";
import type { GenerationSummary } from "../types/api";

function SummaryList({ title, summary, note }: { title: string; summary: GenerationSummary; note: string }) {
  const rows: [string, string][] = [
    ["Mean", `${fmtNumber(summary.mean_mw)} MW`],
    ["Peak", `${fmtNumber(summary.max_mw)} MW`],
    ["Minimum", `${fmtNumber(summary.min_mw)} MW`],
  ];
  if (summary.total_mwh !== null) rows.push(["Energy", `${fmtNumber(summary.total_mwh / 1000, 1)} GWh`]);
  rows.push(["Periods", fmtNumber(summary.n)]);
  return (
    <Card title={title} subtitle={note}>
      {summary.n === 0 ? (
        <p className="text-sm text-slate-500">No data for this selection.</p>
      ) : (
        <dl className="divide-y divide-slate-100 text-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between py-1.5">
              <dt className="text-slate-600">{k}</dt>
              <dd className="num font-medium text-slate-900">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}

export default function Overview() {
  const cfg = useConfig();
  const { start, end, setRange } = useDateRange(cfg.data, "day");
  const q = useOverview(start, end);
  const data = q.data;
  const label = start && end ? (start === end ? fmtDateLong(start) : `${fmtDateLong(start)} – ${fmtDateLong(end)}`) : "";

  return (
    <>
      <PageHeader
        title="Overview"
        description="How good was the wind forecast that was actually available when day-ahead electricity was purchased?"
      >
        {q.isFetching && data && (
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500" role="status">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden /> Updating…
          </span>
        )}
      </PageHeader>

      {cfg.isError ? (
        <ErrorState error={cfg.error} onRetry={() => cfg.refetch()} />
      ) : !cfg.data || !start || !end ? (
        <LoadingState message="Connecting to the analytics service…" />
      ) : (
        <div className="space-y-5">
          <Card>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <DateRangePicker config={cfg.data} start={start} end={end} onChange={setRange} />
              <div className="text-right">
                <div className="label">Delivery period analysed</div>
                <div className="text-sm font-medium text-slate-900">{label}</div>
              </div>
            </div>
          </Card>

          <CutoffPanel policy={cfg.data.policy} earliest={data?.earliest_forecast_publish_time} latest={data?.latest_forecast_publish_time} />

          {q.isError ? (
            <ErrorState error={q.error} onRetry={() => q.refetch()} />
          ) : !data ? (
            <LoadingState message="Retrieving forecasts and actuals from Elexon…" slowHint />
          ) : (
            <>
              <DataStatusBadge status={data.data_status} />

              {data.metrics.n === 0 && (
                <EmptyState title="No matched forecast and actual periods for this selection">
                  Either no forecast was published before the decision cutoff, or Elexon has no actual generation for these periods yet.
                  No values have been estimated or filled in.
                </EmptyState>
              )}

              <MetricKpis metrics={data.metrics} />

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Kpi label="Valid matched periods" value={fmtNumber(data.coverage.matched_periods)} hint={`of ${fmtNumber(data.coverage.expected_periods)} half-hours in selection`} />
                <Kpi label="Forecast coverage" value={data.coverage.forecast_coverage_pct === null ? "—" : fmtNumber(data.coverage.forecast_coverage_pct, 1)} unit="%" hint="Periods with an eligible forecast (hourly forecast resolution)" />
                <Kpi label="Matched coverage" value={data.coverage.matched_coverage_pct === null ? "—" : fmtNumber(data.coverage.matched_coverage_pct, 1)} unit="%" hint="Periods with both forecast and actual" />
              </div>

              <Card
                title="Forecast vs actual wind generation"
                subtitle="Megawatts (MW) per 30-minute period, UK time. Forecast = latest forecast published before the decision cutoff."
              >
                {data.series.every((p) => p.actual_mw === null && p.forecast_mw === null) ? (
                  <EmptyState title="No generation data available for this selection" />
                ) : (
                  <ForecastActualChart series={data.series} singleDay={start === end} />
                )}
              </Card>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                <SummaryList title="Forecast generation summary" summary={data.forecast_summary} note="Selected forecast values (hourly), MW" />
                <SummaryList title="Actual generation summary" summary={data.actual_summary} note="Outturn, 30-minute periods, MW" />
                <Card title="Overestimation vs underestimation" subtitle="Share of matched periods by direction of error">
                  <OverUnderPanel data={data.over_under} />
                </Card>
              </div>

              <Card title="Coverage and data quality">
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <CoveragePanel coverage={data.coverage} />
                  <div>
                    <h3 className="text-sm font-medium text-slate-900">Records handled by the pipeline</h3>
                    <ul className="mt-2 space-y-1 text-sm text-slate-600">
                      <li>Forecasts published after the cutoff and excluded: <b className="num">{fmtNumber(data.quality.forecasts_excluded_after_cutoff)}</b></li>
                      <li>Non-wind actual rows ignored: <b className="num">{fmtNumber(data.quality.actual_rows_non_wind)}</b></li>
                      <li>Invalid rows dropped (actual / forecast): <b className="num">{fmtNumber(data.quality.actual_rows_invalid)} / {fmtNumber(data.quality.forecast_rows_invalid)}</b></li>
                      <li>Duplicates removed (actual / forecast): <b className="num">{fmtNumber(data.quality.actual_duplicates_removed)} / {fmtNumber(data.quality.forecast_duplicates_removed)}</b></li>
                      <li>Conflicting duplicate forecasts resolved: <b className="num">{fmtNumber(data.quality.forecast_conflicting_duplicates)}</b></li>
                    </ul>
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
      )}
    </>
  );
}
