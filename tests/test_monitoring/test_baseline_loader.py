
import json
import pytest
from src.monitoring.baseline_loader import load_baseline, BaselineLoadError



def test_loads_valid_baseline(tmp_path):
    data = {"numerical": {"a": {"percentiles": [0.1, 0.5, 0.9]}}, "metadata":{}}
    (tmp_path / "baseline.json").write_text(json.dumps(data), encoding="utf-8")

    result = load_baseline(tmp_path)
    assert result == data

def test_raises_on_missing_file(tmp_path):
    with pytest.raises(BaselineLoadError, match="Baseline file not found"):
        load_baseline(tmp_path)


def test_raises_on_invalid_json(tmp_path):
    (tmp_path / "baseline.json").write_text("{invalid}", encoding="utf-8")

    with pytest.raises(BaselineLoadError, match="not valid JSON"):
        load_baseline(tmp_path)

        
