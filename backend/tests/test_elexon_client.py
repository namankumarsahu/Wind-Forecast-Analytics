import json
from datetime import date, datetime, timezone

import httpx
import pytest

from app.exceptions import ElexonTimeoutError, ElexonUpstreamError
from app.services.elexon_client import ElexonClient


def make_client(handler, max_retries=3):
    sleeps: list[float] = []
    client = ElexonClient(
        "https://example.test/bmrs/api/v1",
        max_retries=max_retries,
        backoff_seconds=1.0,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_actuals_request_uses_documented_parameters_and_returns_list():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = request.url
        return httpx.Response(200, json=[{"fuelType": "WIND", "startTime": "2026-01-14T00:00:00Z", "generation": 1}])

    client, _ = make_client(handler)
    rows = client.fetch_wind_actuals(date(2026, 1, 14), date(2026, 1, 14))
    assert rows[0]["generation"] == 1
    assert seen["url"].path == "/bmrs/api/v1/datasets/FUELHH/stream"
    q = dict(seen["url"].params)
    assert q == {"settlementDateFrom": "2026-01-14", "settlementDateTo": "2026-01-14", "fuelType": "WIND"}


def test_forecast_request_uses_publish_window_in_utc():
    seen = {}

    def handler(request):
        seen["url"] = request.url
        return httpx.Response(200, json=[])

    client, _ = make_client(handler)
    client.fetch_wind_forecasts(
        datetime(2026, 1, 14, tzinfo=timezone.utc), datetime(2026, 1, 14, 23, 59, 59, tzinfo=timezone.utc)
    )
    assert seen["url"].path.endswith("/datasets/WINDFOR/stream")
    q = dict(seen["url"].params)
    assert q == {"publishDateTimeFrom": "2026-01-14T00:00:00Z", "publishDateTimeTo": "2026-01-14T23:59:59Z"}


def test_transient_errors_are_retried_with_exponential_backoff_then_succeed():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, text="busy") if len(calls) < 3 else httpx.Response(200, json=[])

    client, sleeps = make_client(handler)
    assert client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1)) == []
    assert len(calls) == 3 and sleeps == [1.0, 2.0]


def test_retries_are_bounded_and_end_in_upstream_error():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500, text="boom")

    client, sleeps = make_client(handler, max_retries=2)
    with pytest.raises(ElexonUpstreamError, match="HTTP 500") as err:
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
    assert len(calls) == 3  # 1 attempt + 2 retries
    assert err.value.status_code == 500
    assert sleeps == [1.0, 2.0]


def test_timeouts_raise_timeout_error_after_retries():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client, _ = make_client(handler, max_retries=1)
    with pytest.raises(ElexonTimeoutError):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))


def test_connection_errors_raise_upstream_error():
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    client, _ = make_client(handler, max_retries=0)
    with pytest.raises(ElexonUpstreamError, match="Network error"):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))


def test_client_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, text="bad parameter")

    client, sleeps = make_client(handler)
    with pytest.raises(ElexonUpstreamError, match="HTTP 400"):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
    assert len(calls) == 1 and sleeps == []


def test_non_json_and_unexpected_structures_are_reported():
    client, _ = make_client(lambda r: httpx.Response(200, text="<html>nope</html>"))
    with pytest.raises(ElexonUpstreamError, match="non-JSON"):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))

    client, _ = make_client(lambda r: httpx.Response(200, content=json.dumps({"unexpected": 1})))
    with pytest.raises(ElexonUpstreamError, match="unexpected JSON"):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))


def test_enveloped_data_payload_is_accepted():
    client, _ = make_client(lambda r: httpx.Response(200, json={"data": [{"a": 1}]}))
    assert client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1)) == [{"a": 1}]
