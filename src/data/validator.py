
import pandas as pd
from schema import EXPECTED_COLUMNS


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
    


    



    
        



