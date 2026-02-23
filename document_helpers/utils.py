import pandas as pd
import os
from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import UnstructuredExcelLoader
from dataclasses import dataclass, asdict
from datetime import datetime
import json

load_dotenv(find_dotenv())

@dataclass
class UtilClassException(Exception):
    message: str
    timestamp: datetime
    
    
    def __post_init__(self):
        super().__init__(self.message)
    
    def __log__format(self):
        return f"Error occured at {self.timestamp.isoformat()}\n{self.message}"
    
    def __to_json__(self):
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dump(data)
        
    

def load_excel_sheet(file):
    if not os.path.exists(file):
        raise UtilClassException(
            "Path to file does not exist",
            datetime.now()
        )
        
    try:
        file_loader = UnstructuredExcelLoader(file, mode="elements")
        document = file_loader.load()
        return document
    except Exception as e:
        raise UtilClassException(
            f"Error loading excel file: {str(e)}",
            datetime.now()
        )
    
    
  
    
        
        
