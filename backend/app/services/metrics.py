"""Forecast-accuracy metrics (units: MW for MAE/RMSE/MBE, percent for WAPE).

    error = forecast - actual            (+ over-forecast, - under-forecast)
    MAE   = mean(|error|)
    RMSE  = sqrt(mean(error^2))
    MBE   = mean(error)
    WAPE  = sum(|error|) / sum(|actual|) * 100

Rules:
* Pairs where either side is NaN/inf are dropped and counted (`n_dropped`).
* If no valid pair remains, every metric is ``None`` - never a misleading 0.
* WAPE is ``None`` when sum(|actual|) == 0 (undefined).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AccuracyMetrics:
    n: int
    n_dropped: int
    mae: float | None
    rmse: float | None
    mbe: float | None
    wape_pct: float | None


def _clean_pairs(forecast, actual) -> tuple[np.ndarray, np.ndarray, int]:
    f = np.asarray(forecast, dtype="float64").ravel()
    a = np.asarray(actual, dtype="float64").ravel()
    if f.shape != a.shape:
        raise ValueError(f"forecast and actual must have equal length ({f.size} != {a.size})")
    ok = np.isfinite(f) & np.isfinite(a)
    return f[ok], a[ok], int((~ok).sum())


def mae(forecast, actual) -> float | None:
    f, a, _ = _clean_pairs(forecast, actual)
    return float(np.mean(np.abs(f - a))) if f.size else None


def rmse(forecast, actual) -> float | None:
    f, a, _ = _clean_pairs(forecast, actual)
    return float(np.sqrt(np.mean((f - a) ** 2))) if f.size else None


def mbe(forecast, actual) -> float | None:
    f, a, _ = _clean_pairs(forecast, actual)
    return float(np.mean(f - a)) if f.size else None


def wape_pct(forecast, actual) -> float | None:
    f, a, _ = _clean_pairs(forecast, actual)
    if not f.size:
        return None
    denominator = float(np.sum(np.abs(a)))
    if denominator == 0.0:
        return None
    return float(np.sum(np.abs(f - a)) / denominator * 100.0)


def compute_metrics(forecast, actual) -> AccuracyMetrics:
    """All four metrics from one consistent set of valid pairs."""
    f, a, dropped = _clean_pairs(forecast, actual)
    if not f.size:
        return AccuracyMetrics(0, dropped, None, None, None, None)
    err = f - a
    denominator = float(np.sum(np.abs(a)))
    return AccuracyMetrics(
        n=int(f.size),
        n_dropped=dropped,
        mae=float(np.mean(np.abs(err))),
        rmse=float(np.sqrt(np.mean(err**2))),
        mbe=float(np.mean(err)),
        wape_pct=None if denominator == 0.0 else float(np.sum(np.abs(err)) / denominator * 100.0),
    )
