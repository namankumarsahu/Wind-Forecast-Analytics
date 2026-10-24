import { Clock } from "lucide-react";
import { fmtDateTime, fmtDateShort } from "../lib/format";
import type { PolicyInfo } from "../types/api";

export default function CutoffPanel({ policy, earliest, latest }: { policy: PolicyInfo; earliest?: string | null; latest?: string | null }) {
  return (
    <div className="flex gap-3 rounded-lg border border-navy-100 bg-navy-50 p-4 text-sm text-navy-800">
      <Clock className="mt-0.5 h-5 w-5 shrink-0 text-navy-600" aria-hidden />
      <div className="space-y-1">
        <p className="font-semibold">
          Decision cutoff: {policy.cutoff_local_time} {policy.timezone}, {policy.days_ahead === 1 ? "the day before delivery" : `${policy.days_ahead} days before delivery`}
        </p>
        <p>
          For each 30-minute target period we use the <strong>latest forecast published at or before the cutoff</strong>;
          later forecasts are ignored, because they were not available when the purchase was made.
          Example: delivery on {fmtDateShort(policy.example_delivery_date)} → cutoff {fmtDateTime(policy.example_decision_cutoff_utc)}.
        </p>
        {earliest && latest && (
          <p className="text-navy-600">
            Selected forecasts in this view were published between {fmtDateTime(earliest)} and {fmtDateTime(latest)}.
          </p>
        )}
      </div>
    </div>
  );
}
