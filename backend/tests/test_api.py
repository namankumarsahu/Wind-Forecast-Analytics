import pytest

from app.exceptions import DataUnavailableError, ElexonTimeoutError, ElexonUpstreamError


class Failing:
    def __init__(self, exc):
        self.exc = exc

    def load(self, start, end):
        raise self.exc


def test_health(make_client):
    r = make_client().get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "analysis_start": "2026-01-01", "analysis_end": "2026-01-31"}


def test_config_exposes_scope_and_cutoff_policy(make_client):
    body = make_client().get("/api/config").json()
    assert body["analysis_start"] == "2026-01-01" and body["unit"] == "MW"
    assert body["policy"]["cutoff_local_time"] == "09:00" and body["policy"]["days_ahead"] == 1


def test_overview_single_day_returns_backend_computed_metrics(make_client):
    r = make_client().get("/api/overview", params={"date": "2026-01-15"})
    assert r.status_code == 200
    body = r.json()
    assert body["metrics"]["n"] == 24
    assert body["metrics"]["mae_mw"] == pytest.approx(500.0)
    assert body["metrics"]["unit"] == "MW"
    assert len(body["series"]) == 48
    assert body["policy"]["example_decision_cutoff_utc"].startswith("2026-01-14T09:00:00")
    assert body["data_status"]["source"] == "elexon-live"


def test_overview_without_params_defaults_to_whole_scope(make_client):
    body = make_client().get("/api/overview").json()
    assert (body["start"], body["end"]) == ("2026-01-01", "2026-01-31")


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-01-01"},
        {"end": "2026-01-01"},
        {"date": "2026-01-02", "start": "2026-01-01", "end": "2026-01-03"},
        {"date": "15-01-2026"},
        {"date": "2026-02-01"},
        {"date": "2025-12-31"},
    ],
)
def test_overview_rejects_invalid_or_out_of_scope_parameters(make_client, params):
    assert make_client().get("/api/overview", params=params).status_code == 422


def test_periods_returns_every_half_hour_with_publication_time(make_client):
    body = make_client().get("/api/periods", params={"date": "2026-01-15"}).json()
    assert len(body["rows"]) == 48
    first = body["rows"][0]
    assert first["status"] == "matched"
    assert first["forecast_publish_time"].startswith("2026-01-14T08:00:00")
    assert first["decision_cutoff"].startswith("2026-01-14T09:00:00")
    assert first["error_mw"] == pytest.approx(500.0)
    assert body["rows"][1]["status"] == "missing_forecast"
    assert body["rows"][1]["forecast_mw"] is None


def test_periods_requires_date(make_client):
    assert make_client().get("/api/periods").status_code == 422


def test_accuracy_endpoint(make_client):
    body = make_client().get("/api/accuracy", params={"start": "2026-01-01", "end": "2026-01-31"}).json()
    assert body["metrics"]["n"] == 31 * 24
    assert len(body["daily"]) == 31
    assert len(body["top_errors"]) == 10
    assert sum(b["count"] for b in body["histogram"]) == body["metrics"]["n"]


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-01-10", "end": "2026-01-09"},
        {"start": "2025-12-01", "end": "2026-01-10"},
        {"start": "2026-01-10", "end": "2026-02-10"},
        {"start": "2026-01-10"},
        {"start": "garbage", "end": "2026-01-10"},
    ],
)
def test_accuracy_validates_range(make_client, params):
    r = make_client().get("/api/accuracy", params=params)
    assert r.status_code == 422


def test_scope_error_message_is_understandable(make_client):
    r = make_client().get("/api/accuracy", params={"start": "2026-02-01", "end": "2026-02-02"})
    assert "analysis scope" in r.json()["detail"]


@pytest.mark.parametrize(
    "exc,status",
    [
        (ElexonTimeoutError("t/o"), 504),
        (ElexonUpstreamError("HTTP 500", status_code=500), 502),
        (DataUnavailableError("not cached"), 503),
    ],
)
def test_upstream_failures_map_to_meaningful_http_errors(make_client, exc, status):
    r = make_client(Failing(exc)).get("/api/overview", params={"date": "2026-01-15"})
    assert r.status_code == status
    assert "detail" in r.json()


def test_cors_allows_configured_origin(make_client):
    r = make_client().get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = make_client().get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_openapi_docs_are_served(make_client):
    c = make_client()
    assert c.get("/docs").status_code == 200
    assert "/api/overview" in c.get("/openapi.json").json()["paths"]
