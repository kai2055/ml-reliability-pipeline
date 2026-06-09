"""Pydantic schema for API request and response validation"""

from pydantic import BaseModel
from typing import Optional



class PredictRequest(BaseModel):
    features: dict[str, float | str | int | None]



class PredictResponse(BaseModel):
    default_probability: float
    decision: str  # "approve" or "reject"
    threshold: float


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
    