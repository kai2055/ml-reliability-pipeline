import pandas as pd

from src.data.schema import (
    STRING_COLUMNS,
    INTEGER_COLUMNS,
    FLOAT_COLUMNS,
    DATE_COLUMNS,
)


def _strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in STRING_COLUMNS:
        df[col] = df[col].str.strip()
    return df

def _lowercase_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in STRING_COLUMNS:
        df[col] = df[col].str.lower()
    return df

def _remove_internal_whitespace(s: pd.Series) -> pd.Series:\
    return s.str.replace(" ", "", regex=False)

def _coerce_revolver_status(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0}).astype("Int64")

def _coerce_integer_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in INTEGER_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df




def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = _strip_string_columns(df)
    df = _lowercase_string_columns(df)
    df["loanstatus"] = _remove_internal_whitespace(df["loanstatus"])
    df["revolverstatus"] = _coerce_revolver_status(df["revolverstatus"])
    df = _coerce_integer_columns(df)

    return df


