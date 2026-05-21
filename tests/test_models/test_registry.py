
from src.models.registry import save_model, load_model
import json
import pytest


def test_save_load_preserves_core_fields(sample_selection_result, tmp_path):
    result = sample_selection_result
    model_dir = tmp_path / "model"

    save_model(result, model_dir)
    artifact = load_model(model_dir)

    assert artifact.model_name == result.best_model_name
    assert artifact.threshold == result.threshold
    assert artifact.cost_ratio == result.cost_ratio

    assert artifact.pipeline.get_params() == result.best_estimator.get_params()


def test_save_load_preserves_metric_values(sample_selection_result, tmp_path):
    result = sample_selection_result
    model_dir = tmp_path / "model"

    save_model(result, model_dir)
    artifact = load_model(model_dir)

    original_metrics = result.validation_metrics
    loaded_metrics = artifact.metadata["validation_metrics"]

    assert loaded_metrics == original_metrics


def test_comparison_excluded_from_json(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"

    save_model(sample_selection_result, model_dir)

    with open(model_dir / "metadata.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "comparison" not in data


def test_metadata_contains_expected_keys(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"

    save_model(sample_selection_result, model_dir)
    artifact = load_model(model_dir)

    assert "selection_metadata" in artifact.metadata
    assert "validation_metrics" in artifact.metadata
    assert "model_name" in artifact.metadata
    assert "threshold" in artifact.metadata
    assert "cost_ratio" in artifact.metadata



def test_save_refuses_overwrite_by_default(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"
    save_model(sample_selection_result, model_dir)

    with pytest.raises(FileExistsError):
        save_model(sample_selection_result,model_dir)



def test_save_overwrite_succeeds(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"

    save_model(sample_selection_result, model_dir)
    save_model(sample_selection_result, model_dir, overwrite=True)

    artifact = load_model(model_dir)
    assert artifact.model_name == sample_selection_result.best_model_name


def test_load_missing_directory_raises(tmp_path):
    missing_dir = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError):
        load_model(missing_dir)



def test_load_missing_joblib_raises(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"
    save_model(sample_selection_result, model_dir)

    (model_dir / "model.joblib").unlink()

    with pytest.raises(FileNotFoundError):
        load_model(model_dir)


def test_load_missing_metadata_raises(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"
    save_model(sample_selection_result, model_dir)

    (model_dir / "metadata.json").unlink()

    with pytest.raises(FileNotFoundError):
        load_model(model_dir)



def test_json_contains_correct_types(sample_selection_result, tmp_path):
    model_dir = tmp_path / "model"
    save_model(sample_selection_result, model_dir)

    with open(model_dir / "metadata.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data["cost_ratio"], list)

    for key, value in data["validation_metrics"].items():
        assert isinstance(value, float), f"{key} is {type(value)}, not float"

        