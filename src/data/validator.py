
import pandas as pd
from src.data.schema import EXPECTED_COLUMNS, VALID_VALUES, REQUIRED_COLUMNS


def check_columns(df: pd.DataFrame) -> dict:
    """
    Check that DataFrame columns match the expected schema

    Args:
        df (pd.DataFrame): The dataset to validate

    Returns:
        dict: With 'status' ('pass' or 'fail'). On failure, includes 
              'details' with 'missing' and 'extra' sets.
    """

    expected_columns = set(EXPECTED_COLUMNS)
    dataset_columns = set(col.strip().lower() for col in df.columns)

    missing_columns = expected_columns - dataset_columns
    extra_columns = dataset_columns - expected_columns

    if missing_columns or extra_columns:
        return {
            "status": "fail",
            "details": {
                "missing": missing_columns,
                "extra": extra_columns,
            }
        }
    
    return {
        "status": "pass",
        
        
    }


def check_usable_rows(df: pd.DataFrame)-> dict:
    """
    Check that the number of pif and chgoff loan_status_values are above the threshold.

    args:
        df (pd.DataFrame): The dataframe of the dataset 

    Returns:
        dict with status ('pass' or 'fail'). On both cases, includes 
            'total row count' 'number of rows with "pif" and "chgoff" loan_status'
    
    
    """

    ABSOLUTE_THRESHOLD = 50_000
    PERCENT_THRESHOLD = 0.12

    total_rows = len(df)

    

    usable_rows = df["loanstatus"].isin(["pif", "chgoff"]).sum()
    usable_pct = usable_rows / total_rows

    if usable_pct < PERCENT_THRESHOLD or usable_rows < ABSOLUTE_THRESHOLD:
        return {
            "status": "fail",
            "details": {
                "total_rows": total_rows,
                "usable_rows": usable_rows,
                "usable_pct": round(usable_pct, 4),

            }
            

        }

    return {
        "status": "pass",
        "details": {
            "total_rows": total_rows,
            "usable_rows": usable_rows,
            "usable_pct": round(usable_pct, 4),
        }
        
    }



def check_program_values(df: pd.DataFrame)-> dict:
    """
    Checks is the dataframe has the minimum threshold for 7(A) rows

    args:
        df (pd.DataFrame): The datframe of the dataset

    returns:
        dict with status ('pass' or 'fail'). On both cases includes
        total 7A row counts and percentage of 7A rows 
    
    """
    PERCENT_THRESHOLD = 0.92

    total_rows = len(df)

    program_rows = (df["program"] == "7a").sum()
    program_pct = program_rows / total_rows

    if program_pct < PERCENT_THRESHOLD:
        return {
            "status": "fail",
            "details": {
                "7a_rows": program_rows,
                "7a_pct": round(program_pct, 4),
            }
        }
    return {
        "status": "pass",
        "details": {
            "7a_rows": program_rows,
            "7a_pct": round(program_pct, 4),
        }
    }
    


# --------------------------------------------------------------------------------------------
# Non-fatal checks
# -----------------------------------------------------------------------------------------------------



def check_missing_rates(df: pd.DataFrame) -> dict:
    return {
        col: {
            "null_count": int(df[col].isna().sum()),
            "null_pct": float(df[col].isna().mean()),
        }
        for col in df.columns
    }


def check_unknown_values(df: pd.DataFrame) -> dict:
    return {
        col : sorted(set(df[col].dropna().unique()) - set(valid))
        for col, valid in VALID_VALUES.items()
    }


def check_required_columns(df: pd.DataFrame) -> dict:
    return {
        col: int(df[col].isna().sum())
        for col in REQUIRED_COLUMNS
        if df[col].isna().any()
    }







    



    
        



