
from src.data.validator import (
    check_columns,
    check_usable_rows,
    check_program_values,
    check_missing_rates,
    check_unknown_values,
    check_required_columns
)
from tests.conftest import _make_df


def test_check_columns_passes_for_valid_dataframe():
    df = _make_df()
    result = check_columns(df)
    assert result["status"] == "pass"


def test_check_columns_fails_when_column_missing():
    df = _make_df()
    df = df.drop(columns=["program"])
    result = check_columns(df)
    assert result["status"] == "fail"
    assert "program" in result["details"]["missing"]


def test_check_columns_fails_when_extra_columns_present():
    df = _make_df()
    df["unexpected_column"] = "x"
    result = check_columns(df)
    assert result["status"] == "fail"
    assert "unexpected_column" in result["details"]["extra"]



def test_check_usable_rows_passes_when_threshold_met():
    df = _make_df(n_rows=100_000, loanstatus=["pif"] * 60_000 + ["chgoff"] * 40_000)
    result = check_usable_rows(df)
    assert result["status"] == "pass"


def test_check_usable_rows_fails_when_below_absolute_threshold():
    df = _make_df(n_rows=1000, loanstatus=["pif"] * 500 + ["chgoff"] * 500)
    result = check_usable_rows(df)
    assert result["status"] == "fail"


def test_check_usable_rows_fails_when_below_percent_threshold():
    df = _make_df(n_rows=100_000, loanstatus=["pif"] * 1000 + ["chgoff"] * 1000 + ["curr"] * 98_000)
    result = check_usable_rows(df)
    assert result["status"] == "fail"


def test_check_program_values_passes_when_threshold_met():
    df = _make_df(n_rows=100, program=["7a"] * 95 + ["other"] * 5)
    result = check_program_values(df)
    assert result["status"] == "pass"

def test_check_program_value_fails_when_below_threshold():
    df = _make_df(n_rows=100, program=["7a"] * 50 + ["other"] * 50)
    result = check_program_values(df)
    assert result["status"] == "fail"

def test_check_missing_rate_returns_zero_for_complete_data():
    df = _make_df()
    result = check_missing_rates(df)
    assert result["borrname"]["null_count"] == 0
    assert result["borrname"]["null_pct"] == 0.0


def test_check_missing_rates_counts_nulls_correctly():
    df = _make_df(n_rows=4, borrname=["Nikhil", None, "Adhikari", None])
    result = check_missing_rates(df)
    assert result["borrname"]["null_count"] == 2
    assert result["borrname"]["null_pct"] == 0.5

def test_check_unknown_values_returns_empty_lists_for_valid_data():
    df = _make_df(loanstatus=["pif"], businesstype=["individual"])
    result = check_unknown_values(df)
    assert result["loanstatus"] == []
    assert result["businesstype"] == []

def test_check_unknown_values_flags_invalid_loanstatus():
    df = _make_df(n_rows=2, loanstatus=["pif", "garbage"])
    result = check_unknown_values(df)
    assert result["loanstatus"] == ["garbage"]


def test_check_required_columns_returns_wmpty_when_all_populated():
    df = _make_df()
    result = check_required_columns(df)
    assert result == {}

def test_check_required_columns_flags_columns_with_nulls():
    df = _make_df(n_rows=3, loanstatus=["pif", None, "chgoff"])
    result = check_required_columns(df)
    assert "loanstatus" in result
    assert result["loanstatus"] == 1


