import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import CoveragePanel from "../components/CoveragePanel";
import CutoffPanel from "../components/CutoffPanel";
import DateRangePicker from "../components/DateRangePicker";
import MetricKpis from "../components/MetricKpis";
import OverUnderPanel from "../components/OverUnderPanel";
import { Card, DataStatusBadge, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAccuracy, useConfig } from "../hooks/useApi";
import { useDateRange } from "../hooks/useDateRange";
import { fmtDateLong, fmtDateShort, fmtDateTime, fmtNumber, fmtPct, fmtSigned } from "../lib/format";

const NAVY = "#0b1d36";
const GREEN = "#15803d";
const OVER = "#c2410c";
const UNDER = "#1d4ed8";
const axis = { fontSize: 12, fill: "#475569" };

export default function Accuracy() {
  const cfg = useConfig();
  const { start, end, setRange } = useDateRange(cfg.data, "month");
  const q = useAccuracy(start, end);
  const d = q.data;

  const daily = (d?.daily ?? []).map((x) => ({ ...x, label: fmtDateShort(x.date) }));
  const hist = (d?.histogram ?? []).map((b) => ({ ...b, mid: (b.lower_mw + b.upper_mw) / 2 }));

  return (
    <>
      <PageHeader title="Accuracy Analysis" description="Quantify forecast error over a date range using the same forecast-selection policy as the rest of the application." />
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
                <div className="text-sm font-medium text-slate-900">{start === end ? fmtDateLong(start) : `${fmtDateLong(start)} – ${fmtDateLong(end)}`}</div>
              </div>
            </div>
          </Card>
          <CutoffPanel policy={cfg.data.policy} />

          {q.isError ? (
            <ErrorState error={q.error} onRetry={() => q.refetch()} />
          ) : !d ? (
            <LoadingState message="Calculating accuracy metrics…" slowHint />
          ) : (
            <>
              <DataStatusBadge status={d.data_status} />
              {d.metrics.n === 0 ? (
                <EmptyState title="No matched forecast and actual periods in this range">Metrics are undefined without data and are not shown as zero.</EmptyState>
              ) : (
                <>
                  <MetricKpis metrics={d.metrics} />

                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                    <Card title="Overestimation vs underestimation" className="lg:col-span-1">
                      <OverUnderPanel data={d.over_under} />
                    </Card>
                    <Card title="Error distribution" subtitle={`Matched periods by forecast error (forecast − actual), ${fmtNumber(d.histogram_bin_width_mw)} MW bins`} className="lg:col-span-2">
                      <div className="h-64 w-full" role="img" aria-label="Histogram of forecast errors in megawatts">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={hist} margin={{ top: 8, right: 12, bottom: 16, left: 0 }} barCategoryGap={1}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                            <XAxis dataKey="mid" tick={axis} tickFormatter={(v: number) => fmtSigned(v)} interval="preserveStartEnd" minTickGap={24} label={{ value: "Forecast error (MW)", position: "insideBottom", offset: -8, style: { fontSize: 12, fill: "#475569" } }} />
                            <YAxis tick={axis} width={48} allowDecimals={false} label={{ value: "Periods", angle: -90, position: "insideLeft", style: { fontSize: 12, fill: "#475569", textAnchor: "middle" } }} />
                            <ReferenceLine x={0} stroke="#64748b" />
                            <Tooltip
                              cursor={{ fill: "#f1f5f9" }}
                              formatter={(v) => [fmtNumber(Number(v)), "Periods"]}
                              labelFormatter={(_, p) => (p?.[0] ? `${fmtSigned(p[0].payload.lower_mw)} to ${fmtSigned(p[0].payload.upper_mw)} MW` : "")}
                            />
                            <Bar dataKey="count" isAnimationActive={false}>
                              {hist.map((b) => (
                                <Cell key={b.lower_mw} fill={b.lower_mw >= 0 ? OVER : UNDER} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        <span style={{ color: UNDER }}>■</span> under-forecast (negative error) &nbsp; <span style={{ color: OVER }}>■</span> over-forecast (positive error)
                      </p>
                    </Card>
                  </div>

                  <Card title="Daily accuracy" subtitle="MAE (bars) and RMSE (line) per delivery day, MW. Days without matched periods are blank.">
                    <div className="h-72 w-full" role="img" aria-label="Daily MAE and RMSE in megawatts">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={daily} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="label" tick={axis} interval="preserveStartEnd" minTickGap={16} />
                          <YAxis tick={axis} width={56} tickFormatter={(v: number) => fmtNumber(v)} label={{ value: "MW", angle: -90, position: "insideLeft", style: { fontSize: 12, fill: "#475569" } }} />
                          <Tooltip formatter={(v, name) => [`${fmtNumber(Number(v))} MW`, String(name)]} />
                          <Bar dataKey="mae_mw" name="MAE" fill={NAVY} isAnimationActive={false} />
                          <Line dataKey="rmse_mw" name="RMSE" stroke={GREEN} strokeWidth={2} dot={{ r: 2.5 }} isAnimationActive={false} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="mt-1 text-xs text-slate-500"><span style={{ color: NAVY }}>■</span> MAE &nbsp; <span style={{ color: GREEN }}>━</span> RMSE</p>
                  </Card>

                  <Card title="Daily bias (MBE)" subtitle="Average signed error per day. Above zero: forecasts were too high. Below zero: too low.">
                    <div className="h-56 w-full" role="img" aria-label="Daily mean bias error in megawatts">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={daily} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="label" tick={axis} interval="preserveStartEnd" minTickGap={16} />
                          <YAxis tick={axis} width={56} tickFormatter={(v: number) => fmtNumber(v)} />
                          <ReferenceLine y={0} stroke="#64748b" />
                          <Tooltip formatter={(v) => [`${fmtSigned(Number(v))} MW`, "MBE"]} />
                          <Bar dataKey="mbe_mw" isAnimationActive={false}>
                            {daily.map((x) => (
                              <Cell key={x.date} fill={(x.mbe_mw ?? 0) >= 0 ? OVER : UNDER} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>

                  <Card title="Largest forecast errors" subtitle="The 10 matched periods with the biggest absolute error, with the publication time of the forecast that was used.">
                    <div className="-mx-4 overflow-x-auto sm:-mx-5">
                      <table className="min-w-full text-sm">
                        <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                          <tr>
                            <th scope="col" className="px-3 py-2 text-left font-semibold">#</th>
                            <th scope="col" className="px-3 py-2 text-left font-semibold">Target period (UK)</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Forecast MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Actual MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Error MW</th>
                            <th scope="col" className="px-3 py-2 text-left font-semibold">Direction</th>
                            <th scope="col" className="px-3 py-2 text-left font-semibold">Forecast published</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {d.top_errors.map((t, i) => (
                            <tr key={t.start_time} className="hover:bg-slate-50">
                              <td className="num px-3 py-2 text-slate-400">{i + 1}</td>
                              <td className="num whitespace-nowrap px-3 py-2 font-medium text-slate-900">{fmtDateTime(t.start_time)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(t.forecast_mw)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(t.actual_mw)}</td>
                              <td className={`num px-3 py-2 text-right font-medium ${t.direction === "over" ? "text-orange-700" : "text-blue-700"}`}>{fmtSigned(t.error_mw)}</td>
                              <td className="px-3 py-2">{t.direction === "over" ? "▲ Over-forecast" : "▼ Under-forecast"}</td>
                              <td className="num whitespace-nowrap px-3 py-2 text-slate-600">{fmtDateTime(t.forecast_publish_time)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>

                  <Card title="Daily summary table">
                    <div className="-mx-4 overflow-x-auto sm:-mx-5">
                      <table className="min-w-full text-sm">
                        <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                          <tr>
                            <th scope="col" className="px-3 py-2 text-left font-semibold">Date</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Periods</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">MAE MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">RMSE MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">MBE MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">WAPE</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Mean actual MW</th>
                            <th scope="col" className="px-3 py-2 text-right font-semibold">Mean forecast MW</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {d.daily.map((x) => (
                            <tr key={x.date} className="hover:bg-slate-50">
                              <td className="num whitespace-nowrap px-3 py-2 font-medium text-slate-900">{fmtDateLong(x.date)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(x.n)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(x.mae_mw)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(x.rmse_mw)}</td>
                              <td className="num px-3 py-2 text-right">{fmtSigned(x.mbe_mw)}</td>
                              <td className="num px-3 py-2 text-right">{fmtPct(x.wape_pct)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(x.mean_actual_mw)}</td>
                              <td className="num px-3 py-2 text-right">{fmtNumber(x.mean_forecast_mw)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>

                  <Card title="Coverage">
                    <CoveragePanel coverage={d.coverage} />
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      )}
    </>
  );
}
