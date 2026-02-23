import pandas as pd
from langchain_community.docstore.document import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from typing import List
from dotenv import find_dotenv, load_dotenv
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

@dataclass
class CoreClassException(Exception):
    message: str
    timestamp: datetime
    
    def __post_init__(self):
        super().__init__(self.message)
        
    def __log__format(self):
        return f"Error occured at {self.timestamp.isoformat()} \n {self.message}"
    
    def __to_json__(self):
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dump(data)

def create_document_from_spreadsheet(file):
    if not os.path.exists(file):
        raise CoreClassException(
            "Path to file does not exist",
            datetime.now()
        )
    try:
        file_loader = UnstructuredExcelLoader(file, mode="elements")
        document = file_loader.load()
        return document
    except Exception as e:
        raise CoreClassException(
            f"Error loading excel file: {str(e)}",
            datetime.now()
        )

def create_vectorstore(documents: List[Document]):
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)
        return vectorstore
    except Exception as e:
        raise CoreClassException(
            f"Error creating vectorstore: {str(e)}",
            datetime.now()
        )
    
    
    
    
                
    
    