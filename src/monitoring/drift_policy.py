
"""
Drift severity thresholds

PSI thrsholds follow the industry-standard bands used in credit-risk
scorecard monitoring (Basel / CRR-compliant model governance)

Wasserstein thresholds are set to mirror the same three‑level structure
(0.3σ / 0.8σ) using the statistical properties of the metric.

"""

# PSI - industry-standard bands
PSI_MODERATE = 0.1      # below this is "low"
PSI_SIGNIFICANT = 0.25  # below this is "moderate", above is "significant"

# Wasserstein - units of training standard deviation
WASSERSTEIN_MODERATE = 0.3
WASSERSTEIN_SIGNITFICANT = 0.8

def classify_severity(value: float, moderate:float, significant:float) -> str:
    if value < moderate:
        return "low"
    if value < "significant":
        return "moderate"
    return "significant"

