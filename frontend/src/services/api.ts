import type { AccuracyResponse, ConfigResponse, OverviewResponse, PeriodsResponse } from "../types/api";

const BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function explain(status: number, detail: string): string {
  switch (status) {
    case 422:
      return detail || "The selected dates are not valid for this analysis.";
    case 502:
      return `The Elexon data service returned an error. ${detail}`.trim();
    case 503:
      return `Required data is not available right now. ${detail}`.trim();
    case 504:
      return "Elexon did not respond in time. Please try again in a moment.";
    default:
      return detail || `Request failed (HTTP ${status}).`;
  }
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => v && query.set(k, v));
  const qs = query.toString();
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("Cannot reach the analytics backend. Check your connection or that the API is running.", 0);
  }
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : "";
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(explain(response.status, detail), response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  config: () => get<ConfigResponse>("/api/config"),
  overview: (start: string, end: string) =>
    start === end ? get<OverviewResponse>("/api/overview", { date: start }) : get<OverviewResponse>("/api/overview", { start, end }),
  periods: (date: string) => get<PeriodsResponse>("/api/periods", { date }),
  accuracy: (start: string, end: string) => get<AccuracyResponse>("/api/accuracy", { start, end }),
};
