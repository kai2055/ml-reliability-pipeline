
"""
Monitoring pipeline orchestration.

Runs the full monitoring pipeline end to end: load and process the
production data, load the training baseline, compute drif metrics,
generate a human-readable report, and log the results to MLflow.

Run from the project root: python scripts/run_monitoring.py

"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mlflow

from src.data.loader import load_dataset
from src.data.transformer import transform
from src.data.validator import run_fatal_checks
from src.models.dataset_builder import build_features
from src.monitoring.baseline_loader import load_baseline
from src.monitoring.drift_detector import detect_drift
from src.monitoring.report_generator import generate_report, DriftReport


# Configuration - edit this block to change a monitoring run

PRODUCTION_DATA_PATH = Path("data/raw/sba_7a_2020_present.csv")
BASELINE_DIR = Path("data/baseline")
MLFLOW_EXPERIMENT = "ml-reliability-pipeline"
USABLE_ROWS_THRESHOLD = 50_000  # data-policy floor (ADR 005)



def run_monitoring(
        production_data_path: Path,
        baseline_dir: Path,
        mlflow_experiment: str,
        absolute_threshold: int,
) -> DriftReport:
    """
    Execute the full monitoring pipeline end to end

    Parameters accept overrides for testing; production uses the
    constants defined in the config block at the top of this file.
    """
    run_start = time.time()
    mlflow.set_experiment(mlflow_experiment)
    run_name = f"monitoring_{datetime.now(timezone.utc).strftime('%y-%m-%d_%H-%M-%S')}"

    with mlflow.start_run(run_name=run_name):
        # Load and process production data
        print("Loading production data....")
        raw_df = load_dataset(production_data_path)
        transformed_df = transform(raw_df)
        transformed_df = transformed_df.dropna(subset=["initialinterestrate"])
        run_fatal_checks(transformed_df, absolute_threshold, include_usable_rows=False)

        production_feeatures = build_features(transformed_df)

        # Load baseline
        print("loading baseline...")
        baseline = load_baseline(baseline_dir)

        # Detect drift
        print("Datecting drift...")
        drift_results = detect_drift(baseline, production_feeatures)

        # Generate report
        print("Generating report...")
        report = generate_report(drift_results)

        # Log to MLflow
        mlflow.log_params({
            "production_data_path": str(production_data_path),
            "baseline_dir": str(baseline_dir),
            "n_production_rows": len(production_feeatures),
            "n_features_total": report.summary.total_features,
        })

        mlflow.log_metrics({
            "features_significant": report.summary.significant,
            "features_moderate": report.summary.moderate,
            "features_low": report.summary.low,
        })

        for detail in report.details:
            mlflow.log_metric(f"psi_{detail.feature_name}", detail.psi)
            if detail.wasserstein is not None:
                mlflow.log_metric(f"wasserstein_{detail.feature_name}", detail.wasserstein)

        run_duration = time.time() - run_start
        mlflow.log_metric("dun_duration_seconds", round(run_duration, 2))
        print(f"Monitoring complete in {run_duration:.1f}s")
        print(f"    Significant:  {report.summary.significant}")
        print(f"    Moderate:     {report.summary.moderate}")
        print(f"    Low:          {report.summary.low}")

        return report
    



if __name__ == "__main__":
    run_monitoring(
        production_data_path=PRODUCTION_DATA_PATH,
        baseline_dir=BASELINE_DIR,
        mlflow_experiment=MLFLOW_EXPERIMENT,
        absolute_threshold=USABLE_ROWS_THRESHOLD,
    )
