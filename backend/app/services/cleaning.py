"""Normalisation of raw Elexon records into clean, typed frames.

Pure functions: no I/O, no HTTP. They take the JSON records as a DataFrame
(columns as returned by Elexon) and return a tidy frame plus a report that
says exactly what was discarded and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .timeutils import parse_utc

_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

ACTUAL_COLUMNS = ["start_time", "actual_mw"]
FORECAST_COLUMNS = ["start_time", "publish_time", "forecast_mw"]


@dataclass
class CleaningReport:
    """Counts of what happened to the raw rows. Surfaced in API responses."""

    raw_rows: int = 0
    non_wind_rows: int = 0
    invalid_timestamp_rows: int = 0
    invalid_value_rows: int = 0
    duplicate_rows_removed: int = 0
    conflicting_duplicate_groups: int = 0
    kept_rows: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


def _require(raw: pd.DataFrame, columns: list[str], what: str) -> None:
    missing = [c for c in columns if c not in raw.columns]
    if missing:
        raise ValueError(f"{what} records are missing required column(s): {', '.join(missing)}")


def _valid_generation(values: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Return (numeric values, validity mask). Invalid = non-numeric, NaN, inf or negative."""
    numeric = pd.to_numeric(values, errors="coerce").astype("float64")
    ok = np.isfinite(numeric) & (numeric >= 0)
    return numeric, ok


def normalise_actuals(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """FUELHH records -> one row per `start_time` with `actual_mw`.

    * keeps only ``fuelType == "WIND"``
    * parses ``startTime`` to tz-aware UTC
    * drops unparseable timestamps and non-numeric / negative / non-finite generation
    * de-duplicates per `start_time`: the record with the latest ``publishTime`` wins
      (revisions supersede earlier values); a tie is broken by the higher generation,
      so the outcome never depends on row order.
    """
    report = CleaningReport(raw_rows=len(raw))
    if raw.empty:
        return pd.DataFrame({c: [] for c in ACTUAL_COLUMNS}).astype(
            {"start_time": "datetime64[ns, UTC]", "actual_mw": "float64"}
        ), report
    _require(raw, ["startTime", "generation", "fuelType"], "Actual generation")

    df = raw.copy()
    is_wind = df["fuelType"].astype(str).str.strip().str.upper() == "WIND"
    report.non_wind_rows = int((~is_wind).sum())
    df = df[is_wind]

    df["start_time"] = parse_utc(df["startTime"])
    df["publish_time"] = (
        parse_utc(df["publishTime"])
        if "publishTime" in df.columns
        else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    )
    df["actual_mw"], value_ok = _valid_generation(df["generation"])

    time_ok = df["start_time"].notna()
    report.invalid_timestamp_rows = int((~time_ok).sum())
    report.invalid_value_rows = int((time_ok & ~value_ok).sum())
    df = df[time_ok & value_ok]

    df = df.assign(_pub=df["publish_time"].fillna(_EPOCH))
    conflicts = df.groupby("start_time")["actual_mw"].nunique()
    report.conflicting_duplicate_groups = int((conflicts > 1).sum())
    before = len(df)
    df = (
        df.sort_values(["start_time", "_pub", "actual_mw"], kind="mergesort")
        .drop_duplicates("start_time", keep="last")
    )
    report.duplicate_rows_removed = before - len(df)
    report.kept_rows = len(df)
    return df[ACTUAL_COLUMNS].reset_index(drop=True), report


def normalise_forecasts(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """WINDFOR records -> one row per (`start_time`, `publish_time`) with `forecast_mw`.

    Records without a parseable ``publishTime`` are dropped: without it we cannot
    know whether the forecast was available at the decision cutoff.

    Exact duplicates collapse to one row. Records that share ``startTime`` *and*
    ``publishTime`` but disagree on ``generation`` are a data conflict; the rule is
    to keep the **highest** value (deterministic, independent of row order) and the
    conflict is counted in the report.
    """
    report = CleaningReport(raw_rows=len(raw))
    if raw.empty:
        return pd.DataFrame({c: [] for c in FORECAST_COLUMNS}).astype(
            {
                "start_time": "datetime64[ns, UTC]",
                "publish_time": "datetime64[ns, UTC]",
                "forecast_mw": "float64",
            }
        ), report
    _require(raw, ["startTime", "publishTime", "generation"], "Forecast generation")

    df = raw.copy()
    df["start_time"] = parse_utc(df["startTime"])
    df["publish_time"] = parse_utc(df["publishTime"])
    df["forecast_mw"], value_ok = _valid_generation(df["generation"])

    time_ok = df["start_time"].notna() & df["publish_time"].notna()
    report.invalid_timestamp_rows = int((~time_ok).sum())
    report.invalid_value_rows = int((time_ok & ~value_ok).sum())
    df = df[time_ok & value_ok]

    key = ["start_time", "publish_time"]
    conflicts = df.groupby(key)["forecast_mw"].nunique()
    report.conflicting_duplicate_groups = int((conflicts > 1).sum())
    before = len(df)
    df = df.sort_values(key + ["forecast_mw"], kind="mergesort").drop_duplicates(key, keep="last")
    report.duplicate_rows_removed = before - len(df)
    report.kept_rows = len(df)
    return df[FORECAST_COLUMNS].reset_index(drop=True), report
