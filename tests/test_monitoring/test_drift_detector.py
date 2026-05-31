
import pytest
import pandas as pd
import numpy as np


from src.monitoring.drift_detector import detect_drift, FeatureMismatchError



def test_raises_on_missing_feature():
    """
    detect_drift raises FeatureMismatchError if a baseline feature is absent.
    """
    baseline = {
        "numerical": {"income": {"percentiles": [10, 20, 30], "std": 5.0}},
        "categorical": {},
    }
    production = pd.DataFrame({"other_column": [1, 2, 3]})

    with pytest.raises(FeatureMismatchError, match="income"):
        detect_drift(baseline, production)



def test_output_contract_shape():
    """Each baseline feature gets one FeatureDriftResult with correct types"""
    baseline = {
        "numerical": {
            "loan_amount": {
                "percentiles": list(range(1, 100)),
                "std": 5.0
            }
        },
        "categorical": {
            "loan_type": {"a": 0.5, "b": 0.5}
        },
    }
    production = pd.DataFrame({
        "loan_amount": [15, 25, 35, 45, 55, 65, 75, 85],
        "loan_type": ["a", "b", "a", "b", "a", "b", "a", "b" ],

    })

    results = detect_drift(baseline, production)

    assert len(results) == 2

    numerical_result = [r for r in results if r.feature_type == "numerical"][0]
    categorical_result = [r for r in results if r.feature_type == "categorical"][0]

    assert numerical_result.feature_name == "loan_amount"
    assert isinstance(numerical_result.psi, float)
    assert isinstance(numerical_result.wasserstein, float)

    assert categorical_result.feature_name == "loan_type"
    assert isinstance(categorical_result.psi, float)
    assert categorical_result.wasserstein is None



def test_no_drift_yields_low_psi():
    """PSI should be near zero prodcution matches the baseline distribution"""
    
    baseline = {
        "numerical": {
            "loan_amount": {
                "percentiles": list(range(1, 100)),
                "std": 1.0,
            }
        },
        "categorical": {},
    }

    rng = np.random.default_rng(42)
    production = pd.DataFrame({
        "loan_amount": rng.integers(1, 101, size=1000),
    })

    results = detect_drift(baseline, production)
    psi = results[0].psi

    assert psi < 0.1



def test_real_drift_tields_high_psi():
    """PSI should be large when prodcution is concentrated in one region"""
    baseline = {
        "numerical": {
            "loan_amount": {
                "percentiles": list(range(1, 100)),
                "std": 1.0,
            }
        },
        "categorical": {},
    }

    rng = np.random.default_rng(42)
    production = pd.DataFrame({
        "loan_amount": rng.integers(1, 31, size=1000),
    })

    results = detect_drift(baseline, production)
    psi = results[0].psi

    assert psi > 0.25 # ADR 023 "significant shift's band"