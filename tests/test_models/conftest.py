
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



@pytest.fixture
def fitted_tuning_results(tiny_xy):
    """
    Three fitted TuningResults with predictably different behaviors.

    Model A: DummyClassifier(stratrgy="most_frequent") -> always predicts
              the majority class. AUC 0.5

    Model B: DummyClassifier(strategy-"stratified") -> random predictions
             respecting class balance. AUC 0.5

    Model C: LogisticRegression(solver="saga", max_iter=2000
             random_state=42, C=0.1) -> real classifier, should 
             beat both dummies comfortable.

    The fixture provides a known winner (Model C) and two closely-matched
    dummies that can be forces to tie on cost by tweaking cost_fn/cost_fp 
    
    """

    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression

    from src.models.trainer import build_pipeline
    from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES
    from src.models.tuner import TuningResult, SearchMetadata

    X, y = tiny_xy
    results: dict[str, TuningResult] = {}

    for name, model in [
        ("model_a", DummyClassifier(strategy="most_frequent")),
        ("model_b", DummyClassifier(strategy="stratified", random_state=42)),
        ("model_c", LogisticRegression(solver="saga", max_iter=2000, random_state=42, C=0.1)),
    ]:
        pipeline = build_pipeline(
            NUMERICAL_FEATURES, CATEGORICAL_FEATURES, model
        )
        pipeline.fit(X, y)


        # Minimal metadata that satifies the dataclass contract
        metadata = SearchMetadata(
            search_strategy="GridSearchCV",
            param_space={},
            scoring="roc_auc",
            cv_strategy="StratifiedKFold(n_splits=2)",
            n_candidates=1,
            n_fits=2,
            n_iter=None,
            random_state=42,
            started_at="2026-01-01T00:00:00+00:00",
            duration_seconds=0.1
        )

        results[name] = TuningResult(
            best_estimator=pipeline,
            best_params={},
            best_score=0.5,
            cv_results={},
            search_metadata=metadata
        )


    return results


@pytest.fixture
def sample_selection_result(tiny_xy):
    """
    A minimal SelectionResult backed by a fitted LogisticRegression on tiny_xy
    
    """
    from sklearn.linear_model import LogisticRegression
    from src.models.trainer import build_pipeline
    from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES
    from src.models.selector import SelectionResult, SelectionMetadata

    X, y = tiny_xy
    pipeline = build_pipeline(
        NUMERICAL_FEATURES, CATEGORICAL_FEATURES,
        LogisticRegression(solver="saga", max_iter=2000, random_state=42)

    )
    pipeline.fit(X, y)

    metadata = SelectionMetadata(
        run_started_at="2026-01-01T00:00:00+00:00",
        run_duration_seconds=1.0,
        n_candidates_considered=1,
        candidate_names=["test_model"],
        validation_set_size=len(y),
        threshold_search_grid="0.01..0.99 step 0.01",
    )

    return SelectionResult(
        best_estimator=pipeline,
        best_model_name="test_model",
        threshold=0.42,
        cost_ratio=(5.0, 1.0),
        validation_metrics={
            "precision": 0.6,
            "recall": 0.5,
            "roc_auc": 0.8,
            "log_loss": 0.4,
            "brier_score": 0.1,
            "expected_cost": 10.0,
        },
        comparison={},
        selection_metadata=metadata,
    )
