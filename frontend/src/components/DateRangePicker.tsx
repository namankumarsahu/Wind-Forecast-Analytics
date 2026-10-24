import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { addDays } from "../lib/format";
import type { ConfigResponse } from "../types/api";

interface Props {
  config: ConfigResponse;
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
  /** Explorer only needs a single day. */
  singleDayOnly?: boolean;
}

export default function DateRangePicker({ config, start, end, onChange, singleDayOnly = false }: Props) {
  const { analysis_start: min, analysis_end: max } = config;
  const isDay = start === end;
  const clamp = (d: string) => (d < min ? min : d > max ? max : d);

  const setStart = (v: string) => v && onChange(clamp(v), end < v ? clamp(v) : end);
  const setEnd = (v: string) => v && onChange(start > v ? clamp(v) : start, clamp(v));

  return (
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Date selection">
      {!singleDayOnly && (
        <div className="inline-flex rounded-md border border-slate-300 bg-white p-0.5 text-sm shadow-sm" role="group" aria-label="Selection mode">
          <button className={`rounded px-3 py-1.5 font-medium ${isDay ? "bg-navy-800 text-white" : "text-slate-600 hover:bg-slate-100"}`} onClick={() => onChange(start, start)} aria-pressed={isDay}>
            Single day
          </button>
          <button className={`rounded px-3 py-1.5 font-medium ${!isDay ? "bg-navy-800 text-white" : "text-slate-600 hover:bg-slate-100"}`} onClick={() => onChange(min, max)} aria-pressed={!isDay}>
            Date range
          </button>
        </div>
      )}

      {isDay ? (
        <div className="flex items-end gap-1">
          <button className="btn px-2" aria-label="Previous day" disabled={start <= min} onClick={() => { const d = addDays(start, -1); onChange(d, d); }}>
            <ChevronLeft className="h-4 w-4" />
          </button>
          <label className="flex flex-col gap-1">
            <span className="label">Delivery date</span>
            <input type="date" className="input num" min={min} max={max} value={start} onChange={(e) => e.target.value && onChange(clamp(e.target.value), clamp(e.target.value))} />
          </label>
          <button className="btn px-2" aria-label="Next day" disabled={start >= max} onClick={() => { const d = addDays(start, 1); onChange(d, d); }}>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="label">From</span>
            <input type="date" className="input num" min={min} max={max} value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="label">To</span>
            <input type="date" className="input num" min={min} max={max} value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button className="btn" onClick={() => onChange(min, max)}>
            <CalendarDays className="h-4 w-4" aria-hidden /> Full month
          </button>
        </div>
      )}
      <p className="pb-2 text-xs text-slate-500">Scope: {min} to {max}</p>
    </div>
  );
}
