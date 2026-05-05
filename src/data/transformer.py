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



def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = _strip_string_columns(df)
    return df