import { AlertTriangle, CheckCircle2, Database, Info, Loader2, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { fmtDateTime } from "../lib/format";
import type { DataStatus } from "../types/api";

export function Card({ title, subtitle, action, children, className = "" }: {
  title?: string; subtitle?: ReactNode; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 px-4 py-3 sm:px-5">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

export function Kpi({ label, value, unit, hint, tone = "default" }: {
  label: string; value: string; unit?: string; hint?: ReactNode; tone?: "default" | "good";
}) {
  return (
    <div className={`card p-4 ${tone === "good" ? "border-l-4 border-l-green-600" : "border-l-4 border-l-navy-700"}`}>
      <div className="label">{label}</div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="num text-2xl font-semibold text-slate-900">{value}</span>
        {unit && value !== "—" && <span className="text-sm text-slate-500">{unit}</span>}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function LoadingState({ message = "Loading data…", slowHint = false }: { message?: string; slowHint?: boolean }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-2 py-16 text-slate-500">
      <Loader2 className="h-6 w-6 animate-spin text-navy-600" aria-hidden />
      <p className="text-sm">{message}</p>
      {slowHint && (
        <p className="max-w-md text-center text-xs text-slate-400">
          The first request for a date range downloads the data from Elexon and caches it, so it can take
          a little longer. Later requests are served from the cache.
        </p>
      )}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <div>
          <p className="font-medium">We couldn’t load this data</p>
          <p className="mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden /> Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
      <Info className="h-5 w-5 text-slate-400" aria-hidden />
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {children && <p className="max-w-lg text-xs text-slate-500">{children}</p>}
    </div>
  );
}

export function DataStatusBadge({ status }: { status: DataStatus }) {
  const label =
    status.source === "elexon-live" ? "Retrieved live from Elexon" : status.source === "cache" ? "Served from cache" : "Cache + live Elexon";
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 font-medium text-green-800 ring-1 ring-green-200">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> {label}
      </span>
      <span className="inline-flex items-center gap-1">
        <Database className="h-3.5 w-3.5" aria-hidden />
        Data retrieved {fmtDateTime(status.retrieved_at)} · {status.chunks_total} daily chunks
        {status.offline_mode && " · offline mode"}
      </span>
    </div>
  );
}

export function PageHeader({ title, description, children }: { title: string; description: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>
      {children}
    </div>
  );
}
