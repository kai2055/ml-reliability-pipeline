import json
import pytest
import numpy as np
import pandas as pd
import pathlib as Path


from scripts.run_monitoring import run_monitoring
from src.monitoring.report_generator import DriftReport


def _make_production_csv(path: Path, n_rows: int = 300) -> None:
    """Write a small schema-valid SBA-shaped CSV for the monitoring test."""
    from tests.test_scripts.test_run_training import _make_training_csv
    _make_training_csv(path, n_rows=n_rows)


@pytest.mark.slow
def test_run_monitoring_integration(tmp_path):
    """Full monitoring pipeline runs end-to-end and returns a DriftReport"""
    # Arrange - prodcution CSV
    csv_path = tmp_path / "tiny_production.csv"
    _make_production_csv(csv_path, n_rows=300)

    # Arrange - baseline built from a small processed dataset
    from src.data.loader import load_dataset
    from src.data.transformer import transform
    from src.models.dataset_builder import build_features
    from src.models.baseline_saver import compute_baseline, save_baseline

    raw_df = load_dataset(csv_path)
    transformed_df = transform(raw_df)
    X = build_features(transformed_df)
    baseline = compute_baseline(X)
    baseline_dir = tmp_path / "baseline"
    save_baseline(baseline, baseline_dir)

    # Isolate MLflow
    import mlflow
    mlflow.set_tracking_uri((tmp_path / "Mlruns").as_uri())

    report = run_monitoring(
        production_data_path=csv_path,
        baseline_dir=baseline_dir,
        mlflow_experiment="test_monitoring_integration",
        absolute_threshold=10,
    )


    assert isinstance(report, DriftReport)
    assert report.summary.total_features == 12
    assert report.summary.significant + report.summary.moderate + report.summary.low == 12
    