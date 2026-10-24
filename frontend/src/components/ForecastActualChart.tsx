import { useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtDateTime, fmtDay, fmtNumber, fmtSigned, fmtTime } from "../lib/format";
import type { TimeSeriesPoint } from "../types/api";

const ACTUAL = "#0b1d36";
const FORECAST = "#15803d";

interface Point {
  t: number;
  actual: number | null;
  forecast: number | null;
  published: string | null;
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Point }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const err = p.forecast !== null && p.actual !== null ? p.forecast - p.actual : null;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 text-xs shadow-md">
      <div className="mb-1 font-semibold text-slate-900">{fmtDateTime(new Date(p.t).toISOString())}</div>
      <div className="num space-y-0.5">
        <div><span style={{ color: ACTUAL }}>●</span> Actual: {fmtNumber(p.actual)} MW</div>
        <div><span style={{ color: FORECAST }}>●</span> Forecast: {p.forecast === null ? "none at this time" : `${fmtNumber(p.forecast)} MW`}</div>
        {err !== null && <div>Error: {fmtSigned(err)} MW</div>}
        {p.published && <div className="text-slate-500">Forecast published {fmtDateTime(p.published)}</div>}
      </div>
    </div>
  );
}

export default function ForecastActualChart({ series, singleDay }: { series: TimeSeriesPoint[]; singleDay: boolean }) {
  const data = useMemo<Point[]>(
    () => series.map((s) => ({ t: Date.parse(s.start_time), actual: s.actual_mw, forecast: s.forecast_mw, published: s.forecast_publish_time })),
    [series],
  );
  const tick = (t: number) => (singleDay ? fmtTime(new Date(t).toISOString()) : fmtDay(new Date(t).toISOString()));

  return (
    <div role="img" aria-label="Line chart of selected forecast and actual wind generation in megawatts over time" className="h-72 w-full sm:h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} tick={{ fontSize: 12, fill: "#475569" }} minTickGap={32} />
          <YAxis tickFormatter={(v: number) => fmtNumber(v)} tick={{ fontSize: 12, fill: "#475569" }} width={64} label={{ value: "Generation (MW)", angle: -90, position: "insideLeft", offset: 4, style: { fontSize: 12, fill: "#475569", textAnchor: "middle" } }} />
          <Tooltip content={<ChartTooltip />} />
          <Legend verticalAlign="top" height={32} iconType="plainline" />
          <Line dataKey="actual" name="Actual generation (FUELHH)" stroke={ACTUAL} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          <Line dataKey="forecast" name="Forecast at decision cutoff (WINDFOR)" stroke={FORECAST} strokeWidth={2} strokeDasharray="6 3" dot={singleDay ? { r: 2.5 } : false} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
