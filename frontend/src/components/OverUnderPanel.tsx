import { fmtNumber, fmtPct, fmtSigned } from "../lib/format";
import type { OverUnder } from "../types/api";

const OVER = "#c2410c";
const UNDER = "#1d4ed8";

export default function OverUnderPanel({ data }: { data: OverUnder }) {
  const total = data.overestimated_n + data.underestimated_n + data.exact_n;
  if (total === 0) return <p className="text-sm text-slate-500">No matched periods to analyse.</p>;
  const w = (n: number) => `${(n / total) * 100}%`;
  return (
    <div className="space-y-4">
      <div>
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${fmtPct(data.overestimated_pct)} over-forecast, ${fmtPct(data.underestimated_pct)} under-forecast`}>
          <div style={{ width: w(data.overestimated_n), background: OVER }} />
          <div style={{ width: w(data.exact_n), background: "#94a3b8" }} />
          <div style={{ width: w(data.underestimated_n), background: UNDER }} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md border border-slate-200 p-3">
          <div className="flex items-center gap-1.5 font-medium" style={{ color: OVER }}>▲ Overestimated</div>
          <div className="num mt-1 text-xl font-semibold text-slate-900">{fmtPct(data.overestimated_pct)}</div>
          <div className="text-xs text-slate-500">{fmtNumber(data.overestimated_n)} periods (forecast &gt; actual)</div>
          <dl className="mt-2 space-y-0.5 text-xs text-slate-600">
            <div className="flex justify-between"><dt>Mean error</dt><dd className="num">{fmtSigned(data.mean_overestimate_mw)} MW</dd></div>
            <div className="flex justify-between"><dt>Largest</dt><dd className="num">{fmtSigned(data.max_overestimate_mw)} MW</dd></div>
          </dl>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="flex items-center gap-1.5 font-medium" style={{ color: UNDER }}>▼ Underestimated</div>
          <div className="num mt-1 text-xl font-semibold text-slate-900">{fmtPct(data.underestimated_pct)}</div>
          <div className="text-xs text-slate-500">{fmtNumber(data.underestimated_n)} periods (forecast &lt; actual)</div>
          <dl className="mt-2 space-y-0.5 text-xs text-slate-600">
            <div className="flex justify-between"><dt>Mean error</dt><dd className="num">{fmtSigned(data.mean_underestimate_mw)} MW</dd></div>
            <div className="flex justify-between"><dt>Largest</dt><dd className="num">{fmtSigned(data.max_underestimate_mw)} MW</dd></div>
          </dl>
        </div>
      </div>
      {data.exact_n > 0 && <p className="text-xs text-slate-500">{fmtNumber(data.exact_n)} periods matched exactly.</p>}
    </div>
  );
}
