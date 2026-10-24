from datetime import date, time

import pandas as pd
import pytest

from app.services.policy import DecisionPolicy
from app.services.timeutils import delivery_dates, half_hour_index, parse_utc


def test_default_cutoff_is_0900_london_the_day_before_in_winter():
    cutoff = DecisionPolicy().cutoff_utc(date(2026, 1, 15))
    assert cutoff == pd.Timestamp("2026-01-14T09:00:00Z")


def test_cutoff_follows_british_summer_time():
    # 09:00 BST == 08:00 UTC
    assert DecisionPolicy().cutoff_utc(date(2026, 7, 2)) == pd.Timestamp("2026-07-01T08:00:00Z")


def test_cutoff_is_configurable():
    p = DecisionPolicy(cutoff_time=time(10, 30), days_ahead=2)
    assert p.cutoff_utc(date(2026, 1, 15)) == pd.Timestamp("2026-01-13T10:30:00Z")


def test_cutoff_across_spring_forward_day_uses_the_local_offset_of_the_decision_day():
    # Delivery Sun 2026-03-29 (clocks go forward 01:00->02:00); decision Sat 28 Mar is still GMT.
    assert DecisionPolicy().cutoff_utc(date(2026, 3, 29)) == pd.Timestamp("2026-03-28T09:00:00Z")
    # Delivery Mon 30 Mar: decision Sun 29 Mar 09:00 is already BST (08:00 UTC).
    assert DecisionPolicy().cutoff_utc(date(2026, 3, 30)) == pd.Timestamp("2026-03-29T08:00:00Z")


def test_invalid_policy_rejected():
    with pytest.raises(ValueError):
        DecisionPolicy(days_ahead=-1)


def test_parse_utc_handles_z_offsets_naive_and_garbage():
    s = pd.Series(["2026-01-14T04:30:00Z", "2026-07-01T09:00:00+01:00", "2026-01-14T00:00:00", "nonsense", None])
    out = parse_utc(s)
    assert out.iloc[0] == pd.Timestamp("2026-01-14T04:30:00Z")
    assert out.iloc[1] == pd.Timestamp("2026-07-01T08:00:00Z")  # offset converted to UTC
    assert out.iloc[2] == pd.Timestamp("2026-01-14T00:00:00Z")  # naive -> UTC
    assert out.iloc[3:].isna().all()
    assert str(out.dt.tz) == "UTC"


def test_delivery_date_is_uk_local_date():
    s = parse_utc(pd.Series(["2026-07-01T23:30:00Z", "2026-01-01T23:30:00Z"]))
    d = delivery_dates(s, "Europe/London")
    assert list(d) == [date(2026, 7, 2), date(2026, 1, 1)]  # 23:30Z is already 00:30 BST next day


@pytest.mark.parametrize(
    "day,periods",
    [(date(2026, 1, 15), 48), (date(2026, 3, 29), 46), (date(2026, 10, 25), 50)],
)
def test_half_hour_index_handles_dst_days(day, periods):
    idx = half_hour_index(day, day, "Europe/London")
    assert len(idx) == periods
    assert idx.is_unique and idx.is_monotonic_increasing


def test_half_hour_index_multiday_january():
    assert len(half_hour_index(date(2026, 1, 1), date(2026, 1, 31), "Europe/London")) == 31 * 48
