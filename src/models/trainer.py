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

    Rerurns: 
        Pipeline: Assembled pipeline with steps:
            ("preprocessing", ColumnTransformer) and ("model", model) 
    """


    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", OneHotEncoder(), categorical_cols)
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



def train(pipeline: Pipeline, X: pd.DataFrame, Y:pd.Series) ->Pipeline:
    """
    Fit a pipeline on training data

    Args: 
        pipeline (Pipeline): An unfitted sklearn Pipeline
        X (pd.DataFrame): Training features
        Y (pd.Series): Training target labels

    Returns:
        Pipeline: The fitted pipeline, ready for prediction

    """
    return pipeline.fit(X, Y)




    