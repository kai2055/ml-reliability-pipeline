
from typing import Tuple
import pandas as pd

NUMERICAL_FEATURES = [
    "grossapproval",
    "sbaguaranteedapproval",
    "initialinterestrate",
    "terminmonths",
    "jobssupported",
]

CATEGORICAL_FEATURES = [
    "subprogram",
    "processingmethod",
    "fixedorvariableinterestind",
    "revolverstatus",
    "businesstype",
    "businessage",
    "collateralind",
]


_VALID_OUTCOMES = frozenset({"pif", "chgoff"})


def _filter_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only rows with a resolved loan outcome.
    Drops any row where loanstatus is not 'pif' or 'chgoff'.

    Args:
        df: Clean DataFrame from the data layer. Must contain 'loanstatus'

    Returns:
        DataFrame containing only resolved-outcome rows
    
    """
    mask = df["loanstatus"].isin(_VALID_OUTCOMES)
    return df.loc[mask].copy()


def _derive_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Convert loanstatus to a binary target and remove it from features.

    Mapping:
        pif     -> 0 (paid in full  - good outcome)
        chgoff  -> 1 (charged off  - default)

    Args:
        df: DataFrame containing only resolved-outcome rows.

    Returns:
        Tuple of (DataFrame without loanstatus, binary target Series)

    """
    y = df["loanstatus"].map({"pif": 0, "chgoff": 1}).astype("int8")
    X_candidates = df.drop(columns=["loanstatus"])
    return X_candidates, y


def _select_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop every column that is not in the v1 feature set.

    Combines NUMERICAL_FEATURES and CATEGORICAL FEATURES into the
    v1 set. Any column not on that list is silently excluded.

    Args:
        df: DataFrame after target derivation

    Returns:
        DataFrame with exactly 12 columns (5 numerical + 7 categorical)

    """
    feature_columns = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    return df[feature_columns].copy()


def _fill_missing_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].fillna("missing")
    return df


def build_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Transform a clean data-layer DataFrame into model-ready X and y.


    Pipeline:
        1. _filter_rows     -> narrow to resolved outcomes
        2. _derive_target   -> create y, remove loanstatus from candidates
        3. _select_features -> keep only v1 feature columns

    Args:
        df: Clean typed DataFrame 

    Returns:
        Tuple of:
            X - pd.DataFrame with 12 feature columns (5 numerical, 7 categorical)
            y - pd.Series of int8 values (0 for pif, 1 for chgoff)

    """

    df = _filter_rows(df)
    df, y = _derive_target(df)
    X = _select_features(df)
    X = _fill_missing_categoricals(X)
    return X, y


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the v1 feature columns from a transformed, validated DataFrame.

    Unlike build_dataset, this function does not filter rows by loanstatus
    or derive a target. It is used by the monitoring layer, where production
    loans have not yet resolved to a known outcome.

    Args:
        df: Clean typed DataFrame from the data layer

    Returns:
        DataFrame with exactly 12 feature columns (5 numerical, 7 categorical)
    
    
    """
    X = _select_features(df)
    X = _fill_missing_categoricals(X)
    return X
