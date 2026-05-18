from src.models.tuner import tune, TuningResult
from sklearn.utils.validation import check_is_fitted



def test_tune_grid_config_uses_exhaustive_search(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)

    assert isinstance(result, TuningResult)
    # 2 C values -> 2 candidates
    assert result.search_metadata.n_candidates == 2


def test_tune_random_config_uses_n_iter_samples(tiny_xy, tiny_random_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_random_config)

    assert isinstance(result, TuningResult)
    # n_iter=3 -> 3 candidates
    assert result.search_metadata.n_candidates == 3



def test_search_strategy_matches_config_class(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)

    assert result.search_metadata.search_strategy == "GridSearchCV"



def test_n_fits_equals_n_splits_times_n_candidates(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)
    assert result.search_metadata.n_fits == 5 * result.search_metadata.n_candidates


def test_tuning_result_all_fields_populated(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)

    assert isinstance(result, TuningResult)
    assert result.best_estimator is not None
    assert result.best_params is not None
    assert result.best_score is not None
    assert result.cv_results is not None
    assert result.search_metadata is not None


def test_best_estimator_is_fitted(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)

    check_is_fitted(result.best_estimator)


def test_best_score_is_valid_auc(tiny_xy, tiny_grid_config):
    X, y = tiny_xy
    result = tune(X, y, tiny_grid_config)

    assert isinstance(result.best_score, float)
    assert 0.0 <= result.best_score <= 1.0



def test_tune_reproducibility(tiny_xy, tiny_random_config):
    X, y = tiny_xy
    result1 = tune(X, y, tiny_random_config)
    result2 = tune(X, y, tiny_random_config)

    assert result1.best_score == result2.best_score
    assert result1.best_params == result2.best_params
    



