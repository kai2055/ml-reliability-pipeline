
import pytest
import pandas as pd
from src.data.loader import load_dataset


def test_load_dataset_raises_when_path_does_not_exist(tmp_path):
    bad_path = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileNotFoundError):
        load_dataset(bad_path)



def test_load_dataset_raises_when_path_is_directory(tmp_path):
    with pytest.raises(IsADirectoryError):
        load_dataset(tmp_path)




def test_load_dataset_raises_when_extension_is_not_csv(tmp_path):
    bad_file = tmp_path / "data.txt"
    bad_file.write_text("col1,col2\n1,2")
    with pytest.raises(ValueError):
        load_dataset(bad_file)



def test_load_dataset_returns_dataframe_for_valid_csv(tmp_path):
    valid_file = tmp_path / "data.csv"
    valid_file.write_text("col1, col2\n1,2\n3,4")
    result = load_dataset(valid_file)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    