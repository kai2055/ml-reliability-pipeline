from pathlib import Path
import pandas as pd



def load_dataset(path: Path)-> pd.DataFrame:
    """ Function takes the initial dataset and loads it
    
        Args:
            path (Path): The path to the dataset

        Returns:
            pd.DataFrame: Dataframe of the dataset
        
        Raises:
            FileNotFoundError: The file path does not exist
            IsADirectoryError: Path leads to a directory rather than file
            ValueError: Path leads to file types other than csv files
    
    """
    if not path.exists():
        raise FileNotFoundError(f"The specified path does not exist: {path}")
    
    if path.is_dir():
        raise IsADirectoryError(f"The given path leads to a directory; not a file: {path}")
    
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected .csv file, got: {path.suffix}")
    
    df = pd.read_csv(path,header = 0)

    return df
 
