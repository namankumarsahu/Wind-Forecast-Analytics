"""Deterministic SYNTHETIC records for unit tests only.

Never used by the running application: production analysis uses real Elexon data.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd

from app.services.data_provider import DataStatus, LoadedData


def actual(start: str, mw, fuel: str = "WIND", publish: str | None = None) -> dict:
    rec = {"dataset": "FUELHH", "fuelType": fuel, "startTime": start, "generation": mw}
    if publish:
        rec["publishTime"] = publish
    return rec


def forecast(start: str, publish: str, mw) -> dict:
    return {"dataset": "WINDFOR", "startTime": start, "publishTime": publish, "generation": mw}


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def winter_day(day: date, forecast_error: float = 500.0, late_error: float = -2000.0):
    """One January delivery day (UTC == UK time).

    actual(h:mm) = 10_000 + 100*hour  (half-hourly)
    forecast published 08:00 the day before (eligible): actual + forecast_error  (hourly)
    forecast published 09:00:01 the day before (too late): actual + late_error    (hourly)
    """
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    decision = midnight - timedelta(days=1)
    early = iso(decision.replace(hour=8))
    late = iso(decision.replace(hour=9, second=1))
    actuals, forecasts = [], []
    for k in range(48):
        t = midnight + timedelta(minutes=30 * k)
        a = 10_000 + 100 * t.hour
        actuals.append(actual(iso(t), a))
        if t.minute == 0:
            forecasts.append(forecast(iso(t), early, a + forecast_error))
            forecasts.append(forecast(iso(t), late, a + late_error))
    return actuals, forecasts


class FakeProvider:
    """Serves synthetic January days; records the ranges it was asked for."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list[tuple[date, date]] = []

    def load(self, start: date, end: date) -> LoadedData:
        self.calls.append((start, end))
        actuals, forecasts = [], []
        d = start
        while d <= end:
            a, f = winter_day(d, **self.kwargs)
            actuals += a
            forecasts += f
            d += timedelta(days=1)
        return LoadedData(
            actuals_raw=pd.DataFrame(actuals),
            forecasts_raw=pd.DataFrame(forecasts),
            status=DataStatus(chunks_total=2, chunks_fetched=2, offline=False,
                              oldest_retrieval=datetime(2026, 2, 1, tzinfo=timezone.utc),
                              newest_retrieval=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        )
