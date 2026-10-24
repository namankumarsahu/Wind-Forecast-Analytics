"""Timestamp helpers. All internal timestamps are timezone-aware UTC.

Elexon returns ISO-8601 strings such as ``2026-01-14T04:30:00Z`` (UTC).
"Delivery date" is the UK local calendar date of a target period, which is
also how Elexon defines ``settlementDate``.
"""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

HALF_HOUR = pd.Timedelta(minutes=30)


def parse_utc(series: pd.Series) -> pd.Series:
    """Parse ISO-8601 strings to tz-aware UTC timestamps. Unparseable values become NaT.

    Strings without an offset are interpreted as UTC (the Elexon convention).
    """
    return pd.to_datetime(series, utc=True, errors="coerce", format="ISO8601").dt.as_unit("ns")


def delivery_dates(start_utc: pd.Series, tz: str) -> pd.Series:
    """UK-local calendar date of each target period start."""
    return start_utc.dt.tz_convert(ZoneInfo(tz)).dt.date


def half_hour_index(start: date, end: date, tz: str) -> pd.DatetimeIndex:
    """Every 30-minute period start (UTC) whose local date lies in [start, end].

    Built in local time so DST days have 46 / 50 periods rather than 48.
    """
    zone = ZoneInfo(tz)
    first = pd.Timestamp(start, tz=zone)
    after_last = pd.Timestamp(end + timedelta(days=1), tz=zone)
    local = pd.date_range(first, after_last, freq=HALF_HOUR, inclusive="left")
    return local.tz_convert("UTC").as_unit("ns")
