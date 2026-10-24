"""Runtime configuration, read from environment variables (see backend/.env.example)."""

from __future__ import annotations

from datetime import date, time
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .services.policy import DecisionPolicy


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Elexon BMRS -------------------------------------------------------
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3  # retries after the first attempt (bounded)
    http_backoff_seconds: float = 1.0  # exponential: 1s, 2s, 4s ...
    fetch_concurrency: int = 6

    # --- Cache / data loading ---------------------------------------------
    cache_dir: Path = Path("./data_cache")
    cache_min_age_days: int = 2  # only persist chunks at least this old (data is final)
    elexon_offline: bool = False  # true = never call Elexon, serve only what is cached
    prefetch_on_startup: bool = False  # warm the cache for the whole analysis scope

    # --- Analysis scope (delivery dates) ----------------------------------
    analysis_start: date = date(2026, 1, 1)
    analysis_end: date = date(2026, 1, 31)

    # --- Decision cutoff ---------------------------------------------------
    decision_timezone: str = "Europe/London"
    decision_cutoff_time: str = "09:00"  # HH:MM local time on the decision day
    decision_days_ahead: int = 1
    windfor_lookback_days: int = 3  # how far before the cutoff to load forecast publications

    # --- Web ---------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    def decision_policy(self) -> DecisionPolicy:
        hh, mm = self.decision_cutoff_time.split(":")
        return DecisionPolicy(
            timezone=self.decision_timezone,
            cutoff_time=time(int(hh), int(mm)),
            days_ahead=self.decision_days_ahead,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
