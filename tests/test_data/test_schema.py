

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


def test_no_column_appears_in_multiple_views():
    all_views = [STRING_COLUMNS, INTEGER_COLUMNS, FLOAT_COLUMNS, DATE_COLUMNS]
    seen = set()
    for view in all_views:
        for col in view:
            assert col not in seen, f"{col} appears in multiple views"
            seen.add(col)


def test_every_column_appears_in_some_views():
    all_view_columns = set(STRING_COLUMNS) | set(INTEGER_COLUMNS) | set(FLOAT_COLUMNS) | set(DATE_COLUMNS)
    assert all_view_columns == set(COLUMN_TYPES.keys())
    
