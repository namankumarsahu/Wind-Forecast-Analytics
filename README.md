# Wind Forecast Analytics

A small analytics web app for a UK electricity utility's day-ahead purchasing team. It answers two questions about **national GB wind generation**:

1. *What was the latest wind forecast available at the moment the day-ahead purchase decision had to be made?*
2. *How accurate was that forecast compared with what the wind farms actually produced?*

Data comes only from the public **Elexon BMRS** API (no API key, no database, no other sources). Scope: purchase decisions for January 2026.

> **Status:** code complete and tested locally (backend tests, frontend build and Docker Compose all run on the author's machine); **not yet deployed**. Public URL: _add here once deployed_ (see [Deployment](#deployment)).

---

## Contents

- [Features](#features) · [Business problem](#business-problem-and-users) · [Architecture](#architecture-and-data-flow) · [Repository layout](#repository-layout)
- [Data sources and assumptions](#data-sources-and-assumptions) · [Cutoff methodology](#forecast-cutoff-methodology) · [Metrics](#metric-definitions-and-units)
- [Run locally](#run-locally) · [Docker](#docker) · [Tests](#tests) · [Environment variables](#environment-variables) · [API](#api) · [Deployment](#deployment)
- [Verification status](#verification-status) · [AI tools disclosure](#ai-tools-disclosure)

## Features

- **Overview** – KPI cards (MAE, RMSE, MBE, WAPE), forecast-vs-actual chart, generation summaries, over/under-forecast split, coverage, data-retrieval status, and the cutoff rule in plain words.
- **Forecast Explorer** – every 30-minute period of a chosen delivery day: selected forecast, actual, signed and absolute error, **forecast publication time**, lead time, cutoff used, status. Sortable; loading / empty / error states.
- **Accuracy Analysis** – aggregate metrics, daily MAE/RMSE/MBE/WAPE, error histogram, over/under analysis, ten largest errors, date-range filter limited to the analysis scope.
- All numbers are computed **in the backend**; the frontend only displays them.

## Business problem and users

The procurement team buys power on the GB day-ahead market the day before delivery, so it must rely on wind **forecasts**. Whatever wind the forecast promises does not need to be bought from thermal plants; if the forecast is wrong, the team is exposed. Evaluating accuracy fairly means using only the forecast that *existed* at decision time, not a better one published later.

## Architecture and data flow

```
 React + Vite (Vercel / nginx)  ──HTTP /api──►  FastAPI  ──►  AnalysisService
                                                                │
   Elexon BMRS  ◄── ElexonClient (retries) ◄── ElexonDataProvider (daily chunks, disk cache)
   FUELHH / WINDFOR                                             │
                                  cleaning ─► selection(policy) ─► matching ─► metrics ─► Pydantic response
```

1. `ElexonDataProvider` loads one **settlement day** of actuals and one **UTC publish day** of forecasts per request chunk, in parallel, through `ElexonClient` (timeouts, bounded exponential-backoff retries on 429/5xx/network errors, clear errors otherwise).
2. Chunks at least `CACHE_MIN_AGE_DAYS` old (January 2026 data is final) are cached as JSON on disk; recent ones only in memory. Concurrent callers share one upstream call.
3. `cleaning.py` keeps `fuelType == WIND`, parses timestamps to tz-aware UTC, drops invalid rows, and de-duplicates deterministically; a report of what was dropped is returned to the UI.
4. `selection.py` applies the cutoff policy and picks, per target period, the latest eligible forecast; `build_period_frame` joins it with actuals on `startTime` for every half-hour of the requested days (DST-aware).
5. `metrics.py` computes the metrics from valid matched pairs only. `analysis.py` assembles the three endpoints from the **same** prepared frame, so all pages are consistent.

Selection logic, cleaning and metrics are pure functions: no HTTP, files or framework imports.

## Repository layout

```
wind-forecast-analytics/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, CORS, error→HTTP mapping
│   │   ├── config.py            Settings from environment variables
│   │   ├── deps.py              Dependency wiring (overridable in tests)
│   │   ├── exceptions.py        Domain errors (timeout / upstream / offline)
│   │   ├── prefetch.py          `python -m app.prefetch` warms the cache
│   │   ├── routes/              health.py (/health, /config), analysis.py (/overview, /periods, /accuracy)
│   │   ├── schemas/             Pydantic response models
│   │   └── services/
│   │       ├── elexon_client.py   HTTP client + retries
│   │       ├── data_provider.py   chunking, caching, single-flight, offline mode
│   │       ├── cleaning.py        WIND filter, timestamp parsing, de-duplication
│   │       ├── policy.py          decision-cutoff policy (configurable, DST-safe)
│   │       ├── selection.py       forecast selection + actual/forecast matching
│   │       ├── metrics.py         MAE, RMSE, MBE, WAPE
│   │       ├── timeutils.py       UTC parsing, UK-local dates, half-hour grid
│   │       └── analysis.py        orchestration for the endpoints
│   ├── tests/                   pytest suite with deterministic synthetic fixtures
│   ├── Dockerfile · Procfile · requirements*.txt · pytest.ini · .env.example
├── frontend/
│   ├── src/{pages,components,hooks,services,types,lib}/
│   ├── Dockerfile · nginx.conf · vercel.json · .env.example
├── docs/                        customer-demo-script.md, technical-demo-script.md, submission-checklist.md
├── scripts/smoke_test.sh        quick curl check of a running backend
├── docker-compose.yml · render.yaml · .gitignore · README.md
```

## Data sources and assumptions

Official API (public, no key): `https://data.elexon.co.uk/bmrs/api/v1`. Docs: [FUELHH stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), [WINDFOR stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream).

Behaviour observed while building (via live requests to the API on 2026-10-24; the documentation site itself is a JavaScript app and could not be read as text):

| | Actuals – `FUELHH` | Forecasts – `WINDFOR` |
|---|---|---|
| Date filter | `settlementDateFrom`, `settlementDateTo` (+ `fuelType=WIND`) | `publishDateTimeFrom`, `publishDateTimeTo` |
| Response | JSON array, not paginated | JSON array, not paginated |
| Fields | `dataset, publishTime, startTime, settlementDate, settlementPeriod, fuelType, generation` | `dataset, publishTime, startTime, generation` |
| Resolution | **30 min** (48 records for a normal day) | **hourly** target times, ~72 h horizon per publication |

Because the stream endpoints are not paginated, requests are bounded by asking for one day at a time.

**Limitations and assumptions (please read):**

- **Forecasts are hourly, actuals half-hourly.** Only periods with both values are compared (~24 per day). Coverage is shown in the UI. Nothing is interpolated or forward-filled.
- **Units.** Values are treated and labelled as **MW** (power, averaged over the period). The magnitudes observed (~13,000–20,000 for GB wind in January) are consistent with MW; the unit could not be read from the JavaScript documentation site, so this rests on that plausibility check. Energy is shown as MW × 0.5 h.
- **Scope = delivery dates 1–31 January 2026** (`ANALYSIS_START/END`). The brief's wording ("decisions made in January") could also mean delivery dates 2 Jan–1 Feb; change the two variables to switch, nothing else is hard-coded.
- **Revisions of actuals.** If FUELHH holds several records for one period, the one with the latest `publishTime` wins (ties → higher value).
- No data is ever fabricated; synthetic records exist only in unit tests.

## Forecast cutoff methodology

The brief says purchases are made "one day before delivery" without a time. Assumption (configurable):

> **cutoff = (delivery date − 1 day) at 09:00 Europe/London.**

Rationale: the GB day-ahead auction closes mid-morning on the day before delivery (the N2EX day-ahead auction's gate closure is 09:50 GMT per [Nord Pool](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-day-ahead-gb-auction); other auction times were not verified). 09:00 leaves the trader time to read the forecast before bidding. Change with `DECISION_CUTOFF_TIME`, `DECISION_TIMEZONE`, `DECISION_DAYS_AHEAD`.

For every target `startTime`:

1. delivery date = UK-local calendar date of `startTime`;
2. cutoff = that date minus `DECISION_DAYS_AHEAD`, at the cutoff clock time, converted to UTC with the IANA tz database (so DST is handled; a non-existent/ambiguous wall time resolves with `fold=0`);
3. forecasts with `publishTime > cutoff` are excluded (`publishTime == cutoff` is included);
4. the forecast with the **latest** remaining `publishTime` is selected;
5. **Tie-breaking:** records with identical `startTime` *and* `publishTime` collapse to one; if their values differ the **highest** value is kept, which is independent of row order, and the conflict is counted in the quality report;
6. it is matched to the actual with the same `startTime`; errors are computed only for valid pairs.

The selected forecast's `publishTime`, its lead time and the cutoff are shown per row in the Forecast Explorer.

## Metric definitions and units

With `error = forecast − actual` (positive = over-forecast, negative = under-forecast), N valid matched periods:

| Metric | Formula | Unit |
|---|---|---|
| MAE | mean(\|error\|) | MW |
| RMSE | sqrt(mean(error²)) | MW |
| MBE | mean(error) | MW |
| WAPE | Σ\|error\| / Σ\|actual\| × 100 | % |

Pairs with missing/non-finite values are dropped and counted. With no valid pairs every metric is `null` (shown as "—", never 0); WAPE is `null` when Σ\|actual\| = 0. Every response carries the sample count `n`.

## Run locally

Requirements: Python 3.12+, Node 20+ (22 recommended), internet access to `data.elexon.co.uk`.

```bash
# backend  → http://localhost:8000  (interactive docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                                   # Windows: copy .env.example .env
python -m uvicorn app.main:app --reload

# frontend → http://localhost:5173 (Vite proxies /api to :8000)
cd frontend
npm install
npm run dev
```

The first request for a date range downloads data from Elexon (in parallel, one request per day of data; a full month can take a while on the first load) and caches it under `backend/data_cache/`. To warm the whole of January up front: `python -m app.prefetch` (or set `PREFETCH_ON_STARTUP=true`).

## Docker

```bash
docker compose up --build
# UI       http://localhost:18080  (nginx serves the SPA and proxies /api to the backend)
# API docs http://localhost:8000/docs
```

The UI is published on port **18080** (not 8080) to avoid clashes with other programs that commonly use 8080/8081. To use another port, change the left-hand number of `"18080:80"` in `docker-compose.yml`. If you see `port is already allocated`, something else is using that port: pick another or stop the other container (`docker ps`).

The backend has a health check (`/api/health`); the frontend waits for it. Downloaded data lives in the `elexon-cache` volume. The frontend image is built with an empty `VITE_API_BASE_URL`, so browser calls are same-origin (`/api`) and never point at `localhost` from a deployed page.

## Tests

```bash
cd backend && pytest                 # backend suite
cd frontend && npm run lint && npm run typecheck && npm run build
```

Backend tests (deterministic synthetic data only) cover: WIND filtering, timestamp parsing, cutoff selection (latest eligible, late forecasts excluded, identical-publishTime ties), DST cutoffs and 46/50-period days, forecast/actual matching, missing forecasts/actuals, duplicates, all four metrics incl. zero denominators and empty input, January scope validation, client retries/timeouts/HTTP errors, cache behaviour (disk, offline, corrupt file, concurrent single-flight), service output, and the HTTP API (validation, error mapping, CORS, OpenAPI).

## Environment variables

Backend (`backend/.env.example` lists all, with defaults): `CORS_ORIGINS` (comma-separated allowed frontend origins, **set this to your Vercel URL**), `ELEXON_BASE_URL`, `HTTP_TIMEOUT_SECONDS`, `HTTP_MAX_RETRIES`, `HTTP_BACKOFF_SECONDS`, `FETCH_CONCURRENCY`, `CACHE_DIR`, `CACHE_MIN_AGE_DAYS`, `ELEXON_OFFLINE`, `PREFETCH_ON_STARTUP`, `ANALYSIS_START`, `ANALYSIS_END`, `DECISION_TIMEZONE`, `DECISION_CUTOFF_TIME`, `DECISION_DAYS_AHEAD`, `WINDFOR_LOOKBACK_DAYS`.

Frontend: `VITE_API_BASE_URL` – backend base URL without trailing slash (empty for local dev and Docker Compose). No secrets are used anywhere; `.env` files are git-ignored.

## API

Interactive docs: `/docs` (Swagger) and `/redoc`.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness (does not call Elexon) |
| `GET /api/config` | analysis scope, unit, cutoff policy |
| `GET /api/overview?date=2026-01-15` (or `start=&end=`; none = whole scope) | KPIs, coverage, series, summaries, data status |
| `GET /api/periods?date=2026-01-15` | every half-hour with selected forecast, actual, errors, publish time, cutoff |
| `GET /api/accuracy?start=2026-01-01&end=2026-01-31` | aggregate + daily metrics, histogram, over/under, top errors |

Errors: `422` invalid or out-of-scope dates (message states the allowed range), `502` Elexon error, `504` Elexon timeout, `503` data missing in offline mode.

## Deployment

**Backend (Render, free tier – `render.yaml` provided)**
1. Push the repo to GitHub (anonymous repo name).
2. Render → New → Blueprint → select the repo. It reads `render.yaml` (root dir `backend`, health check `/api/health`).
3. After the first deploy copy the service URL (e.g. `https://wind-forecast-api.onrender.com`).
4. Set env var `CORS_ORIGINS` to the Vercel URL once you have it (no trailing slash), then redeploy.
   Any host that runs `uvicorn app.main:app --host 0.0.0.0 --port $PORT` works (`Procfile` included for Heroku-style platforms). Free tiers sleep when idle and use an ephemeral disk, so the first request after idle re-downloads data; open the app once before presenting.

**Frontend (Vercel)**
1. Vercel → Add New Project → import the repo → **Root Directory: `frontend`** (Vite is detected; `vercel.json` adds the SPA rewrite).
2. Environment variable `VITE_API_BASE_URL` = backend URL from above (no trailing slash).
3. Deploy, then put the Vercel URL into the backend's `CORS_ORIGINS` and into this README.

Not deployed yet; no public URL is claimed. Add the real URL to the status line at the top once it is live and verified.

## Verification status

Checked by running the commands in this README on a Windows machine (Python 3.14, Node 22, Docker Desktop):

- ✅ **Backend:** `python -m pytest` → 93 passed (includes the 24 HTTP API tests).
- ✅ **Frontend:** `npm run lint`, `npm run typecheck` and `npm run build` pass.
- ✅ **Live data:** the dashboard loads real January 2026 data from Elexon (744 matched periods for the full month, i.e. 50% of 1,488 half-hours, as expected with hourly forecasts).
- ✅ **Docker Compose:** `docker compose up --build` builds both images, the backend health check passes and the UI proxies `/api` to the backend.
- ⚠️ **Not done yet:** public deployment (Render / Vercel). No public URL is claimed anywhere in this repository.

Observation worth knowing before presenting: over the full month the selected forecasts over-estimate on average (large positive MBE). The app reports exactly what the data shows; the likely reasons (e.g. differences in what the two Elexon datasets cover) have not been investigated here.

## AI tools disclosure

This project was developed with the assistance of **Claude (Anthropic)** via Claude Code / claude.ai, which generated and reviewed code, tests and documentation. All output should be reviewed by the submitter, who remains responsible for it. _Add any other AI tools you used here._
