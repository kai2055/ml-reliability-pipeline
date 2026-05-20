import numpy as np
from sklearn.metrics import confusion_matrix


from src.models.selector import select_best_model, SelectionResult, THRESHOLD_GRID


def test_returns_selection_result_with_all_fields_populated(
        fitted_tuning_results, tiny_xy
):
    
    X_val, y_val = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    assert isinstance(result, SelectionResult)
    assert result.best_estimator is not None
    assert isinstance(result.best_model_name, str) and result.best_model_name != ""
    assert isinstance(result.threshold, float)
    assert (
        isinstance(result.cost_ratio, tuple)
        and len(result.cost_ratio) == 2
    )
    assert isinstance(result.validation_metrics, dict) and result.validation_metrics
    assert isinstance(result.comparison, dict) and result.comparison
    assert result.selection_metadata is not None



def test_comparison_contains_all_candidate_keys(
        fitted_tuning_results, tiny_xy
):
    X_val, y_val = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    assert set(result.comparison.keys()) == set(fitted_tuning_results.keys())


def test_validation_metrics_has_expected_keys(
        fitted_tuning_results, tiny_xy
):
    X_val, y_val = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    expected_keys = {
        "precision",
        "recall",
        "roc_auc",
        "log_loss",
        "brier_score",
        "expected_cost",
    }

    assert set(result.validation_metrics.keys()) == expected_keys



def test_winner_has_lowest_expected_cost(
    fitted_tuning_results, tiny_xy
):
    """The selected model must have the minimum expected cost across all candidates.

    Tie‑break (higher AUC wins when costs are equal) is guaranteed by
    Python's built‑in tuple comparison in _sort_key and is not tested
    separately — engineering a tie in the fixture would be fragile.
    """
    X_val, y_val = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    winner_cost = result.validation_metrics["expected_cost"]
    all_costs = [stats["expected_cost"] for stats in result.comparison.values()]

    assert winner_cost == min(all_costs)


def test_best_estimator_matches_best_model_name(
        fitted_tuning_results, tiny_xy
):
    X_val, y_val = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    expected_pipeline = fitted_tuning_results[result.best_model_name].best_estimator
    assert result.best_estimator is expected_pipeline





def test_winner_threshold_minimizes_cost(
        fitted_tuning_results, tiny_xy
):
    X_val, y_val = tiny_xy
    cost_fn, cost_fp = 5, 1

    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=cost_fn, cost_fp=cost_fp
    )

    # Independent recomputation using sklearn's confusion matrix
    proba = result.best_estimator.predict_proba(X_val)[:, 1]
    costs = []
    for t in THRESHOLD_GRID:
        pred = (proba >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()
        costs.append(fn * cost_fn + fp * cost_fp)

    best_idx = int(np.argmin(costs))
    expected_threshold = float(THRESHOLD_GRID[best_idx])

    assert result.threshold == expected_threshold



def test_expected_cost_formula_is_correct(
        fitted_tuning_results, tiny_xy
):
    """
    Expected cost for every candidate must equal FN*cost_fn + FP*cost_fp
    """
    X_val, y_val = tiny_xy
    cost_fn, cost_fp = 5, 1

    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=cost_fn, cost_fp=cost_fp
    )

    for name, stats in result.comparison.items():
        pipeline = fitted_tuning_results[name].best_estimator
        proba = pipeline.predict_proba(X_val)[:, 1]
        pred = (proba >= stats["best_threshold"]).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()
        recomputed_cost = fn * cost_fn + fp * cost_fp

        assert stats["expected_cost"] == recomputed_cost, (
            f"Cost mismatch for {name}"
        )


def test_selection_metadata_reflects_reality(
        fitted_tuning_results, tiny_xy
):
    X_val, y_val, = tiny_xy
    result = select_best_model(
        fitted_tuning_results, X_val, y_val, cost_fn=5, cost_fp=1
    )

    meta = result.selection_metadata

    assert meta.n_candidates_considered == len(fitted_tuning_results)
    assert meta.candidate_names == list(fitted_tuning_results.keys())
    assert meta.validation_set_size == len(X_val)
    assert meta.run_duration_seconds > 0






