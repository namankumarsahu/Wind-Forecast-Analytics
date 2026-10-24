"""Thin, well-behaved client for the Elexon BMRS "stream" endpoints.

Verified behaviour of the official API (https://bmrs.elexon.co.uk/api-documentation):

* Base URL ``https://data.elexon.co.uk/bmrs/api/v1`` (``bmrs.elexon.co.uk/api/v1`` is an alias).
* ``GET /datasets/FUELHH/stream`` accepts ``settlementDateFrom`` / ``settlementDateTo``
  (YYYY-MM-DD, UK settlement date) and ``fuelType=WIND``. It returns a JSON **array**
  (no pagination envelope) of
  ``{dataset, publishTime, startTime, settlementDate, settlementPeriod, fuelType, generation}``.
* ``GET /datasets/WINDFOR/stream`` accepts ``publishDateTimeFrom`` / ``publishDateTimeTo``
  (ISO-8601 UTC) and returns a JSON array of ``{dataset, publishTime, startTime, generation}``.
  Each publication contains hourly targets, roughly 72 hours ahead.
* The stream endpoints are not paginated; we bound the size of every request by
  asking for one day at a time (see `data_provider.py`).

No API key is required. Transient failures (timeouts, connection errors, HTTP 429
and 5xx) are retried a bounded number of times with exponential back-off; other
4xx responses fail immediately.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, Callable

import httpx

from ..exceptions import ElexonTimeoutError, ElexonUpstreamError

log = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "wind-forecast-analytics/1.0"},
        )
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ API
    def fetch_wind_actuals(self, start: date, end: date) -> list[dict[str, Any]]:
        """FUELHH wind records for settlement dates start..end (inclusive)."""
        return self._get_json(
            "datasets/FUELHH/stream",
            {
                "settlementDateFrom": start.isoformat(),
                "settlementDateTo": end.isoformat(),
                "fuelType": "WIND",
            },
        )

    def fetch_wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> list[dict[str, Any]]:
        """WINDFOR records published between the two UTC instants."""
        return self._get_json(
            "datasets/WINDFOR/stream",
            {"publishDateTimeFrom": _iso_z(publish_from), "publishDateTimeTo": _iso_z(publish_to)},
        )

    # ------------------------------------------------------------- internals
    def _get_json(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(path, params=params)
            except httpx.TimeoutException as exc:
                last_error = ElexonTimeoutError(f"Timed out calling Elexon {path}: {exc}")
            except httpx.TransportError as exc:
                last_error = ElexonUpstreamError(f"Network error calling Elexon {path}: {exc}")
            else:
                if response.status_code == 200:
                    return self._parse(response, path)
                snippet = response.text[:200].replace("\n", " ")
                error = ElexonUpstreamError(
                    f"Elexon {path} returned HTTP {response.status_code}: {snippet}",
                    status_code=response.status_code,
                )
                if response.status_code not in _RETRYABLE_STATUS:
                    raise error  # e.g. 400 bad parameters: retrying cannot help
                last_error = error

            if attempt < self._max_retries:
                delay = self._backoff * (2**attempt)
                log.warning("Elexon call failed (%s); retry %d in %.1fs", last_error, attempt + 1, delay)
                self._sleep(delay)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _parse(response: httpx.Response, path: str) -> list[dict[str, Any]]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ElexonUpstreamError(f"Elexon {path} returned a non-JSON body") from exc
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            payload = payload["data"]  # tolerate the enveloped format used by non-stream endpoints
        if not isinstance(payload, list):
            raise ElexonUpstreamError(f"Elexon {path} returned an unexpected JSON structure")
        return payload
