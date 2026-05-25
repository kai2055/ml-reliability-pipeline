"""
Integration test for the full training pipeline orchestration


"""

import pytest
import pandas as pd
from pathlib import Path
import numpy as np
import mlflow


from src.data.schema import (
    STRING_COLUMNS,
    INTEGER_COLUMNS,
    FLOAT_COLUMNS,
    DATE_COLUMNS,
)
from scripts.run_training import run_training
from src.models.registry import load_model
from src.models.baseline_saver import load_baseline


def _make_training_csv(path: Path, n_rows: int = 300) -> None:
    """
    Write a small schema-valid SBA-shaped CSV to path.

    Numerical and categorical features carry seeded random variation,
    and loanstatus is weakly correlated with grossapproval so the
    models produce a genuine (non-degenerate) fit. Raw loanstatus
    values use the uppercase-spaced form the transformer expects.
    
    """

    rng = np.random.default_rng(42)

    base = {col: ["X"] * n_rows for col in STRING_COLUMNS}
    base.update({col: [1] * n_rows for col in INTEGER_COLUMNS})
    base.update({col: [1.0] * n_rows for col in FLOAT_COLUMNS})
    base.update({col: ["1999-02-02"] * n_rows for col in DATE_COLUMNS})

    # Required by fatal checks
    base["program"] = ["7a"] * n_rows

    # Give two categorical features real categories so OneHotEncoder works
    base["businesstype"] = list(rng.choice(["corp", "llc", "sole"], size=n_rows))
    base["processingmethod"] = list(rng.choice(["plp", "clp", "gp"], size=n_rows))

    # Numerical feature with spread
    grossapproval = rng.integers(10_000, 500_000, size=n_rows)
    base["grossapproval"] = grossapproval

    # Weak real signal: larger loans default slightly more often
    default_prob = (grossapproval - grossapproval.min()) / np.ptp(grossapproval)
    is_chgoff = rng.random(n_rows) < (0.3 + 0.4 * default_prob)
    base["loanstatus"] = ["CHGOFF" if c else "P I F" for c in is_chgoff]

    df = pd.DataFrame(base)
    df.to_csv(path, index=False)


@pytest.mark.slow
def test_run_training_integration(tmp_path):
    """
    The full pipeline runs end-to-end on a small dataset and produces valid artifacts
    """
    # Isolate MLflow from production tracking
    mlflow.set_tracking_uri(f"file:///{tmp_path / 'mlruns'}")


    csv_path = tmp_path / "tiny_sba.csv"
    _make_training_csv(csv_path, n_rows=300)

    model_dir = tmp_path / "model"
    baseline_dir = tmp_path / "baseline"

    # Act - run the whole orchestration with a low row threshold
    run_training(
        data_path=csv_path,
        model_dir=model_dir,
        baseline_dir=baseline_dir,
        cost_fn=5.0,
        cost_fp=1.0,
        mlflow_experiment="test_integration",
        absolute_threshold=10,          # override the 50k production floor

    )

    assert (model_dir / "model.joblib").exists()
    model_artifact = load_model(model_dir)
    assert model_artifact.pipeline is not None

    assert (baseline_dir / "baseline.json").exists()
    baseline = load_baseline(baseline_dir)
    assert "numerical" in baseline
    assert "categorical" in baseline

