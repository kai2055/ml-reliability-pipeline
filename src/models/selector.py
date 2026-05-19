
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.models.tuner import TuningResult
from src.models.evaluator import predict, evaluate


THRESHOLD_GRID = np.linspace(0.01, 0.99, 99)


@dataclass(frozen=True)
class SelectionMetadata:
    run_started_at: str
    run_duration_seconds: float
    n_candidates_considered: int
    candidate_names: list[str]
    validation_set_size: int
    threshold_search_grid: str


@dataclass(frozen=True)
class SelectionResult:
    best_estimator: Pipeline
    best_model_name: str
    threshold: float
    cost_ratio: tuple[float, float]
    validation_metrics: dict[str, float]
    comparison: dict[str, dict]
    selection_metadata: SelectionMetadata



def _find_cost_optimal_threshold(
        pipeline: Pipeline,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        cost_fn: float,
        cost_fp: float,
) -> tuple[float, float]:
    """
    Return (best_threshold, lowest_expected_cost) for a fitted pipeline.
    
    """
    proba = pipeline.predict_proba(X_val)[:, 1]
    y_pred = (proba[:, None] >= THRESHOLD_GRID[None, :]).astype(int)

    fn = ((y_val.to_numpy()[:, None] == 1) & (y_pred == 0)).sum(axis=0)
    fp = ((y_val.to_numpy()[:, None] == 0) & (y_pred == 1)).sum(axis=0)

    costs = fn * cost_fn + fp * cost_fp
    best_idx = np.argmin(costs)
    return float(THRESHOLD_GRID[best_idx]), float(costs[best_idx])


def select_best_model(
        tuning_results: dict[str, TuningResult],
        X_val: pd.DataFrame,
        y_val: pd.Series,
        cost_fn: float,
        cost_fp: float,
) -> SelectionResult:
    """
    Select the best model by lowest expected cost on validation data.

    Each model is evaluated across a grid of thresholds. The winner is 
    the model whose cost-optimal threshold yields the smallest expected cost;
    ties are broken by AUC.
    """

    start_wall = time.time()
    started_at = datetime.now(timezone.utc).isoformat()

    comparison: dict[str, dict] = {}

    # evaluate every candidate
    for name, tuning_result in tuning_results.items():
        pipeline = tuning_result.best_estimator

        best_thresh, min_cost = _find_cost_optimal_threshold(
            pipeline, X_val, y_val, cost_fn, cost_fp
        )

        preds = predict(pipeline, X_val, threshold=best_thresh)
        metrics = evaluate(y_val, preds)

        comparison[name] = {
            "best_threshold": best_thresh,
            "expected_cost": min_cost,
            **metrics,
        }
    
    # pick winner (lowest expected costm break ties by AUC)
    def _sort_key(name: str) -> tuple[float, float]:
        return (
            comparison[name]["expected_cost"],
            -comparison[name]["roc_auc"],       # higher AUC -> lower sort value
        )
    
    winner_name = min(comparison, key=_sort_key)
    winner_data = comparison[winner_name]
    winner_pipeline = tuning_results[winner_name].best_estimator

    # build metadata
    metadata = SelectionMetadata(
        run_started_at=started_at,
        run_duration_seconds=round(time.time() - start_wall, 2),
        n_candidates_considered=len(tuning_results),
        candidate_names=list(tuning_results.keys()),
        validation_set_size=len(X_val),
        threshold_search_grid=(
            f"{THRESHOLD_GRID[0]:.2f}..{THRESHOLD_GRID[-1]:.2f} "
            f"step {(THRESHOLD_GRID[1] - THRESHOLD_GRID[0]):.2f}"
        ),

    )

    # assemble result

    return SelectionResult(
        best_estimator=winner_pipeline,
        best_model_name=winner_name,
        threshold=winner_data["best_threshold"],
        cost_ratio=(cost_fn, cost_fp),
        validation_metrics={
            k: winner_data[k]
            for k in ("precision", "recall", "roc_auc", "log_loss", "brier_score", "expected_cost")
            
        },
        comparison=comparison,
        selection_metadata=metadata,
    )

