from src.models.tuner import TuningConfig
from src.models.trainer import build_pipeline
from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from scipy.stats import randint, uniform, loguniform    # for RandomizedSearch distributions


LOGREG_TUNING_CONFIG = TuningConfig(
    name="logistic_regression",
    pipeline=build_pipeline(
        NUMERICAL_FEATURES,
        CATEGORICAL_FEATURES,
        LogisticRegression(solver="liblinear", max_iter=1000, random_state=42),
        
    ),
    search_class=GridSearchCV,
    param_space={
        "model__C": [0.01, 0.1, 1.0, 10.0, 100.0],
        "model__penalty": ["l1", "l2"],
        "model__class_weight": [None, "balanced"],
    },
    scoring="roc_auc",
)



RF_TUNING_CONFIG = TuningConfig(
    name="random_forest",
    pipeline=build_pipeline(
        NUMERICAL_FEATURES,
        CATEGORICAL_FEATURES,
        RandomForestClassifier(random_state=42, n_jobs=-1),
    ),
    search_class=RandomizedSearchCV,
    param_space={
        "model__n_estimators": randint(100, 501),
        "model__max_depth": [5, 10, 15, 20, 30, None],
        "model__min_samples_split": randint(2, 21),
        "model__min_samples_leaf": randint(1, 11),
        "model__max_features": ["sqrt", "log2", 0.5],
        "model__class_weight": ["balanced", None],

    },
    scoring="roc_auc",
    n_iter=20,
)


XGB_TUNING_CONFIG = TuningConfig(
    name="xgboost",
    pipeline=build_pipeline(
        NUMERICAL_FEATURES,
        CATEGORICAL_FEATURES,
        XGBClassifier(
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            use_label_encoder=False,
        ),
    ),
    search_class=RandomizedSearchCV,
    param_space={
        "model__n_estimators": randint(100, 501),
        "model__max_depth": randint(3, 11),
        "model__learning_rate": loguniform(0.01, 0.3),
        "model__subsample": uniform(0.6, 0.4),
        "model__colsample_bytree": uniform(0.6, 0.4),
        "model__min_child_weight": randint(1, 11),
        "model__gamma": uniform(0, 5),
        "model__scale_pos_weight": randint(1, 11),

    },
    scoring="roc_auc",
    n_iter=20,
)




