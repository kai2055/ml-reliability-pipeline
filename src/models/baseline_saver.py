
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from src.models.dataset_builder import NUMERICAL_FEATURES, CATEGORICAL_FEATURES

def compute_baseline(X_train: pd.DataFrame) -> dict:
    """
    Compute the distribution snapshot for the training data.

    For each numerical feature, stores 99 percentiles, mean, standard
    deviation (population, doof=0), min, max, and the fraction of
    missing values. For each categorical feature, stores the frequency
    of every observed category (inclludng missing as a separate 
    category).

    Args:
        X_train: Feature DataFrame used to fit the deployed model

    Returns:
    A dict with keys "metadata", "numerical", and "categorical".
    All values are JSON-safe.
    
    
    """
    baseline = {
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "n_training_rows": len(X_train),
            "numerical_features": list(NUMERICAL_FEATURES),
            "categorical_features": list(CATEGORICAL_FEATURES),
        },
        "numerical": {},
        "categorical": {},
    }

    percentiles = [i / 100 for i in range(1, 100)]

    for col in NUMERICAL_FEATURES:
        series = X_train[col]
        missing_fraction = float(series.isna().mean())
        values = series.dropna().astype(float)
        baseline["numerical"][col] = {
            "percentiles": np.quantile(values, percentiles).tolist(),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "min": float(values.min()),
            "max": float(values.max()),
            "missing_fraction": missing_fraction,
        }

    for col in CATEGORICAL_FEATURES:
        counts = X_train[col].value_counts(dropna=False)
        frequencies = (counts / counts.sum()).to_dict()
        baseline["categorical"][col] = {
            str(k): float(v) for k, v in frequencies.items()
        }

    return baseline



def save_baseline(
        baseline: dict,
        directory: Path,
        overwrite: bool = False,
) -> None:
    """
    Persist the baseline dictionary as baseline.json in directory.

    Creates the directory if it does not exist. If the JSON file
    already exists and the overwrite is False (the default), a 
    FileExistError is raised to prevent accidental replacement
    of the monitoring reference. Pass overwrite=True to replace
    intentionally.

    The overwrite guard protects the file, not the directory, because
    the baseline usually lives alongside a previously saved model artifact
    
    """
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / "baseline.json"

    if file_path.exists() and not overwrite:
        raise FileExistsError(
            f"{file_path} already exists. Pass overwrite=True to replace it."
        )
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)




def load_baseline(directory: Path) -> dict:
    """
    Load a previously saved baseline from dictionary.

    Expects the file baseline.json in the given directory.
    Returns the dictionary originally produced by compute_baseline.
    
    
    """
    file_path = directory / "baseline.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {file_path}")
    

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    

