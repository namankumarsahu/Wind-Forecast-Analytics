import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState } from "react";
import CutoffPanel from "../components/CutoffPanel";
import DateRangePicker from "../components/DateRangePicker";
import { Card, DataStatusBadge, EmptyState, ErrorState, Kpi, LoadingState, PageHeader } from "../components/ui";
import { useConfig, usePeriods } from "../hooks/useApi";
import { useDateRange } from "../hooks/useDateRange";
import { fmtDateLong, fmtDateTime, fmtLead, fmtNumber, fmtSigned, fmtTime } from "../lib/format";
import type { PeriodRow, PeriodStatus } from "../types/api";

type SortKey = "settlement_period" | "forecast_mw" | "actual_mw" | "error_mw" | "abs_error_mw" | "forecast_publish_time" | "lead_time_hours" | "status";

const STATUS_LABEL: Record<PeriodStatus, string> = {
  matched: "Matched",
  missing_forecast: "No forecast",
  missing_actual: "No actual",
  no_data: "No data",
};
const STATUS_STYLE: Record<PeriodStatus, string> = {
  matched: "bg-green-50 text-green-800 ring-green-200",
  missing_forecast: "bg-slate-100 text-slate-600 ring-slate-200",
  missing_actual: "bg-amber-50 text-amber-800 ring-amber-200",
  no_data: "bg-slate-100 text-slate-500 ring-slate-200",
};

function value(row: PeriodRow, key: SortKey): number | string | null {
  return row[key];
}

export default function Explorer() {
  const cfg = useConfig();
  const { start, setRange } = useDateRange(cfg.data, "day");
  const day = start;
  const q = usePeriods(day);
  const [sortKey, setSortKey] = useState<SortKey>("settlement_period");
  const [asc, setAsc] = useState(true);
  const [matchedOnly, setMatchedOnly] = useState(false);

  const rows = useMemo(() => {
    const base = (q.data?.rows ?? []).filter((r) => !matchedOnly || r.status === "matched");
    return [...base].sort((a, b) => {
      const x = value(a, sortKey);
      const y = value(b, sortKey);
      if (x === null && y === null) return a.settlement_period - b.settlement_period;
      if (x === null) return 1; // missing values always last
      if (y === null) return -1;
      const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
      const ordered = c !== 0 ? c : a.settlement_period - b.settlement_period;
      return asc ? ordered : -ordered;
    });
  }, [q.data, sortKey, asc, matchedOnly]);

  const toggle = (key: SortKey) => {
    if (key === sortKey) setAsc(!asc);
    else { setSortKey(key); setAsc(true); }
  };

  const Th = ({ k, children, align = "right" }: { k: SortKey; children: string; align?: "left" | "right" }) => (
    <th scope="col" className={`whitespace-nowrap px-3 py-2 ${align === "left" ? "text-left" : "text-right"}`} aria-sort={sortKey === k ? (asc ? "ascending" : "descending") : "none"}>
      <button className={`inline-flex items-center gap-1 font-semibold hover:text-navy-700 ${align === "right" ? "flex-row-reverse" : ""}`} onClick={() => toggle(k)}>
        {children}
        {sortKey === k ? (asc ? <ArrowUp className="h-3.5 w-3.5" aria-hidden /> : <ArrowDown className="h-3.5 w-3.5" aria-hidden />) : <ArrowUpDown className="h-3.5 w-3.5 text-slate-300" aria-hidden />}
      </button>
    </th>
  );

  const d = q.data;
  return (
    <>
      <PageHeader title="Forecast Explorer" description="Inspect every 30-minute period of a delivery day: which forecast was used, when it was published, and how far it was from the actual." />
      {cfg.isError ? (
        <ErrorState error={cfg.error} onRetry={() => cfg.refetch()} />
      ) : !cfg.data || !day ? (
        <LoadingState message="Connecting to the analytics service…" />
      ) : (
        <div className="space-y-5">
          <Card>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <DateRangePicker config={cfg.data} start={day} end={day} onChange={(s) => setRange(s, s)} singleDayOnly />
              <div className="text-right">
                <div className="label">Delivery date</div>
                <div className="text-sm font-medium text-slate-900">{fmtDateLong(day)}</div>
              </div>
            </div>
          </Card>
          <CutoffPanel policy={cfg.data.policy} />

          {q.isError ? (
            <ErrorState error={q.error} onRetry={() => q.refetch()} />
          ) : !d ? (
            <LoadingState message="Retrieving periods…" slowHint />
          ) : (
            <>
              <DataStatusBadge status={d.data_status} />
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Kpi label="Matched periods" value={fmtNumber(d.metrics.n)} hint={`of ${fmtNumber(d.coverage.expected_periods)} half-hours`} />
                <Kpi label="MAE" value={fmtNumber(d.metrics.mae_mw)} unit="MW" />
                <Kpi label="MBE (bias)" value={fmtSigned(d.metrics.mbe_mw)} unit="MW" />
                <Kpi label="WAPE" value={d.metrics.wape_pct === null ? "—" : fmtNumber(d.metrics.wape_pct, 1)} unit="%" tone="good" />
              </div>

              <Card
                title="Periods"
                subtitle="Error = forecast − actual (positive: over-forecast, negative: under-forecast). Forecasts are published hourly, so half-hour periods between them have none."
                action={
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-green-700" checked={matchedOnly} onChange={(e) => setMatchedOnly(e.target.checked)} />
                    Matched periods only
                  </label>
                }
              >
                {d.metrics.n === 0 && (
                  <div className="mb-4">
                    <EmptyState title="No matched periods on this date">No forecast was available at the cutoff, or actual generation is not yet published. Nothing has been estimated.</EmptyState>
                  </div>
                )}
                {rows.length === 0 ? (
                  <EmptyState title="No rows to show" />
                ) : (
                  <div className="-mx-4 overflow-x-auto sm:-mx-5">
                    <table className="min-w-full text-sm">
                      <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                        <tr>
                          <Th k="settlement_period" align="left">Target period (UK)</Th>
                          <Th k="forecast_mw">Forecast MW</Th>
                          <Th k="actual_mw">Actual MW</Th>
                          <Th k="error_mw">Error MW</Th>
                          <Th k="abs_error_mw">Abs. error MW</Th>
                          <Th k="forecast_publish_time" align="left">Forecast published</Th>
                          <Th k="lead_time_hours">Lead time</Th>
                          <th scope="col" className="whitespace-nowrap px-3 py-2 text-left font-semibold">Decision cutoff</th>
                          <Th k="status" align="left">Status</Th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {rows.map((r) => (
                          <tr key={r.start_time} className="hover:bg-slate-50">
                            <td className="num whitespace-nowrap px-3 py-2 font-medium text-slate-900">{fmtTime(r.start_time)} <span className="text-xs font-normal text-slate-400">SP{r.settlement_period}</span></td>
                            <td className="num px-3 py-2 text-right">{fmtNumber(r.forecast_mw)}</td>
                            <td className="num px-3 py-2 text-right">{fmtNumber(r.actual_mw)}</td>
                            <td className={`num px-3 py-2 text-right font-medium ${r.error_mw === null ? "" : r.error_mw > 0 ? "text-orange-700" : r.error_mw < 0 ? "text-blue-700" : ""}`}>
                              {r.error_mw === null ? "—" : `${r.error_mw > 0 ? "▲ " : r.error_mw < 0 ? "▼ " : ""}${fmtSigned(r.error_mw)}`}
                            </td>
                            <td className="num px-3 py-2 text-right">{fmtNumber(r.abs_error_mw)}</td>
                            <td className="num whitespace-nowrap px-3 py-2 text-slate-700">{fmtDateTime(r.forecast_publish_time)}</td>
                            <td className="num px-3 py-2 text-right text-slate-600">{fmtLead(r.lead_time_hours)}</td>
                            <td className="num whitespace-nowrap px-3 py-2 text-slate-600">{fmtDateTime(r.decision_cutoff)}</td>
                            <td className="px-3 py-2">
                              <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${STATUS_STYLE[r.status]}`}>{STATUS_LABEL[r.status]}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      )}
    </>
  );
}
