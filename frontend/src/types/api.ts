// Mirrors backend/app/schemas. All generation values are in MW.

export interface PolicyInfo {
  timezone: string;
  cutoff_local_time: string;
  days_ahead: number;
  description: string;
  example_delivery_date: string;
  example_decision_cutoff_utc: string;
}

export interface Metrics {
  n: number;
  n_dropped: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  wape_pct: number | null;
  unit: string;
}

export interface Coverage {
  expected_periods: number;
  actual_periods: number;
  forecast_periods: number;
  matched_periods: number;
  forecast_coverage_pct: number | null;
  matched_coverage_pct: number | null;
  note: string;
}

export interface GenerationSummary {
  n: number;
  mean_mw: number | null;
  min_mw: number | null;
  max_mw: number | null;
  total_mwh: number | null;
  unit: string;
}

export interface OverUnder {
  overestimated_n: number;
  underestimated_n: number;
  exact_n: number;
  overestimated_pct: number | null;
  underestimated_pct: number | null;
  mean_overestimate_mw: number | null;
  mean_underestimate_mw: number | null;
  max_overestimate_mw: number | null;
  max_underestimate_mw: number | null;
  unit: string;
}

export interface QualityReport {
  actual_rows_raw: number;
  actual_rows_non_wind: number;
  actual_rows_invalid: number;
  actual_duplicates_removed: number;
  forecast_rows_raw: number;
  forecast_rows_invalid: number;
  forecast_duplicates_removed: number;
  forecast_conflicting_duplicates: number;
  forecasts_excluded_after_cutoff: number;
}

export interface DataStatus {
  source: "elexon-live" | "cache" | "mixed";
  retrieved_at: string | null;
  chunks_total: number;
  chunks_from_cache: number;
  chunks_fetched: number;
  offline_mode: boolean;
}

export interface TimeSeriesPoint {
  start_time: string;
  actual_mw: number | null;
  forecast_mw: number | null;
  forecast_publish_time: string | null;
}

export interface OverviewResponse {
  start: string;
  end: string;
  policy: PolicyInfo;
  metrics: Metrics;
  coverage: Coverage;
  forecast_summary: GenerationSummary;
  actual_summary: GenerationSummary;
  over_under: OverUnder;
  earliest_forecast_publish_time: string | null;
  latest_forecast_publish_time: string | null;
  series: TimeSeriesPoint[];
  data_status: DataStatus;
  quality: QualityReport;
}

export type PeriodStatus = "matched" | "missing_forecast" | "missing_actual" | "no_data";

export interface PeriodRow {
  settlement_period: number;
  start_time: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
  abs_error_mw: number | null;
  forecast_publish_time: string | null;
  lead_time_hours: number | null;
  decision_cutoff: string;
  status: PeriodStatus;
}

export interface PeriodsResponse {
  date: string;
  policy: PolicyInfo;
  metrics: Metrics;
  coverage: Coverage;
  rows: PeriodRow[];
  data_status: DataStatus;
}

export interface DailySummary {
  date: string;
  n: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  wape_pct: number | null;
  mean_actual_mw: number | null;
  mean_forecast_mw: number | null;
}

export interface HistogramBin {
  lower_mw: number;
  upper_mw: number;
  count: number;
}

export interface TopError {
  start_time: string;
  forecast_mw: number;
  actual_mw: number;
  error_mw: number;
  abs_error_mw: number;
  forecast_publish_time: string;
  direction: "over" | "under";
}

export interface AccuracyResponse {
  start: string;
  end: string;
  policy: PolicyInfo;
  metrics: Metrics;
  coverage: Coverage;
  over_under: OverUnder;
  daily: DailySummary[];
  histogram: HistogramBin[];
  histogram_bin_width_mw: number | null;
  top_errors: TopError[];
  data_status: DataStatus;
  quality: QualityReport;
}

export interface ConfigResponse {
  analysis_start: string;
  analysis_end: string;
  unit: string;
  policy: PolicyInfo;
}
