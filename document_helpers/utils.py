import pandas as pd
from dotenv import load_dotenv, find_dotenv
import os
import time
from dataclasses import dataclass

load_dotenv(find_dotenv())

@dataclass
class DocumentLoaderException(Exception):
    timestamp: float
    message: str
    
    def __str__(self):
        return f"[{self.timestamp}] DocumentLoaderException: {self.message}"
    
def load_data(path: str):
    data_path = path or os.environ.get("FINANCIAL_DATASET_PATH")
    if not data_path:
        raise ValueError("No data source path provided")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"{data_path} does not exist")
    
    try:
        return {
            "actuals": pd.read_excel(data_path, sheet_name="actuals"),
            "buddet": pd.read_excel(data_path, sheet_name="budget"),
            "cash" : pd.read_excel(data_path, sheet_name="cash"),
            "fx": pd.read_excel(data_path, sheet_name="fx")
        }
    except Exception as exception:
        raise DocumentLoaderException(
            timestamp=time.time(),
            message=str(exception)
        )
        

    
    
        

    