const TZ = "Europe/London";

export const MW = "MW";

export function fmtNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtSigned(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const s = fmtNumber(Math.abs(value), digits);
  return value > 0 ? `+${s}` : value < 0 ? `−${s}` : s;
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? "—" : `${fmtNumber(value, digits)}%`;
}

const dateTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ, day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
});
const timeOnly = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });
const dayOnly = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "numeric", month: "short" });
const dayLong = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric", month: "long", year: "numeric" });

export const fmtDateTime = (iso: string | null | undefined) => (iso ? dateTime.format(new Date(iso)) : "—");
export const fmtTime = (iso: string) => timeOnly.format(new Date(iso));
export const fmtDay = (iso: string) => dayOnly.format(new Date(iso));
/** Format a YYYY-MM-DD string (no timezone shifting). */
export const fmtDateLong = (ymd: string) => dayLong.format(new Date(`${ymd}T12:00:00Z`));
export const fmtDateShort = (ymd: string) => dayOnly.format(new Date(`${ymd}T12:00:00Z`));

export function fmtLead(hours: number | null | undefined): string {
  return hours === null || hours === undefined ? "—" : `${fmtNumber(hours, 1)} h`;
}

export function addDays(ymd: string, days: number): string {
  const d = new Date(`${ymd}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
