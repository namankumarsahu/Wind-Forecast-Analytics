import { fmtNumber, fmtPct } from "../lib/format";
import type { Coverage } from "../types/api";

export default function CoveragePanel({ coverage }: { coverage: Coverage }) {
  const rows: [string, number, string][] = [
    ["30-minute periods in selection", coverage.expected_periods, ""],
    ["Periods with actual generation", coverage.actual_periods, ""],
    ["Periods with an eligible forecast", coverage.forecast_periods, fmtPct(coverage.forecast_coverage_pct)],
    ["Valid matched periods (used for metrics)", coverage.matched_periods, fmtPct(coverage.matched_coverage_pct)],
  ];
  return (
    <div>
      <dl className="divide-y divide-slate-100 text-sm">
        {rows.map(([label, value, pct]) => (
          <div key={label} className="flex items-center justify-between gap-3 py-2">
            <dt className="text-slate-600">{label}</dt>
            <dd className="num font-medium text-slate-900">
              {fmtNumber(value)} {pct && <span className="ml-1 text-xs font-normal text-slate-500">({pct})</span>}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-slate-500">{coverage.note}</p>
    </div>
  );
}
