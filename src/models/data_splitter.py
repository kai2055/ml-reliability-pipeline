
import pandas as pd
from sklearn.model_selection import train_test_split

def split_train_val_test(
        X: pd.DataFrame,
        y: pd.Series,
        val_size: float = 0.15,
        test_size: float = 0.15,
        random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Split data into training, validation, and test sets.

    Splits are stratified on *y* so that class proportions are
    maintained in each subset. The test set is extracted first,
    then the remainder is divided into training and validation.

    Args:
        X: Feature DataFrame
        y: Target series
        val_size: Fraction of data for validation (default 0.15)
        test_size: Fraction of data for test (default 0.15)
        random_state: Seed for reproducibility

    Returns:
        A 6-tuple (X_train, X_val, X_test, y_train, y_val, y_test)

    
    
    """

    # Pull test set first
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )


    # Split remainder into train and validation
    val_frac = val_size / (1.0 - test_size)

    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=val_frac,
        stratify=y_temp,
        random_state=random_state,
    )

    return X_train, X_val, X_test, y_train, y_val, y_test


