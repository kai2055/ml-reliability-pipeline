
"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def client():
    mock_model = MagicMock()
    mock_model.model_name = "xgboost"
    mock_model.threshold = 0.41
    mock_model.metadata = {"validation_metrics": {"precision": 0.54, "recall": 0.89}}
    mock_model.pipeline.predict_proba.return_value = [[0.7, 0.3]]

    mock_baseline = {
    "numerical": {
        "grossapproval": {"percentiles": list(range(1, 100)), "std": 1.0, "mean": 50.0, "min": 1.0, "max": 100.0, "missing_fraction": 0.0},
        "sbaguaranteedapproval": {"percentiles": list(range(1, 100)), "std": 1.0, "mean": 50.0, "min": 1.0, "max": 100.0, "missing_fraction": 0.0},
        "initialinterestrate": {"percentiles": list(range(1, 100)), "std": 1.0, "mean": 50.0, "min": 1.0, "max": 100.0, "missing_fraction": 0.0},
        "terminmonths": {"percentiles": list(range(1, 100)), "std": 1.0, "mean": 50.0, "min": 1.0, "max": 100.0, "missing_fraction": 0.0},
        "jobssupported": {"percentiles": list(range(1, 100)), "std": 1.0, "mean": 50.0, "min": 1.0, "max": 100.0, "missing_fraction": 0.0},
    },
    "categorical": {
        "subprogram": {"guaranty": 1.0},
        "processingmethod": {"sba express program": 1.0},
        "fixedorvariableinterestind": {"v": 1.0},
        "revolverstatus": {"0": 1.0},
        "businesstype": {"corporation": 1.0},
        "businessage": {"existing or more than 2 years old": 1.0},
        "collateralind": {"true": 1.0},
    },
    "metadata": {}
}

    with patch("src.api.app.load_model", return_value=mock_model), \
         patch("src.api.app.load_baseline", return_value=mock_baseline):
        with TestClient(app) as c:
            yield c



def test_health(client):
    """Get /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_info(client):
    """GET /model/info returns model metadata"""
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "threshold" in data
    assert "validation_metrics" in data



def test_predict(client):
    """POST /predict returns a valid prediction response."""
    payload = {
        "features": {
            "grossapproval": 50000,
            "sbaguaranteedapproval": 37500.0,
            "initialinterestrate": 6.5,
            "terminmonths": 84,
            "jobssupported": 5,
            "subprogram": "guaranty",
            "processingmethod": "sba express program",
            "fixedorvariableinterestind": "v",
            "revolverstatus": 0,
            "businesstype": "corporation",
            "businessage": "existing, 5 or more years",
            "collateralind": "true",
        }
    }
    response = client.post("/predict", json=payload)
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "default_probability" in data
    assert "decision" in data
    assert data["decision"] in ("approve", "reject")
    assert 0.0 <= data["default_probability"] <= 1.0





def test_monitor(client):
    """POST /monitor returns a valid drift report."""
    # Send two minimal records — enough to exercise the chain
    records = [
        {
            "asofdate": "2020-01-01",
            "program": "7A",
            "grossapproval": 50000,
            "sbaguaranteedapproval": 37500.0,
            "initialinterestrate": 6.5,
            "terminmonths": 84,
            "jobssupported": 5,
            "subprogram": "guaranty",
            "processingmethod": "sba express program",
            "fixedorvariableinterestind": "V",
            "revolverstatus": "0",
            "businesstype": "Corporation",
            "businessage": "Existing or more than 2 years old",
            "collateralind": "True",
            "loanstatus": "P I F",
            "locationid": "x",
            "borrname": "x",
            "borrstreet": "x",
            "borrcity": "x",
            "borrstate": "x",
            "borrzip": "x",
            "bankname": "x",
            "bankfdicnumber": "x",
            "bankncuanumber": "x",
            "bankstreet": "x",
            "bankcity": "x",
            "bankstate": "x",
            "bankzip": "x",
            "approvaldate": "2020-01-01",
            "approvalfy": 2020,
            "firstdisbursementdate": "2020-01-01",
            "naicscode": "x",
            "naicsdescription": "x",
            "franchisecode": "x",
            "franchisename": "x",
            "projectcounty": "x",
            "projectstate": "x",
            "sbadistrictoffice": "x",
            "congressionaldistrict": "x",
            "paidinfulldate": "2021-01-01",
            "chargeoffdate": "x",
            "grosschargeoffamount": 0.0,
            "soldsecmrktind": "x",
        }
    ]
    response = client.post("/monitor", json=records)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "details" in data
    assert data["summary"]["total_features"] == 12
