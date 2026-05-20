
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline

from src.models.selector import SelectionResult



@dataclass(frozen=True)
class ModelArtifact:
    pipeline: Pipeline
    threshold: float
    cost_ratio: tuple[float, float]
    model_name: str
    metadata: dict[str, Any]



def _selection_result_to_json_dict(result: SelectionResult) -> dict[str, Any]:
    """
    Convert a SelectionResult into a JSON-safe dictionary for persistence.


    Only the metadata and metrics are included. The fitted pipeline
    is saved seperately via joblib, and 'comparison' is excluded
    (it belongs in MLFlow, not in the deployable artifact)

    """
    metadata_dict = asdict(result.selection_metadata)

    clean_metrics = {
        key: float(value) for key, value in result.validation_metrics.items()
    }

    return {
        "model_name": result.best_model_name,
        "threshold": float(result.threshold),
        "cost_ratio": list(result.cost_ratio),
        "validation_metrics": clean_metrics,
        "selection_metadata": metadata_dict,
    }





def save_model(
        result: SelectionResult,
        directory: Path,
        overwrite: bool = False,
) -> None:
    """
    Persist the deployable artifact to directory.


    Writes two files:
        1. model.joblib - the fitted pipeline   (binary)
        2. metadata.json - threshold, metrics, identity (human-readable)
    
    If directory already exists and overwrite is False (the default),
    a "FileExistsError" is raised to prevent accidental replacement
    of a deployed model. Pass overwrite=True to intentionally to replace.

    """
    
    if directory.exists() and not overwrite:
        raise FileExistsError(
            f"Directory {directory} already exists."
            f" Pass overwrite=True to replace it"
        )
    
    directory.mkdir(parents=True, exist_ok=True)

    joblib.dump(result.best_estimator, directory / "model.joblib")

    metadata_dict = _selection_result_to_json_dict(result)
    with open(directory / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)



def load_model(directory: Path) -> ModelArtifact:
    """
    Load a previously saved model artifact from directory.

    Expects two files:
        1. model.joblib - the fitted pipeline
        2. metadata.json - threshold, metric, identity

    Returns a fully-loaded 'ModelArtifact' ready for scoring or monitoring
    
    """

    if not directory.exists():
        raise FileNotFoundError(f"Artifact directory not found: {directory}")
    
    joblib_path = directory / "model.joblib"
    json_path = directory / "metadata.json"


    if not joblib_path.exists():
        raise FileNotFoundError(f"Missing pipeline file: {joblib_path}")
    if not json_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {json_path}")
    
    pipeline = joblib.load(joblib_path)

    with open(json_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)

    # Undo the save-time conversion
    threshold = float(metadata_dict["threshold"])
    cost_ratio = tuple(metadata_dict["cost_ratio"])

    return ModelArtifact(
        pipeline=pipeline,
        threshold=threshold,
        cost_ratio=cost_ratio,
        model_name=metadata_dict["model_name"],
        metadata=metadata_dict,
    )






