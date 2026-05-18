
import pytest

from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

from src.models.tuner import TuningConfig, tune
from src.models.tuning_configs import (
    LOGREG_TUNING_CONFIG,
    RF_TUNING_CONFIG,
    XGB_TUNING_CONFIG,
)



def test_logreg_config_is_tuning_config():
    assert isinstance(LOGREG_TUNING_CONFIG, TuningConfig)


def test_logreg_config_strategy():
    assert LOGREG_TUNING_CONFIG.search_class == GridSearchCV
    assert LOGREG_TUNING_CONFIG.n_iter is None


def test_logreg_config_smoke_run(tiny_xy):
    X, y = tiny_xy
    result = tune(X, y, LOGREG_TUNING_CONFIG)

    assert isinstance(result.best_score, float)
    assert 0.0 <= result.best_score <= 1.0




def test_rf_config_is_tuning_config():
    assert isinstance(RF_TUNING_CONFIG, TuningConfig)


def test_rf_config_strategy():
    assert RF_TUNING_CONFIG.search_class == RandomizedSearchCV
    assert RF_TUNING_CONFIG.n_iter == 20


@pytest.mark.slow
def test_rf_config_smoke_run(tiny_xy):
    X, y = tiny_xy
    result = tune(X, y, RF_TUNING_CONFIG)

    assert isinstance(result.best_score, float)
    assert 0.0 <= result.best_score <= 1.0



def test_xgb_config_is_tuning_config():
    assert isinstance(XGB_TUNING_CONFIG, TuningConfig)


def test_xgb_config_strategy():
    assert XGB_TUNING_CONFIG.search_class == RandomizedSearchCV
    assert XGB_TUNING_CONFIG.n_iter == 20

@pytest.mark.slow
def test_xgb_config_smoke_run(tiny_xy):
    X, y = tiny_xy
    result = tune(X, y, XGB_TUNING_CONFIG)

    assert isinstance(result.best_score, float)
    assert 0.0 <= result.best_score <= 1.0

