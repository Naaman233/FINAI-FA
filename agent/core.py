import os
from logging import getLogger
from dotenv import load_dotenv, find_dotenv
import pandas as pd
from dataclasses import dataclass
from typing import Union, Dict, Any
load_dotenv(find_dotenv())
logger = getLogger("CFO-PIPELINE")

@dataclass
class Message:
    role: str
    content: str
    
@dataclass
class UserInfo:
    user_id: str
    preferences: Union[Dict[str, Any], str]
def read_text_file(file_path: str):
    """Reads the content of a text file and returns it as a string.

    Args:
        file_path (str): The path to the text file.
    """
    logger.info(f"Attempting to read file from {file_path}")
    
    if os.path.isabs(file_path):
        absolute_file_path= os.path.normpath(file_path)
    else:
        script_dir= os.path.dirname(os.path.abspath(__file__))
        absolute_file_path= os.path.normpath(os.path.join(script_dir,file_path))
    
    if not os.path.exists(absolute_file_path):
        logger.error(f"File not found: {absolute_file_path}")
        raise FileNotFoundError(f"The file at {absolute_file_path} does not exist")
    try:
        with open(absolute_file_path, 'r', encoding="utf-8") as file:
            content = file.read()
            logger.info(f"Successfully read file contents at {absolute_file_path}")
            return content
    except Exception as exception:
        logger.error(f"Error reading file at {absolute_file_path}: {exception}")
        raise FileNotFoundError(f"{exception}") 
    
def load_financial_data():
    """_summary_
    Loads financial dataset into the LLM 
    Args: None
    Returns: Dict of sheet_name and Dataframe pairing
    """
    try:
        file_path= os.getenv("FINANCIAL_DATASET_PATH")
        financial_dataset= pd.ExcelFile(file_path)
        sheets = {}
        for sheet_name in financial_dataset.sheet_names:
            df = pd.read_excel(financial_dataset, sheet_name= sheet_name)
            sheets[sheet_name.lower()] = df
        
        required = {"actuals","budget","cash","fx"}
        missing = required - set(sheets.keys())
        if missing:
            raise KeyError(f"Missing sheets: {missing}")
        logger.info(f"Loaded sheets: {list(sheets.keys())}")
        return sheets
    except Exception as exception:
        logger.error(f"Loading financial dataset failed: \n {exception}")
        raise
    
    
    
    
    