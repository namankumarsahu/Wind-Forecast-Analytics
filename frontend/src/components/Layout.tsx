import { LayoutDashboard, Search, TrendingUp, Wind } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/explorer", label: "Forecast Explorer", icon: Search },
  { to: "/accuracy", label: "Accuracy Analysis", icon: TrendingUp },
];

export default function Layout() {
  const { search } = useLocation();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-navy-900 text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-green-600">
              <Wind className="h-5 w-5" aria-hidden />
            </span>
            <div className="leading-tight">
              <div className="text-base font-semibold">Wind Forecast Analytics</div>
              <div className="text-[11px] text-navy-200">UK day-ahead procurement · national wind · Elexon BMRS</div>
            </div>
          </div>
          <nav aria-label="Main" className="-mb-px flex gap-1 overflow-x-auto">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={{ pathname: to, search: to === "/explorer" ? "" : search }}
                end={to === "/"}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? "bg-white/15 text-white" : "text-navy-100 hover:bg-white/10"
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <p className="mx-auto max-w-7xl px-4 py-4 text-xs text-slate-500 sm:px-6">
          Source: Elexon BMRS (WINDFOR forecasts, FUELHH actuals). All generation values are in MW (megawatts).
          Errors are forecast − actual: positive = over-forecast, negative = under-forecast.
          Decision-cutoff assumptions are documented in the README.
        </p>
      </footer>
    </div>
  );
}
