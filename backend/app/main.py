"""FastAPI application entry point.  Run: ``uvicorn app.main:app --reload``."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .deps import get_service
from .exceptions import DataUnavailableError, ElexonError, ElexonTimeoutError
from .routes import analysis, health
from .services.analysis import ScopeError

log = logging.getLogger("app")


def _warm_cache() -> None:
    settings = get_settings()
    try:
        get_service().overview(settings.analysis_start, settings.analysis_end)
        log.info("Cache warm-up finished")
    except Exception:  # never let warm-up take the app down
        log.exception("Cache warm-up failed; data will be loaded on demand")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().prefetch_on_startup:
        threading.Thread(target=_warm_cache, name="cache-warmup", daemon=True).start()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Wind Forecast Analytics API",
        version="1.0.0",
        description=(
            "UK national wind generation: forecast available at the day-ahead purchase decision "
            "vs actual generation (Elexon BMRS WINDFOR / FUELHH). All generation values are in MW."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(analysis.router)

    @app.exception_handler(ScopeError)
    async def _scope(_: Request, exc: ScopeError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ElexonTimeoutError)
    async def _timeout(_: Request, exc: ElexonTimeoutError):
        return JSONResponse(status_code=504, content={"detail": f"Elexon did not respond in time. {exc}"})

    @app.exception_handler(ElexonError)
    async def _upstream(_: Request, exc: ElexonError):
        return JSONResponse(status_code=502, content={"detail": f"Elexon API error. {exc}"})

    @app.exception_handler(DataUnavailableError)
    async def _unavailable(_: Request, exc: DataUnavailableError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    return app


app = create_app()
