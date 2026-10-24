"""Loading raw Elexon data with chunking, caching and single-flight fetching.

Strategy (documented in the README):

* Actuals are requested one *settlement date* at a time, forecasts one *UTC publish
  day* at a time. Small, regular chunks keep each request bounded and make the cache
  granular and reusable between date selections.
* A chunk is persisted to ``CACHE_DIR/{actuals|forecasts}/YYYY-MM-DD.json`` once it is
  at least ``cache_min_age_days`` old (historical data is final). Younger chunks are only
  held in memory for a few minutes.
* Concurrent requests for the same chunk share one upstream call.
* In offline mode the provider never calls Elexon and raises `DataUnavailableError` for
  chunks that are not already cached (use ``python -m app.prefetch`` to fill the cache).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

import pandas as pd

from ..exceptions import DataUnavailableError
from .policy import DecisionPolicy

if TYPE_CHECKING:  # avoid importing httpx just to type-annotate
    from .elexon_client import ElexonClient

log = logging.getLogger(__name__)

_RECENT_TTL = timedelta(minutes=5)


@dataclass
class DataStatus:
    chunks_total: int = 0
    chunks_from_cache: int = 0
    chunks_fetched: int = 0
    oldest_retrieval: datetime | None = None
    newest_retrieval: datetime | None = None
    offline: bool = False


@dataclass
class LoadedData:
    actuals_raw: pd.DataFrame
    forecasts_raw: pd.DataFrame
    status: DataStatus


class DataProvider(Protocol):
    def load(self, start: date, end: date) -> LoadedData: ...


@dataclass
class _Chunk:
    records: list[dict[str, Any]]
    fetched_at: datetime
    from_cache: bool


class ElexonDataProvider:
    def __init__(
        self,
        client: ElexonClient,
        cache_dir: Path,
        policy: DecisionPolicy,
        lookback_days: int = 3,
        offline: bool = False,
        concurrency: int = 6,
        cache_min_age_days: int = 2,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._client = client
        self._cache_dir = Path(cache_dir)
        self._policy = policy
        self._lookback = lookback_days
        self._offline = offline
        self._concurrency = max(1, concurrency)
        self._min_age = cache_min_age_days
        self._now = now_fn
        self._memory: dict[tuple[str, date], _Chunk] = {}
        self._locks: dict[tuple[str, date], threading.Lock] = {}
        self._guard = threading.Lock()

    # ------------------------------------------------------------------ public
    def required_chunks(self, start: date, end: date) -> list[tuple[str, date]]:
        """Chunks needed to evaluate delivery dates start..end under the cutoff policy."""
        chunks: list[tuple[str, date]] = []
        d = start
        while d <= end:
            chunks.append(("actuals", d))
            d += timedelta(days=1)

        pub_from = self._policy.cutoff_utc(start).to_pydatetime() - timedelta(days=self._lookback)
        pub_to = self._policy.cutoff_utc(end).to_pydatetime()
        d = pub_from.date()
        while d <= pub_to.date():
            chunks.append(("forecasts", d))
            d += timedelta(days=1)
        return chunks

    def load(self, start: date, end: date) -> LoadedData:
        chunks = self.required_chunks(start, end)
        with ThreadPoolExecutor(max_workers=self._concurrency) as pool:
            results = list(pool.map(lambda key: (key, self._get_chunk(*key)), chunks))

        status = DataStatus(chunks_total=len(results), offline=self._offline)
        records = {"actuals": [], "forecasts": []}
        for (kind, _), chunk in results:
            records[kind].extend(chunk.records)
            status.chunks_from_cache += int(chunk.from_cache)
            status.chunks_fetched += int(not chunk.from_cache)
            if status.oldest_retrieval is None or chunk.fetched_at < status.oldest_retrieval:
                status.oldest_retrieval = chunk.fetched_at
            if status.newest_retrieval is None or chunk.fetched_at > status.newest_retrieval:
                status.newest_retrieval = chunk.fetched_at
        return LoadedData(
            actuals_raw=pd.DataFrame.from_records(records["actuals"]),
            forecasts_raw=pd.DataFrame.from_records(records["forecasts"]),
            status=status,
        )

    # ----------------------------------------------------------------- chunks
    def _get_chunk(self, kind: str, day: date) -> _Chunk:
        key = (kind, day)
        chunk = self._lookup(key)
        if chunk is not None:
            return chunk
        with self._lock_for(key):  # single-flight per chunk
            chunk = self._lookup(key)
            if chunk is not None:
                return chunk
            if self._offline:
                raise DataUnavailableError(
                    f"{kind} for {day} are not cached and ELEXON_OFFLINE is enabled. "
                    "Run `python -m app.prefetch` on a machine with internet access."
                )
            records = self._fetch(kind, day)
            chunk = _Chunk(records, self._now(), from_cache=False)
            self._remember(key, chunk)
            return chunk

    def _lookup(self, key: tuple[str, date]) -> _Chunk | None:
        cached = self._memory.get(key)
        if cached is not None:
            if self._is_final(key[1]) or self._now() - cached.fetched_at < _RECENT_TTL:
                return _Chunk(cached.records, cached.fetched_at, from_cache=True)
            del self._memory[key]
        path = self._path(key)
        if path.exists():
            try:
                payload = json.loads(path.read_text())
                chunk = _Chunk(
                    payload["records"], datetime.fromisoformat(payload["fetched_at"]), from_cache=True
                )
                self._memory[key] = chunk
                return chunk
            except (OSError, ValueError, KeyError):
                log.warning("Ignoring unreadable cache file %s", path)
        return None

    def _remember(self, key: tuple[str, date], chunk: _Chunk) -> None:
        self._memory[key] = chunk
        if not self._is_final(key[1]):
            return
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"fetched_at": chunk.fetched_at.isoformat(), "records": chunk.records}))
        os.replace(tmp, path)  # atomic: readers never see a half-written file

    def _fetch(self, kind: str, day: date) -> list[dict[str, Any]]:
        log.info("Fetching %s for %s from Elexon", kind, day)
        if kind == "actuals":
            return self._client.fetch_wind_actuals(day, day)
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        return self._client.fetch_wind_forecasts(start, start + timedelta(hours=23, minutes=59, seconds=59))

    def _is_final(self, day: date) -> bool:
        """Old enough that Elexon's data for this day will no longer change."""
        return day <= (self._now().date() - timedelta(days=self._min_age))

    def _path(self, key: tuple[str, date]) -> Path:
        return self._cache_dir / key[0] / f"{key[1].isoformat()}.json"

    def _lock_for(self, key: tuple[str, date]) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())
