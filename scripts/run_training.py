
"""
Training pipeline orchestration.

Runs the full model-training pipeline end to end: load the raw SBA data,
transform and validate it, build the modelling dataset, split it, 
tune three model families, select the best, evaluate on the test set,
and persist the model artifact and the baseline snapshot

Run from the project root: python scripts/run_training.py


"""

# The project is not as a package, so the project root is 
# added to sys.path to make 'src' importable when this script is 
# run from any working directory
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from datetime import datetime, timezone

import mlflow
import pandas as pd

from src.data.loader import load_dataset
from src.data.transformer import transform
from src.data.validator import (
    check_columns,
    check_usable_rows,
    check_program_values,
    check_required_columns,
)


from src.models.dataset_builder import build_dataset
from src.models.data_splitter import split_train_val_test
from src.models.tuning_configs import (
    LOGREG_TUNING_CONFIG,
    RF_TUNING_CONFIG,
    XGB_TUNING_CONFIG,
)
from src.models.tuner import tune
from src.models.selector import select_best_model
from src.models.evaluator import predict, evaluate
from src.models.registry import save_model
from src.models.baseline_saver import compute_baseline, save_baseline





# Configuration - block to change a training run

DATA_PATH = Path("data/raw/sba_7a_2010_2019.csv")


# Cost ratio for threshold selection (ADR 021)
# v1 PLACEHOLDER - not derived from Datatroniq financials (fictional company, no P&L).
# Direction (FN > FP) is principled; magnitude is the  conservative
# end of the ~5-10x range cited for small-business lending
# Re-estimation from real cost data is tracked as Q14

COST_FN = 5.0       # cost of a false negative (approving a defaulter)
COST_FP = 1.0       # cost of a false positive (rejecting a good applicant)

MODEL_DIR = Path("artifacts/model")
BASELINE_DIR = Path("data/baseline")


MLFLOW_EXPERIMENT = "ml-reliability-pipeline"


def _run_fatal_checks(df: pd.DataFrame) -> None:
    """
    Run the fatal data-quality checks. Raise if any fails

    Fatal checks gate the pipeline: if the data does not clear them,
    training must not proceed
    
    
    """
    checks_with_status = {
        "columns": check_columns(df),
        "usable_rows": check_usable_rows(df),
        "program_values": check_program_values(df),
    }
    for name, result in checks_with_status.items():
        if result["status"]  == "fail":
            raise ValueError(
                f"Fatal data check '{name}' failed: {result.get('details',{})}"

            )
        

    required_violations = check_required_columns(df)
    if required_violations:
        raise ValueError(
            f"Fatal data check 'required_columns' failed: {required_violations}"
        )
    


def run_training(
        data_path: Path,
        model_dir: Path,
        baseline_dir: Path,
        cost_fn: float,
        cost_fp: float,
        mlflow_experiment: str,
) -> None:
    """
    Execute the full training pipeline end to end.

    Parameters are explicit testing seam. Production invocation is fixed:
    the __main__ block always calls this with the module-level config constants.
    
    """
    run_start = time.time()
    mlflow.set_experiment(mlflow_experiment)
    run_name = f"training_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}"

    with mlflow.start_run(run_name=run_name):
        #  Load and prepare data ────────────────────────────────
        print("Loading data...")
        raw_df = load_dataset(data_path)
        transformed_df = transform(raw_df)
        _run_fatal_checks(transformed_df)

        #  Build modelling dataset ──────────────────────────────
        X, y = build_dataset(transformed_df)

        # Train / validation / test split ──────────────────────
        X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
            X, y, val_size=0.15, test_size=0.15, random_state=42
        )

        #  Log input parameters early ───────────────────────────
        # Logged before tuning so a run that crashes mid-training
        # still records what it was attempting.
        mlflow.log_params({
            "data_path": str(data_path),
            "n_rows_raw": len(raw_df),
            "n_rows_transformed": len(transformed_df),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_test": len(X_test),
            "cost_fn": cost_fn,
            "cost_fp": cost_fp,
        })

        # Tune all three model families ────────────────────────
        configs = {
            "logistic_regression": LOGREG_TUNING_CONFIG,
            "random_forest": RF_TUNING_CONFIG,
            "xgboost": XGB_TUNING_CONFIG,
        }
        tuning_results = {}
        for name, cfg in configs.items():
            print(f"Tuning {name}...")
            tuning_results[name] = tune(X_train, y_train, cfg)

        #  Select best model by validation expected cost ────────
        print("Selecting best model...")
        selection = select_best_model(
            tuning_results, X_val, y_val, cost_fn=cost_fn, cost_fp=cost_fp
        )

        #  Evaluate winner on test set ──────────────────────────
        print("Evaluating on test set...")
        test_predictions = predict(
            selection.best_estimator, X_test, threshold=selection.threshold
        )
        test_metrics = evaluate(y_test, test_predictions)

        # Save artifacts to disk ───────────────────────────────
        print("Saving model and baseline...")
        save_model(selection, model_dir, overwrite=True)
        baseline = compute_baseline(X_train)
        save_baseline(baseline, baseline_dir, overwrite=True)

        #  Log results to MLflow ────────────────────────────────
        # Winning model identity and its tuned hyperparameters.
        winning_params = tuning_results[selection.best_model_name].best_params
        mlflow.log_params({
            "selected_model": selection.best_model_name,
            "threshold": selection.threshold,
            "best_hyperparams": str(winning_params),
        })

        # Tuning scores, one per model family.
        for name, res in tuning_results.items():
            mlflow.log_metric(f"tune_{name}_best_score", res.best_score)

        # Validation metrics for the selected model.
        for metric, value in selection.validation_metrics.items():
            mlflow.log_metric(f"val_{metric}", value)

        
        for metric, value in test_metrics.items():
            mlflow.log_metric(f"test_{metric}", value)

        run_duration = time.time() - run_start
        mlflow.log_metric("run_duration_seconds", round(run_duration, 2))
        print(f"Training complete in {run_duration:.1f}s")





if __name__ == "__main__":
    run_training(
        data_path=DATA_PATH,
        model_dir=MODEL_DIR,
        baseline_dir=BASELINE_DIR,
        cost_fn=COST_FN,
        cost_fp=COST_FP,
        mlflow_experiment=MLFLOW_EXPERIMENT,
    )