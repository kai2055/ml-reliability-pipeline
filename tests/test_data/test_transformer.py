
import pandas as pd
from src.data.transformer import (
    _strip_string_columns,
    _lowercase_string_columns,
    _collapse_internal_whitespace,
    _remove_internal_whitespace,
    _coerce_revolver_status,
    _coerce_float_columns,
    _coerce_integer_columns,
    _coerce_string_columns,
    _parse_date_columns,
    transform,

)

from src.data.schema import STRING_COLUMNS, INTEGER_COLUMNS, FLOAT_COLUMNS, DATE_COLUMNS


def _make_df(n_rows=1, **overrides):
    base = {col: ["x"] * n_rows for col in STRING_COLUMNS}
    base.update({col: [0] * n_rows for col in INTEGER_COLUMNS})
    base.update({col: [0.0] * n_rows for col in FLOAT_COLUMNS })
    base.update({col: ["1999-02-02"] * n_rows for col in DATE_COLUMNS} )
    base.update(overrides)

    return pd.DataFrame(base)




def test_strip_string_columns_removes_leading_and_trailing_whitespace():
    df = _make_df(n_rows=2, borrname=["     John    ", "Jane     "])
    result = _strip_string_columns(df)
    assert result["borrname"].tolist() == ["John", "Jane"]



def test_lowercase_string_columns_converts_to_lowercase():
    df = _make_df(n_rows=2, borrname=["NIKHIL", "Adhikari"])
    result = _lowercase_string_columns(df)
    assert result["borrname"].tolist() == ["nikhil", "adhikari"]


def test_collapse_internal_whitespace_reduces_multiple_spaces_to_one():
    df = _make_df(n_rows=2, borrname=["Nikhil   Adhikari", "Flyin     Monk"])
    result = _collapse_internal_whitespace(df)
    assert result["borrname"].tolist() == ["Nikhil Adhikari", "Flyin Monk"]


def test_remove_internal_whitespace_strips_all_spaces():
    series = pd.Series(["P I F", "C H G O F F"])
    result = _remove_internal_whitespace(series)
    assert result.tolist() == ["PIF", "CHGOFF"]


def test_coerce_revolver_status_converts_lowercase_strings():
    series = pd.Series(["true", "false", "true"])
    result = _coerce_revolver_status(series)
    assert result.tolist() == [1, 0, 1]

def test_coerce_revolver_status_converts_uppercase_strings():
    series = pd.Series(["TRUE", "FALSE"])
    result = _coerce_revolver_status(series)
    assert result.tolist() == [1, 0]


def test_coerce_revolver_status_returns_int64_dtype():
    series = pd.Series(["true", "false"])
    result = _coerce_revolver_status(series)
    assert result.dtype == "Int64"

def test_coerce_string_columns_converts_non_object_to_string():
    df = _make_df(borrname=[123])
    result = _coerce_string_columns(df)
    assert result["borrname"].dtype == "string"

def test_coerce_integer_columns_produces_int64():
    df = _make_df(grossapproval=[42])
    result = _coerce_integer_columns(df)
    assert result["grossapproval"].dtype == "Int64"

def test_coerce_integer_columns_coerces_invalid_to_na():
    df = _make_df(grossapproval=["not a number"])
    result = _coerce_integer_columns(df)
    assert pd.isna(result["grossapproval"].iloc[0])

def test_coerce_float_columns_produces_float64():
    df = _make_df(initialinterestrate=[3.5])
    result = _coerce_float_columns(df)
    assert result["initialinterestrate"].dtype == "float64"

def test_parse_date_columns_produces_datetime64():
    df = _make_df(asofdate=["2024-01-15"])
    result = _parse_date_columns(df)
    assert result["asofdate"].dtype == "datetime64[ns]"

def test_transform_does_not_mutate_input():
    df = _make_df(borrname=["   Nikhil    "])
    original_value = df["borrname"].iloc[0]
    transform(df)
    assert df["borrname"].iloc[0] == original_value

def test_transform_produces_lowercase_stripped_strings():
    df = _make_df(borrname=["    NIKHIL    "])
    result = transform(df)
    assert result["borrname"].iloc[0] == "nikhil"

def test_transform_produces_correct_dtypes():
    df = _make_df()
    result = transform(df)
    assert result["borrname"].dtype == "string"
    assert result["grossapproval"].dtype == "Int64"
    assert result["initialinterestrate"].dtype == "float64"
    assert result["asofdate"].dtype == "datetime64[ns]"












