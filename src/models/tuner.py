import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


import pandas as pd
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
)
from sklearn.pipeline import Pipeline


CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

@dataclass(frozen=True)
class SearchMetadata:
    search_strategy: str
    param_space: dict[str, Any]
    scoring: str
    cv_strategy: str
    n_candidates: int
    n_fits: int
    n_iter: int | None
    random_state: int
    started_at: str
    duration_seconds: float


@dataclass(frozen=True)
class TuningConfig:
    name: str
    pipeline: Pipeline
    search_class: type
    param_space: dict[str, Any]
    scoring: str
    n_iter: int | None = None
    random_state: int = 42


@dataclass(frozen=True)
class TuningResult:
    best_estimator: Pipeline
    best_params: dict[str, Any]
    best_score: float
    cv_results: dict[str, Any]
    search_metadata: SearchMetadata


def tune(
        X: pd.DataFrame,
        y: pd.Series,
        config: TuningConfig,
) -> TuningResult:
    """Run hyperparameter search according to config and return results."""

    start_wall = time.time()
    started_at = datetime.now(timezone.utc).isoformat()

    if config.search_class == GridSearchCV:
        search = config.search_class(
            estimator=config.pipeline,
            param_grid=config.param_space,
            scoring=config.scoring,
            cv=CV,
            n_jobs=-1,
        )
    else:
        search = config.search_class(
            estimator=config.pipeline,
            param_distributions=config.param_space,
            scoring=config.scoring,
            cv=CV,
            n_iter=config.n_iter,
            random_state=config.random_state,
            n_jobs=-1,
        )

    search.fit(X, y)

    end_wall = time.time()


    metadata = SearchMetadata(
        search_strategy=config.search_class.__name__,
        param_space=config.param_space,
        scoring=config.scoring,
        cv_strategy=f"StratifiedKFold(n_splits={CV.n_splits}, shuffle={CV.shuffle}, random_state={CV.random_state})",
        n_candidates=len(search.cv_results_["params"]),
        n_fits=search.n_splits_ * len(search.cv_results_["params"]),
        n_iter=config.n_iter,
        random_state=config.random_state,
        started_at=started_at,
        duration_seconds=round(end_wall - start_wall, 2),
    )


    return TuningResult(
        best_estimator=search.best_estimator_,
        best_params=search.best_params_,
        best_score=search.best_score_,
        cv_results=search.cv_results_,
        search_metadata=metadata,
    )
