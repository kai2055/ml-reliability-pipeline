import pandas as pd

from src.data.schema import (
    STRING_COLUMNS,
    INTEGER_COLUMNS,
    FLOAT_COLUMNS,
    DATE_COLUMNS,
)

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df