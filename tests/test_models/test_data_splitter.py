
from src.models.data_splitter import split_train_val_test



def test_split_sizes_with_explicit_proportions(tiny_xy):
    X, y = tiny_xy

    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        X, y, val_size=0.2, test_size=0.2, random_state=42
    )

    assert len(X_train) == 30
    assert len(X_val) == 10
    assert len(X_test) == 10

    assert len(y_train) == 30
    assert len(y_val) == 10
    assert len(y_test) == 10

    assert len(X_train) + len(X_val) + len(X_test) == 50


def test_split_preserves_stratification(tiny_xy):
    X, y = tiny_xy
    orig_ratio = y.mean()

    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        X, y, val_size=0.2, test_size=0.2, random_state=42
    )

    # With small splits (10 rows), allowed deviation is +-0.15
    assert abs(y_train.mean() - orig_ratio) < 0.15
    assert abs(y_val.mean() - orig_ratio) < 0.15
    assert abs(y_test.mean() - orig_ratio) < 0.15



def test_splits_are_disjoint_and_cover_all_rows(tiny_xy):
    X, y = tiny_xy
    X_train, X_val, X_test, *_ = split_train_val_test(\
        X, y, val_size=0.2, test_size=0.2, random_state=42
        )
    
    train_idx = set(X_train.index)
    val_idx = set(X_val.index)
    test_idx = set(X_test.index)

    assert train_idx.isdisjoint(val_idx)
    assert train_idx.isdisjoint(test_idx)
    assert val_idx.isdisjoint(test_idx)

    assert train_idx | val_idx | test_idx == set(X.index)


def test_split_reproducibility(tiny_xy):
    X, y = tiny_xy
    kwargs = dict(val_size=0.2, test_size=0.2, random_state=42)

    out1 = split_train_val_test(X, y, **kwargs)
    out2 = split_train_val_test(X, y, **kwargs)

    for a, b in zip(out1, out2):
        assert a.equals(b)
        
