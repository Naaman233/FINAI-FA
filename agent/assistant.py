from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate 
import os
from dotenv import find_dotenv, load_dotenv
from langchain import hub
from dataclasses import dataclass, asdict
from datetime import datetime
import json 

load_dotenv(find_dotenv())

@dataclass
class AssistantClassException(Exception):
    message: str
    timestamp: datetime
    
    def __post_init__(self):
        super().__init__(self.message)
        
    def __log__format(self):
        return f"Error occured at {self.timestamp.isoformat()} \n {self.message}"
    
    def __to_json__(self):
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)
    
    
def create_qa_chain(vectorstore, llm):
    template = os.getenv("SYSTEM_PROMPT")
    if not template:
        raise AssistantClassException(
            "System prompt could not be found or loaded",
            datetime.now()
        )
    
    try:
        prompt = PromptTemplate(
            template= template,
            input_variables= ["context","input"]
        )
        
        combine_chain_docs = create_stuff_documents_chain(
            llm= llm,
            prompt= prompt
        )
        qa_chain = create_retrieval_chain(
            combine_chain_docs,
            retriever= vectorstore.as_retriever(search_kwargs={"k":5})
           
        )
        return qa_chain
    except Exception as e:
        raise AssistantClassException(
            f"Error creating QA chain: {str(e)}",
            datetime.now()
        )   
    
    
