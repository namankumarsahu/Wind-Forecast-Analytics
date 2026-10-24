"""Decision-cutoff policy: *which forecasts were knowable when the purchase was made*.

The brief says day-ahead purchases are made "one day before the delivery day"
but gives no clock time. We therefore model the cutoff explicitly and keep it
configurable:

    cutoff(delivery_date) = (delivery_date - days_ahead) at cutoff_time, in `timezone`

Defaults: 1 day ahead, 09:00 Europe/London. 09:00 is deliberately a little
earlier than the GB day-ahead auction gate closure (N2EX day-ahead auction:
09:50 GMT, per Nord Pool's published auction description; other GB auctions may
close earlier and were not verified), so that a trader has the forecast *in
hand* before bids are submitted. Set DECISION_CUTOFF_TIME to test other times.

Daylight saving: the local wall-clock time is converted to UTC with the IANA
tz database (zoneinfo), so "09:00 London" is 09:00 UTC in winter and 08:00 UTC
in summer. A wall-clock time that does not exist (spring-forward gap) or exists
twice (autumn overlap) is resolved deterministically with fold=0, i.e. the
first occurrence / the offset in force before the transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd


@dataclass(frozen=True)
class DecisionPolicy:
    timezone: str = "Europe/London"
    cutoff_time: time = time(9, 0)
    days_ahead: int = 1

    def __post_init__(self) -> None:
        if self.days_ahead < 0:
            raise ValueError("days_ahead must be >= 0")
        ZoneInfo(self.timezone)  # raises ZoneInfoNotFoundError if invalid

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def decision_date(self, delivery_date: date) -> date:
        return delivery_date - timedelta(days=self.days_ahead)

    def cutoff_local(self, delivery_date: date) -> datetime:
        naive = datetime.combine(self.decision_date(delivery_date), self.cutoff_time)
        return naive.replace(tzinfo=self.tz, fold=0)

    def cutoff_utc(self, delivery_date: date) -> pd.Timestamp:
        return _cutoff_utc_cached(self, delivery_date)

    def describe(self) -> str:
        when = "the day before" if self.days_ahead == 1 else f"{self.days_ahead} days before"
        return (
            f"Purchase decisions are assumed to be taken {when} delivery at "
            f"{self.cutoff_time.strftime('%H:%M')} ({self.timezone}). Only forecasts with "
            f"publishTime <= that cutoff are eligible; the latest eligible one is used."
        )


@lru_cache(maxsize=4096)
def _cutoff_utc_cached(policy: DecisionPolicy, delivery_date: date) -> pd.Timestamp:
    local = policy.cutoff_local(delivery_date)
    return pd.Timestamp(local.astimezone(timezone.utc))
