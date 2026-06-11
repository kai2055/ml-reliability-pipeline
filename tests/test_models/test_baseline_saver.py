from src.models.baseline_saver import compute_baseline, save_baseline, load_baseline
from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES

import pytest
import numpy as np


def test_compute_baseline_structure_and_metadata(tiny_xy):
    X, _ = tiny_xy
    baseline = compute_baseline(X)

    assert set(baseline.keys()) == {"metadata", "numerical", "categorical"}

    meta = baseline["metadata"]
    assert meta["n_training_rows"] == len(X)
    assert isinstance(meta["created_at"], str) and meta["created_at"]
    assert meta["numerical_features"] == list(NUMERICAL_FEATURES)
    assert meta["categorical_features"] == list(CATEGORICAL_FEATURES)


def test_compute_baseline_numerical_summary_shape_and_sanity(tiny_xy):
    X, _ = tiny_xy
    baseline = compute_baseline(X)

    for col in NUMERICAL_FEATURES:
        stats = baseline["numerical"][col]

        assert set(stats.keys()) == {
            "percentiles", "mean", "std", "min", "max", "missing_fraction"
        }

        assert stats["min"] <= stats["mean"] <= stats["max"]
        assert stats["std"] >= 0
        assert 0.0 <= stats["missing_fraction"] <= 1.0



def test_compute_baseline_percentile_count_and_monotonicity(tiny_xy):
    X, _ = tiny_xy
    baseline = compute_baseline(X)

    for col in NUMERICAL_FEATURES:
        pcts = baseline["numerical"][col]["percentiles"]
        assert len(pcts) == 99

        # Strictly increasing (or non-decreasing; quantiles can tie with few values)
        assert all(pcts[i] <= pcts[i + 1] for i in range(len(pcts) - 1))



def test_compute_baseline_categorical_frequencies(tiny_xy):
    X, y = tiny_xy
    baseline = compute_baseline(X)

    for col in CATEGORICAL_FEATURES:
        freqs = baseline["categorical"][col]
        assert sum(freqs.values()) == pytest.approx(1.0)
        assert all(isinstance(k, str) for k in freqs)


def test_save_baseline_roundtrip(tiny_xy, tmp_path):
    X, _ = tiny_xy
    original = compute_baseline(X)
    save_baseline(original, tmp_path)
    loaded = load_baseline(tmp_path)
    assert loaded == original


def test_save_baseline_overwrite_guard_default(tiny_xy, tmp_path):
    X, _ = tiny_xy
    baseline = compute_baseline(X)

    save_baseline(baseline, tmp_path)

    with pytest.raises(FileExistsError):
        save_baseline(baseline, tmp_path)



def test_save_baseline_overwrite_allowed(tiny_xy, tmp_path):
    X, _ = tiny_xy
    baseline1 = compute_baseline(X)
    save_baseline(baseline1, tmp_path)

    baseline2 = compute_baseline(X)
    baseline2["metadata"]["n_training_rows"] = 9999
    save_baseline(baseline2, tmp_path, overwrite=True)

    loaded = load_baseline(tmp_path)
    assert loaded["metadata"]["n_training_rows"] == 9999


def test_load_baseline_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_baseline(tmp_path)



def test_compute_baseline_missing_fraction(tiny_xy):
    X, _ = tiny_xy
    X_mod = X.copy()
    col = NUMERICAL_FEATURES[0]
    n_rows = len(X_mod)
    n_nan =5

    X_mod.iloc[:n_nan, X_mod.columns.get_loc(col)] = np.nan

    baseline = compute_baseline(X_mod)
    missing_fraction = baseline["numerical"][col]["missing_fraction"]
    assert missing_fraction == pytest.approx(n_nan / n_rows)


    