
"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app

@pytest.fixture(scope="module")
def client():
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