
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    roc_auc_score,
    log_loss,
    brier_score_loss,

)
from sklearn.pipeline import Pipeline


def predict(pipeline: Pipeline, X: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """
    Generate predicted probabilities and hard labels

    Probabilities are obtained from the pipeline's predict_proba() method.
    Hard labels are derived by applying the decision threshold: probability
    >= threshold -> 1 (approved), otherwise 0 (regardless).
    
    Args:
        pipeline (Pipeline): A fitted sklearn Pipeline. Must have predict_proba()
        X (pd.DataFrame): Test features
        threshold (float): Probability cutoff above which an applicant is labelled 1 (approved.)
                Defaults to 0.50

    

    Returns:
        pd.Dataframe: DataFrame with columns:
                - 'predicted_proba': probability of the positive class (default)
                - 'predicted_label': hard label (0 or 1) based on threshold

    
    """
    # Get probabilities for the positive class (index 1 for binary)
    proba = pipeline.predict_proba(X)[:, 1]

    labels = (proba >= threshold).astype(int)

    return pd.DataFrame({
        "predicted_proba": proba,
        "predicted_label": labels
    })
    



def evaluate(y_true: pd.Series, predictions: pd.DataFrame) -> dict:
    """
    Compute performance metrics for a credit risk model

    Calculates both threshold-dependent metrics (precision, recall)
    using the hard labels, and probability-based metrics (ROC_AUC, log_loss, Brier score)
    using the predicted probabilities
    
    Args: 
        y_true (pd.Series): True binary labels (0/1)
        predictions (pd.DataFrame): Output of predict(), with columns
            'predicted_proba' and 'predicted_label'

    Returns:
        dict: Dictionary containing:
            - precision
            - recall
            - roc_auc
            - log_loss
            - brier_score

    """

    return {
        "precision": precision_score(y_true, predictions["predicted_label"], zero_division=0),

        # zero_division=0: when no positives are predicted, precision/recall are
        # undefined; we treat them as 0 rather than raising or emitting warnings.
        
        "recall": recall_score(y_true, predictions["predicted_label"], zero_division=0),


        "roc_auc": roc_auc_score(y_true, predictions["predicted_proba"]),
        "log_loss": log_loss(y_true, predictions["predicted_proba"]),
        "brier_score": brier_score_loss(y_true, predictions["predicted_proba"]),
    }
