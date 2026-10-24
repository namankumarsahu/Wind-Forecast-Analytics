# Technical walkthrough script (≤ 5 minutes)

**Audience:** tech lead. **Goal:** make review easy; transfer knowledge. Have the repo open in an editor, the app and `/docs` in browser tabs.

## 0:00 – Architecture (50 s)
Show the diagram in the README. React + Vite + Tailwind + Recharts + React Query frontend; FastAPI backend; pandas/numpy for processing; Pydantic response models. No database: Elexon is the source, a JSON file cache holds historical chunks. Layers are separate: `elexon_client` (HTTP) → `data_provider` (chunking/cache) → `cleaning` → `selection` + `policy` → `metrics` → `analysis` (orchestration) → `routes`/`schemas`.

## 0:50 – Data retrieval (60 s)
Open `elexon_client.py` docstring: endpoints, parameters (`settlementDateFrom/To` + `fuelType=WIND`; `publishDateTimeFrom/To`), unpaginated JSON arrays. **Finding to call out:** WINDFOR is hourly, FUELHH half-hourly, so only hourly periods match; coverage is reported, nothing interpolated.
Show retries (429/5xx/timeouts, bounded exponential backoff) and `data_provider.py`: one-day chunks fetched in parallel, disk cache for chunks older than 2 days, single-flight locks, offline mode, `python -m app.prefetch`.

## 1:50 – Forecast selection (90 s) – the core rule
Open `policy.py` and `selection.py`.
- Cutoff = (delivery date − 1 day) at 09:00 Europe/London, **configurable** via env; computed with `zoneinfo`, so DST is correct (show test with a summer date and 46/50-period days).
- Steps: delivery date → cutoff → drop `publish_time > cutoff` → latest remaining `publish_time` → join to actual on `start_time`.
- Duplicates: identical (`startTime`, `publishTime`) collapse; conflicting values → highest, deterministic, counted in the quality report.
- Pure functions, no I/O: easy to test. Publication time is exposed through the API and shown in the Explorer.

## 3:20 – Metrics and API (50 s)
`metrics.py`: MAE, RMSE, MBE, WAPE from one set of valid pairs; empty input or zero denominator → `None`, never 0. Backend returns the numbers; the frontend only formats. Show `/docs`: `/api/overview`, `/periods`, `/accuracy`, `/config`; validation returns 422 with the allowed range; Elexon failures map to 502/504; CORS from `CORS_ORIGINS`.

## 4:10 – Tests, Docker, deploy (50 s)
`pytest`: deterministic synthetic data only; show the list (selection, ties, DST, missing/duplicate records, metrics edge cases, client retries, cache, API). Say plainly what was and wasn't run before recording (see README "Verification status") and show the run you did.
`docker compose up --build` → UI :18080 (nginx proxies `/api`), API :8000, health checks. Deployment: backend on Render via `render.yaml`, frontend on Vercel with `VITE_API_BASE_URL`; set `CORS_ORIGINS` to the Vercel URL.
Close with known limitations: hourly forecast resolution, assumed 09:00 cutoff, free-tier cold starts.
