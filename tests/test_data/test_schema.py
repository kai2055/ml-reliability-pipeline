

from src.data.schema import(
    COLUMN_TYPES,
    STRING_COLUMNS,
    INTEGER_COLUMNS,
    FLOAT_COLUMNS,
    DATE_COLUMNS,
)


def test_view_counts_sum_to_column_types():
    total = len(STRING_COLUMNS) + len(INTEGER_COLUMNS) + len(FLOAT_COLUMNS) + len(DATE_COLUMNS)
    assert total == len(COLUMN_TYPES)

    
