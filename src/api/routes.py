"""API route definitions."""

import uuid
import logging
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
from src.data.schema import (
    STRING_COLUMNS,
    INTEGER_COLUMNS,
    FLOAT_COLUMNS,
    DATE_COLUMNS,
)
from src.data.transformer import transform
from src.data.validator import run_fatal_checks, check_columns
from src.models.dataset_builder import build_features
from src.monitoring.drift_detector import detect_drift, FeatureMismatchError
from src.monitoring.report_generator import generate_report

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_full_dataframe(loan_dict: dict) -> pd.DataFrame:
    """Create a complete SBA‑shaped DataFrame with defaults for non‑feature columns."""
    n_rows = 1
    full = {col: ["x"] * n_rows for col in STRING_COLUMNS}
    full.update({col: [1] * n_rows for col in INTEGER_COLUMNS})
    full.update({col: [1.0] * n_rows for col in FLOAT_COLUMNS})
    full.update({col: ["1999-02-02"] * n_rows for col in DATE_COLUMNS})
    # Override with the user‑provided feature values
    full.update(loan_dict)
    return pd.DataFrame(full)


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
        "validation_metrics": model.validation_metrics,
    }


@router.post("/predict", response_model=list[PredictResponse])
def predict(payload: PredictRequest, request: Request):
    """Score a batch of loan applications and return default probabilities."""
    model = get_model(request)
    responses: list[PredictResponse] = []

    for loan in payload.loans:
        try:
            # Build a full DataFrame (all 43 columns) from the single loan
            raw_df = _build_full_dataframe(loan.model_dump())
            transformed_df = transform(raw_df)

            col_result = check_columns(transformed_df)
            if col_result["status"] == "fail":
                raise HTTPException(
                    status_code=422,
                    detail=f"Column check failed: {col_result.get('details', {})}",
                )

            features_df = build_features(transformed_df)
            prob = model.pipeline.predict_proba(features_df)[0][1]
            decision = "reject" if prob >= model.threshold else "approve"

            responses.append(
                PredictResponse(
                    default_probability=round(float(prob), 4),
                    decision=decision,
                    threshold=model.threshold,
                )
            )

        except HTTPException:
            raise
        except Exception:
            error_id = uuid.uuid4().hex[:8]
            logger.exception("prediction failed [%s]", error_id)
            raise HTTPException(
                status_code=500,
                detail=f"Internal error (ref {error_id})",
            )

    return responses


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
