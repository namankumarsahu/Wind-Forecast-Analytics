import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import type { ConfigResponse } from "../types/api";

/** Selected delivery-date range, kept in the URL (?start=&end=) and clamped to the analysis scope. */
export function useDateRange(config: ConfigResponse | undefined, defaultMode: "day" | "month") {
  const [params, setParams] = useSearchParams();

  const clamp = (v: string | null, fallback: string) => {
    if (!config) return undefined;
    const candidate = v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : fallback;
    return candidate < config.analysis_start ? config.analysis_start : candidate > config.analysis_end ? config.analysis_end : candidate;
  };

  const sampleDay = config ? (config.analysis_start.slice(0, 8) + "15") : "";
  const defStart = defaultMode === "day" ? sampleDay : config?.analysis_start ?? "";
  const defEnd = defaultMode === "day" ? sampleDay : config?.analysis_end ?? "";

  let start = clamp(params.get("start"), defStart);
  let end = clamp(params.get("end"), defEnd);
  if (start && end && start > end) [start, end] = [end, start];

  const setRange = useCallback(
    (s: string, e: string) => {
      const next = new URLSearchParams(params);
      next.set("start", s);
      next.set("end", e);
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  return { start, end, setRange };
}
