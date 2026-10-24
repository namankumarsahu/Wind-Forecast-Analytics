import threading
import time
from datetime import date, datetime, timedelta, timezone

import pytest

from app.exceptions import DataUnavailableError
from app.services.data_provider import ElexonDataProvider
from app.services.policy import DecisionPolicy

from .factories import actual, forecast

NOW = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)  # every January chunk is "final"


class FakeClient:
    def __init__(self, delay: float = 0.0):
        self.actual_calls: list[tuple[date, date]] = []
        self.forecast_calls: list[tuple[datetime, datetime]] = []
        self.delay = delay

    def fetch_wind_actuals(self, start, end):
        time.sleep(self.delay)
        self.actual_calls.append((start, end))
        return [actual(f"{start.isoformat()}T00:00:00Z", 1000)]

    def fetch_wind_forecasts(self, publish_from, publish_to):
        time.sleep(self.delay)
        self.forecast_calls.append((publish_from, publish_to))
        d = publish_from.date().isoformat()
        return [forecast(f"{d}T12:00:00Z", f"{d}T08:00:00Z", 900)]


def make(client, tmp_path, now=NOW, **kw):
    return ElexonDataProvider(client, tmp_path, DecisionPolicy(), now_fn=lambda: now, **kw)


def test_required_chunks_cover_the_cutoff_window_for_a_single_day(tmp_path):
    chunks = make(FakeClient(), tmp_path).required_chunks(date(2026, 1, 15), date(2026, 1, 15))
    assert ("actuals", date(2026, 1, 15)) in chunks
    forecast_days = [d for k, d in chunks if k == "forecasts"]
    # cutoff = 14 Jan 09:00Z, lookback 3 days -> publish days 11..14 (never the delivery day or later)
    assert forecast_days == [date(2026, 1, d) for d in (11, 12, 13, 14)]


def test_january_scope_needs_only_late_december_to_end_of_january_publications(tmp_path):
    chunks = make(FakeClient(), tmp_path).required_chunks(date(2026, 1, 1), date(2026, 1, 31))
    fdays = [d for k, d in chunks if k == "forecasts"]
    assert fdays[0] == date(2025, 12, 28) and fdays[-1] == date(2026, 1, 30)
    assert [d for k, d in chunks if k == "actuals"] == [date(2026, 1, d) for d in range(1, 32)]


def test_chunk_requests_are_one_day_each_with_utc_bounds(tmp_path):
    client = FakeClient()
    make(client, tmp_path).load(date(2026, 1, 15), date(2026, 1, 15))
    assert len(client.actual_calls) == 1 and client.actual_calls[0] == (date(2026, 1, 15), date(2026, 1, 15))
    starts = sorted(f for f, _ in client.forecast_calls)
    assert starts[0] == datetime(2026, 1, 11, tzinfo=timezone.utc)
    assert all(t - f == timedelta(hours=23, minutes=59, seconds=59) for f, t in client.forecast_calls)


def test_second_load_is_served_from_disk_cache_without_calling_elexon(tmp_path):
    first = FakeClient()
    make(first, tmp_path).load(date(2026, 1, 15), date(2026, 1, 15))
    assert first.actual_calls

    second = FakeClient()
    data = make(second, tmp_path).load(date(2026, 1, 15), date(2026, 1, 15))  # new instance, empty memory
    assert second.actual_calls == [] and second.forecast_calls == []
    assert data.status.chunks_fetched == 0
    assert data.status.chunks_from_cache == data.status.chunks_total
    assert len(data.actuals_raw) == 1 and len(data.forecasts_raw) == 4
    assert (tmp_path / "actuals" / "2026-01-15.json").exists()


def test_recent_chunks_are_not_persisted_to_disk(tmp_path):
    now = datetime(2026, 1, 16, 12, tzinfo=timezone.utc)  # 15 Jan is younger than cache_min_age_days
    make(FakeClient(), tmp_path, now=now).load(date(2026, 1, 15), date(2026, 1, 15))
    assert not (tmp_path / "actuals" / "2026-01-15.json").exists()
    assert (tmp_path / "forecasts" / "2026-01-11.json").exists()  # old enough


def test_offline_mode_serves_cache_and_refuses_to_fetch(tmp_path):
    with pytest.raises(DataUnavailableError, match="not cached"):
        make(FakeClient(), tmp_path, offline=True).load(date(2026, 1, 15), date(2026, 1, 15))

    make(FakeClient(), tmp_path).load(date(2026, 1, 15), date(2026, 1, 15))  # warm the cache
    client = FakeClient()
    data = make(client, tmp_path, offline=True).load(date(2026, 1, 15), date(2026, 1, 15))
    assert client.actual_calls == [] and data.status.offline


def test_corrupt_cache_file_is_ignored_and_refetched(tmp_path):
    (tmp_path / "actuals").mkdir()
    (tmp_path / "actuals" / "2026-01-15.json").write_text("{not json")
    client = FakeClient()
    make(client, tmp_path).load(date(2026, 1, 15), date(2026, 1, 15))
    assert len(client.actual_calls) == 1


def test_concurrent_requests_for_same_chunk_share_one_upstream_call(tmp_path):
    client = FakeClient(delay=0.2)
    provider = make(client, tmp_path)
    threads = [threading.Thread(target=provider._get_chunk, args=("actuals", date(2026, 1, 15))) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(client.actual_calls) == 1
