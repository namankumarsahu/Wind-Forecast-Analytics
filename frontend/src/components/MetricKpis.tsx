import { fmtNumber, fmtPct, fmtSigned } from "../lib/format";
import type { Metrics } from "../types/api";
import { Kpi } from "./ui";

export default function MetricKpis({ metrics }: { metrics: Metrics }) {
  const n = `n = ${fmtNumber(metrics.n)} matched periods`;
  const mbe = metrics.mbe_mw;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Kpi label="MAE · mean absolute error" value={fmtNumber(metrics.mae_mw, 0)} unit="MW" hint={`Typical size of the miss. ${n}`} />
      <Kpi label="RMSE · root mean squared error" value={fmtNumber(metrics.rmse_mw, 0)} unit="MW" hint="Penalises large misses more than MAE" />
      <Kpi
        label="MBE · mean bias error"
        value={fmtSigned(mbe, 0)}
        unit="MW"
        hint={mbe === null ? "No valid periods" : mbe > 0 ? "Forecasts over-estimate on average" : mbe < 0 ? "Forecasts under-estimate on average" : "No average bias"}
      />
      <Kpi label="WAPE · weighted abs. % error" value={fmtPct(metrics.wape_pct, 1).replace("%", "")} unit="%" hint="Total absolute error ÷ total actual generation" tone="good" />
    </div>
  );
}
