
import pytest
import pandas as pd

from src.models.dataset_builder import (
    build_dataset,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
)



@pytest.fixture
def sample_df():
    """Create a sample DataFrame with realistic SBA loan data.
    
    Contains 7 rows with mixed loanstatus values:
    - 3 pif (paid in full - good outcome)
    - 2 chgoff (charged off - default)
    - 1 curr (current - should be filtered out)
    - 1 delinq (delinquent - should be filtered out)
    """
    data = {
        "loanstatus": ["pif", "chgoff", "pif", "curr", "chgoff", "pif", "delinq"],
        "grossapproval": [100000, 50000, 75000, 25000, 120000, 90000, 60000],
        "sbaguaranteedapproval": [75000, 37500, 56250, 18750, 90000, 67500, 45000],
        "initialinterestrate": [5.5, 6.0, 4.5, 7.0, 5.0, 4.75, 6.5],
        "terminmonths": [120, 84, 60, 36, 180, 120, 48],
        "jobssupported": [10, 5, 8, 2, 15, 12, 3],
        "subprogram": ["7a", "504", "7a", "7a", "504", "7a", "504"],
        "processingmethod": ["PLP", "CLP", "PLP", "PLP", "CLP", "PLP", "CLP"],
        "fixedorvariableinterestind": ["FIXED", "VAR", "FIXED", "VAR", "FIXED", "VAR", "FIXED"],
        "revolverstatus": ["1", "0", "1", "0", "1", "1", "0"],
        "businesstype": ["Corp", "LLC", "Corp", "Sole", "LLC", "Corp", "LLC"],
        "businessage": ["New", "Existing", "Existing", "New", "Existing", "New", "Existing"],
        "collateralind": ["Y", "N", "Y", "N", "Y", "Y", "N"],
        "extra_column": ["a", "b", "c", "d", "e", "f", "g"],  # Should be dropped
    }
    return pd.DataFrame(data)





def test_filters_to_resolved_outcomes_only(sample_df):
    X , y = build_dataset(sample_df)

    assert len(X) == 5
    assert len(y) == 5

    for idx in X.index:
        assert sample_df.loc[idx, "loanstatus"] in {"pif", "chgoff"}

    for idx in sample_df.index:
        if sample_df.loc[idx, "loanstatus"] not in {"pif", "chgoff"}:
            assert idx not in X.index
            assert idx not in y.index




def test_X_has_exactly_12_v1_feature_columns(sample_df):

    X, _ = build_dataset(sample_df)

    expected = set(NUMERICAL_FEATURES + CATEGORICAL_FEATURES)
    actual = set(X.columns)

    assert actual == expected
    assert len(actual) == 12




def test_y_maps_pif_to_0_chgoff_to_1_as_int8(sample_df):

    _, y = build_dataset(sample_df)

    assert y.dtype == "int8"

    for idx in y.index:
        status = sample_df.loc[idx, "loanstatus"]
        if status == "pif":
            assert y[idx] == 0
        elif status == "chgoff":
            assert y[idx] == 1


    

def test_loanstatus_not_in_X(sample_df):
    
    X, _ = build_dataset(sample_df)
    assert "loanstatus" not in X.columns




def test_X_and_y_have_same_row_count(sample_df):

    X, y = build_dataset(sample_df)

    assert len(X) == len(y)




def test_numerical_and_categorical_are_disjoint_and_cover_X(sample_df):

    X, y = build_dataset(sample_df)

    numerical = set(NUMERICAL_FEATURES)
    categorical = set(CATEGORICAL_FEATURES)

    assert numerical & categorical == set()

    assert numerical | categorical == set(X.columns)



def test_raises_error_on_missing_required_column(sample_df):

    df_missing = sample_df.drop(columns=["grossapproval"])

    with pytest.raises(KeyError):
        build_dataset(df_missing)


