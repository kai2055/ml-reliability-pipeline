
"""API route definitions."""

import pandas as pd
from fastapi import APIRouter, HTTPException, Request


from src.api.dependencies import get_model, get_baseline
from src.api.schemas import (
    PredictRequest,
    PredictResponse,
    MonitorResponse,
    FeatureDriftSummary,
    FeatureDriftDetail,
)
from src.data.transformer import transform
from src.data.validator import run_fatal_checks
from src.models.dataset_builder import build_features
from src.monitoring.drift_detector import detect_drift, FeatureMismatchError
from src.monitoring.report_generator import generate_report


router = APIRouter()


@router.get("/health")
def health():
    """Check the API is alive"""
    return {"status": "ok"}


@router.get("/model/info")
def model_info(request: Request):
    """Return metadata about the loaded model."""
    model = get_model(request)
    return {
        "model_name": model.model_name,
        "threshold": model.threshold,
        "validation_metrics": model.metadata.get("validation_metrics", {}),
    }


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, request: Request):
    """Score a single applicant and return default probability"""
    model = get_model(request)


    try:
        features_df = pd.DataFrame([payload.features])
        prob = model.pipeline.predict_proba(features_df)[0][1]
        decision = "reject" if prob >= model.threshold else "approve"

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    
    return PredictResponse(
        default_probability=round(float(prob), 4),
        decision=decision,
        threshold=model.threshold,
    )


@router.post("/monitor", response_model=MonitorResponse)
def monitor(records: list[dict], request: Request):
    """Run drift detection on a batch of production records."""
    baseline = get_baseline(request)

    try:
        raw_df = pd.DataFrame(records)
        transformed_df = transform(raw_df)
        run_fatal_checks(transformed_df, include_usable_rows=False)
        production_features = build_features(transformed_df)
        drift_results = detect_drift(baseline, production_features)
        report = generate_report(drift_results)
    except FeatureMismatchError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return MonitorResponse(
        summary=FeatureDriftSummary(
            significant=report.summary.significant,
            moderate=report.summary.moderate,
            low=report.summary.low,
            total_features=report.summary.total_features,
        ),
        details=[
            FeatureDriftDetail(
                feature_name=d.feature_name,
                feature_type=d.feature_type,
                psi=d.psi,
                psi_severity=d.psi_severity,
                wasserstein=d.wasserstein,
                wasserstein_severity=d.wasserstein_severity,
            )
            for d in report.details
        ],
    )