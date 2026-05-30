
from dataclasses import dataclass
from typing import Optional

from src.monitoring.drift_detector import FeatureDriftResult
from src.monitoring.drift_policy import (
    PSI_MODERATE, PSI_SIGNIFICANT,
    WASSERSTEIN_MODERATE, WASSERSTEIN_SIGNITFICANT,
    classify_severity,
)


# Report dataclasses

@dataclass(frozen=True)
class ReportSummary:
    significant: int
    moderate: int
    low: int
    total_features: int



@dataclass(frozen=True)
class FeatureDriftDetail:
    feature_name: str
    feature_type: str
    psi: float
    psi_severity: str
    wasserstein: Optional[float]
    wasserstein_severity: Optional[str]     # None for categoricals


@dataclass(frozen=True)
class DriftReport:
    summary: ReportSummary
    details: list[FeatureDriftDetail]


# Helpers


def _psi_severity(psi: float) -> str:
    return classify_severity(psi, PSI_MODERATE, PSI_SIGNIFICANT)



def _wasserstein_severity(wasserstein: Optional[float]) -> Optional[str]:
    if wasserstein is None:
        return None
    return classify_severity(wasserstein, WASSERSTEIN_MODERATE, WASSERSTEIN_SIGNITFICANT)





# Main function

def generate_report(results: list[FeatureDriftDetail]) -> DriftReport:
    """
    Convert raw drift results into a structured, human-readable report.

    Features are sorted worst-first so the most deifted features
    appear at the top of the detail lisr
    
    """
    details: list[FeatureDriftDetail] = []
    significant = moderate = low = 0

    for r in results:
        psi_sev = _psi_severity(r.psi)
        wass_sev = _wasserstein_severity(r.wasserstein)

        worst = psi_sev
        if wass_sev == "significant" or (wass_sev == "moderate" and worst == "low"):
            worst = wass_sev

        if worst == "significant":
            significant += 1
        elif worst == "moderate":
            moderate += 1
        else:
            low += 1

        details.append(FeatureDriftDetail(
            feature_name=r.feature_name,
            feature_type=r.feature_type,
            psi=r.psi,
            psi_severity=psi_sev,
            wasserstein=r.wasserstein,
            wasserstein_severity=wass_sev,
        ))


    severity_order = {"significant": 0, "moderate":1, "low":2}
    details.sort(key=lambda d: (severity_order[d.psi_severity], -d.psi))

    return DriftReport(
        summary=ReportSummary(
            significant=significant,
            moderate=moderate,
            low=low,
            total_features=len(results),
        ),
        details=details,
    )
