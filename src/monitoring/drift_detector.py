
"""
Drift detection: PSI and Wasserstein comparison against baseline.

"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

logger = logging.getLogger(__name__)

N_PSI_BINS = 10             # equal-frequecy bins for numerical PSI
PSI_EPSILON = 1e-4          # floor for zero fraction in pSI formula


class FeatureMismatchError(Exception):
    """
    Raised when production data is missing features present in the baseline.
    """



# Output dataclass
@dataclass(frozen=True)
class FeatureDriftResult:
    """ Drift score for a single feature """
    feature_name: str
    feature_type: str       # "numerical" or "categorical"
    psi: float
    wasserstein: Optional[float] = None     # None for categoricals


# PSI helpers
def _psi_numerical(
        baseline_stats: dict,
        production_col: pd.Series,        
) -> float:
    """
    PSI for a numerical feature, using percentile-derived equal-frequency bins

    """

    if 100 % N_PSI_BINS != 0:
        raise ValueError(
            f"N_PSI_BINS must divide 100; got {N_PSI_BINS}"
        )
    
    percentiles = baseline_stats["percentiles"]
    spacing = 100 // N_PSI_BINS

    edges = [-np.inf]
    for k in range(1, N_PSI_BINS):      # k = 1...9
        target_percentile = k * spacing  # 10, 20, .... 90
        edges.append(percentiles[target_percentile - 1])    # stored at index p-1
    edges.append(np.inf)

    expected = 1.0 / N_PSI_BINS
    prod_values = production_col.dropna().astype(float)
    prod_counts, _ = np.histogram(prod_values, bins=edges)
    total = prod_counts.sum()
    if total == 0:
        return 0.0
    

    psi = 0.0
    for count in prod_counts:
        actual = max(count / total, PSI_EPSILON)
        exp = max(expected, PSI_EPSILON)
        psi += (actual - exp) * np.log(actual / exp)
    return float(psi)




def _psi_categorical(
        baseline_freqs: dict[str, float],
        production_col: pd.Series,
) -> float:
    """PSI for a categorical feature, using stored category frequencies"""
    counts = production_col.value_counts(dropna=False)
    total = counts.sum()
    if total == 0:
        return 0.0
    
    prod_freqs = {str(k): v / total for k, v in counts.items()}
    all_cats = set(baseline_freqs.keys()) | set(prod_freqs.keys())

    psi = 0.0
    for cat in all_cats:
        actual = max(prod_freqs.get(cat, 0.0), PSI_EPSILON)
        expected = max(baseline_freqs.get(cat, 0.0), PSI_EPSILON)
        psi += (actual - expected) * np.log(actual / expected)
    return float(psi)



# Wassertein Helper

def _wasserstein_numerical(
        baseline_stats: dict,
        production_col: pd.Series,
) -> float:
    """Std-normalised Wasserstein distance for a numerical feature"""
    percentiles = baseline_stats["percentiles"]
    std = baseline_stats["std"]

    prod_values = production_col.dropna().astype(float)
    if len(prod_values) == 0:
        return 0.0
    
    raw_distance = wasserstein_distance(percentiles, prod_values)

    # Normalise by baseline std (ADR 023) so that score is unitless and
    # comparable across features. Guard against a zero-variance feature.
    if std == 0:
        return 0.0
    
    return float(raw_distance / std)



# Main function
def detect_drift(
        baseline: dict,
        production_data: pd.DataFrame,
) -> list[FeatureDriftResult]:
    """Compare production feature distributions against the training baseline
    
    Args:
        baseline: Loaded baseline dictionary (from baseline_loader)
        production_data: Processed production features (X only)

    Returns:
        One 'FeatureDriftResult' per baseline feature. Wasserstein is 'None' for categorical features
    
    Raises:
        FeatureMismatchError: If any baseline feature is absent from the 
        production DataFrame.
    """

    baseline_numerical = set(baseline.get("numerical", {}).keys())
    baseline_categorical = set(baseline.get("categorical", {}).keys())
    production_cols = set(production_data.columns)

    # Missing features -> fatal
    missing = (baseline_numerical | baseline_categorical) - production_cols
    if missing:
        raise FeatureMismatchError(
            f"Production data missing baseline features: {sorted(missing)}"
        )
    
    # Extra feature -> warn (deferred tracker item)
    extra = production_cols - baseline_numerical - baseline_categorical
    if extra:
        logger.warning(
            "Production data contains %d extra features not in baseline: %s",
            len(extra), sorted(extra),
        )

    results: list[FeatureDriftResult] = []

    # Numerical features
    for feature in sorted(baseline_numerical):
        stats = baseline["numerical"][feature]
        psi = _psi_numerical(stats, production_data[feature])
        was = _wasserstein_numerical(stats, production_data[feature])
        results.append(FeatureDriftResult(
            feature_name=feature,
            feature_type="numerical",
            psi=psi,
            wasserstein=was,
        ))

    # Categorical features
    for feature in sorted(baseline_categorical):
        freqs = baseline["categorical"][feature]
        psi = _psi_categorical(freqs, production_data[feature])
        results.append(FeatureDriftResult(
            feature_name=feature,
            feature_type="categorical",
            psi=psi,
        ))

    return results



    
