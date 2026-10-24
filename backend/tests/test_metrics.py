import math

import numpy as np
import pytest

from app.services.metrics import compute_metrics, mae, mbe, rmse, wape_pct

F = [110.0, 90.0, 150.0, 80.0]
A = [100.0, 100.0, 100.0, 100.0]
# errors: +10, -10, +50, -20


def test_mae():
    assert mae(F, A) == pytest.approx(22.5)


def test_rmse():
    assert rmse(F, A) == pytest.approx(math.sqrt((100 + 100 + 2500 + 400) / 4))


def test_mbe_sign_positive_means_overestimate():
    assert mbe(F, A) == pytest.approx(7.5)
    assert mbe([120], [100]) > 0
    assert mbe([80], [100]) < 0


def test_wape_percent():
    assert wape_pct(F, A) == pytest.approx(90 / 400 * 100)


def test_compute_metrics_consistent_with_individual_functions():
    m = compute_metrics(F, A)
    assert (m.n, m.n_dropped) == (4, 0)
    assert m.mae == pytest.approx(mae(F, A))
    assert m.rmse == pytest.approx(rmse(F, A))
    assert m.mbe == pytest.approx(mbe(F, A))
    assert m.wape_pct == pytest.approx(wape_pct(F, A))


def test_rmse_is_never_smaller_than_mae():
    rng = np.random.default_rng(0)
    f, a = rng.uniform(0, 1000, 200), rng.uniform(0, 1000, 200)
    assert rmse(f, a) >= mae(f, a)


def test_perfect_forecast_is_exactly_zero_not_none():
    m = compute_metrics([5.0, 6.0], [5.0, 6.0])
    assert (m.mae, m.rmse, m.mbe, m.wape_pct) == (0.0, 0.0, 0.0, 0.0)


def test_empty_dataset_gives_none_not_zero():
    m = compute_metrics([], [])
    assert m.n == 0
    assert m.mae is None and m.rmse is None and m.mbe is None and m.wape_pct is None
    assert mae([], []) is None and rmse([], []) is None and mbe([], []) is None and wape_pct([], []) is None


def test_zero_actual_denominator_makes_wape_undefined_only():
    m = compute_metrics([5.0, 7.0], [0.0, 0.0])
    assert m.wape_pct is None
    assert m.mae == pytest.approx(6.0)
    assert wape_pct([5.0], [0.0]) is None


def test_nan_and_inf_pairs_are_dropped_and_counted():
    m = compute_metrics([1.0, np.nan, 3.0, np.inf], [1.0, 2.0, np.nan, 4.0])
    assert m.n == 1
    assert m.n_dropped == 3
    assert m.mae == 0.0


def test_all_invalid_is_treated_as_empty():
    m = compute_metrics([np.nan], [1.0])
    assert m.n == 0 and m.mae is None


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_metrics([1.0, 2.0], [1.0])
