"""Dependency wiring (kept out of main.py so tests can override it)."""

from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .services.analysis import AnalysisService
from .services.data_provider import ElexonDataProvider
from .services.elexon_client import ElexonClient


def build_provider(settings: Settings) -> ElexonDataProvider:
    client = ElexonClient(
        base_url=settings.elexon_base_url,
        timeout=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
        backoff_seconds=settings.http_backoff_seconds,
    )
    return ElexonDataProvider(
        client=client,
        cache_dir=settings.cache_dir,
        policy=settings.decision_policy(),
        lookback_days=settings.windfor_lookback_days,
        offline=settings.elexon_offline,
        concurrency=settings.fetch_concurrency,
        cache_min_age_days=settings.cache_min_age_days,
    )


@lru_cache
def get_service() -> AnalysisService:
    settings = get_settings()
    return AnalysisService(
        provider=build_provider(settings),
        policy=settings.decision_policy(),
        scope_start=settings.analysis_start,
        scope_end=settings.analysis_end,
    )
