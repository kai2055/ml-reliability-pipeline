
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from scipy.stats import loguniform


from src.models.tuner import TuningConfig
from src.models.trainer import build_pipeline
from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES



@pytest.fixture
def tiny_xy():
    """
    Small synthetic (X, y) for fast tuner tests.

    50 rows, both classes present, 2-3 values per categorical
    column so one hot encoding behaves consistently across CV folds.
    
    """

    rng = np.random.default_rng(42)
    n = 50

    X = pd.DataFrame({
        # numerical
        "grossapproval":         rng.uniform(10_000, 500_000, n),
        "sbaguaranteedapproval": rng.uniform(5_000, 400_000, n),
        "initialinterestrate":   rng.uniform(4.0, 9.0, n),
        "terminmonths":          rng.integers(12, 300, n),
        "jobssupported":         rng.integers(0, 50, n),
        # categorical — small alphabet, repeated
        "subprogram":                 rng.choice(["7a", "504"], n),
        "processingmethod":           rng.choice(["PLP", "CLP", "GP"], n),
        "fixedorvariableinterestind": rng.choice(["f", "v"], n),
        "revolverstatus":             rng.choice(["0", "1"], n),
        "businesstype":               rng.choice(["individual", "partnership", "corporation"], n),
        "businessage":                rng.choice(["new", "existing"], n),
        "collateralind":              rng.choice(["true", "false"], n),
    })

    # ~40% positive class, both classes present, fixed seed -> reproducible
    y = pd.Series(rng.choice([0, 1], size=n, p=[0.6, 0.4]), dtype="int8")

    return X, y



def _tiny_pipeline():
    """Shared tiny pipeline for both Grid and Random COnfigs"""
    return build_pipeline(
        NUMERICAL_FEATURES,
        CATEGORICAL_FEATURES,
        LogisticRegression(solver="liblinear", max_iter=200, random_state=42)

    )


@pytest.fixture
def tiny_grid_config():
    """Minimal GridSearchCV config - 2 combinations, runs in milliseconds"""
    return TuningConfig(
        name="test_logreg_grid",
        pipeline=_tiny_pipeline(),
        search_class=GridSearchCV,
        param_space={
            "model__C": [0.1, 1.0],
        },
        scoring="roc_auc"
    )




@pytest.fixture
def tiny_random_config():
    """Minimal RandomizedSearchCV config - n_iter=3 runs in milliseconds"""
    return TuningConfig(
        name="test_logreg_random",
        pipeline=_tiny_pipeline(),
        search_class=RandomizedSearchCV,
        param_space={
            "model__C": loguniform(0.1, 10.0),
        },
        scoring="roc_auc",
        n_iter=3,
    )
