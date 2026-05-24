from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import pandas as pd
from pathlib import Path
import mlflow
import joblib



EXPERIMENT_NAME = "datatroniq-credit-risk"




def build_pipeline(numerical_cols, categorical_cols, model) -> Pipeline:
    """
    Build a sklearn Pipeline with type-specific preprocessing

    Numerical columns are scaled with StandardScaler.
    Categorical columns are one-hot encoded with OneHotEncoder. 

    Args:
        numerical_cols (list of str): Column names to scale
        categorical_cols (list of str): Column names to one-hot encode
        model: (LogisticRegression, RandomForestClassifier, XGBClassifier)

    Returns: 
        Pipeline: Assembled pipeline with steps:
            ("preprocessing", ColumnTransformer) and ("model", model) 
    """


    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist"), categorical_cols)
        ],
        remainder="drop"
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessing", preprocessor),
            ("model", model)
        ]
    )
    
    return pipeline



def train(pipeline: Pipeline, X: pd.DataFrame, y:pd.Series) ->Pipeline:
    """
    Fit a pipeline on training data

    Args: 
        pipeline (Pipeline): An unfitted sklearn Pipeline
        X (pd.DataFrame): Training features
        y (pd.Series): Training target labels

    Returns:
        Pipeline: The fitted pipeline, ready for prediction

    """
    return pipeline.fit(X, y)


def log_and_save(
        pipeline: Pipeline,
        params: dict,
        metrics: dict,
        run_name: str,
        save_path: Path
)-> None:
    """
    Log parameters and metrics to MLflow and save the pipeline to disk.

    Args:
        pipeline (Pipeline): A fitted sklearn Pipeline to persist.
        params (dict): Model parameters to log 
        metrics (dict): Evaluation metrics to log 
        run_name (str): Name of the MLflow run
        save_path (Path): File path to save the pipeline as .joblib
                (e.g., BASE_DIR / "models" / "pipeline.joblib")

    Returns:
        None
    
    """
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipeline, "model")


    joblib.dump(pipeline, save_path)





    