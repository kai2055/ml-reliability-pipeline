import pandas as pd
from src.data.schema import STRING_COLUMNS, INTEGER_COLUMNS, FLOAT_COLUMNS, DATE_COLUMNS






def _make_df(n_rows=1, **overrides):
    base = {col: ["x"] * n_rows for col in STRING_COLUMNS}
    base.update({col: [0] * n_rows for col in INTEGER_COLUMNS})
    base.update({col: [0.0] * n_rows for col in FLOAT_COLUMNS })
    base.update({col: ["1999-02-02"] * n_rows for col in DATE_COLUMNS} )
    base.update(overrides)

    return pd.DataFrame(base)