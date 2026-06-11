"""Pydantic schema for API request and response validation"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Predict request / response ────────────────────────────────────

class LoanFeatures(BaseModel):
    """The 12 features the model was trained on (v1 feature set)."""
    grossapproval: float = Field(gt=0)
    sbaguaranteedapproval: float = Field(ge=0)
    initialinterestrate: float = Field(ge=0, le=50)
    terminmonths: int = Field(gt=0, le=600)
    jobssupported: int = Field(ge=0)
    subprogram: str
    processingmethod: str
    fixedorvariableinterestind: str
    revolverstatus: str
    businesstype: str
    businessage: str
    collateralind: str

    model_config = {"extra": "forbid"}


class PredictRequest(BaseModel):
    """Accept a list of loans (batch). A single loan should be sent as a list
    with one element. The endpoint returns one prediction per loan."""
    loans: list[LoanFeatures] = Field(min_length=1, max_length=1000)


class PredictResponse(BaseModel):
    default_probability: float
    decision: str  # "approve" or "reject"
    threshold: float


# ── Monitor response ──────────────────────────────────────────────

class FeatureDriftSummary(BaseModel):
    significant: int
    moderate: int
    low: int
    total_features: int


class FeatureDriftDetail(BaseModel):
    feature_name: str
    feature_type: str
    psi: float
    psi_severity: str
    wasserstein: Optional[float]
    wasserstein_severity: Optional[str]


class MonitorResponse(BaseModel):
    summary: FeatureDriftSummary
    details: list[FeatureDriftDetail]