from pydantic import BaseModel,Field
class ChatRequest(BaseModel):
    question:str = Field(...,
                         min_length=1,
                         max_length=4000,
                         )
class SourceResponse(BaseModel):
    document_id:int
    file_name:str
    file_path:str
    chunk_index:int

class ChatResponse(BaseModel): 
    answer:str
    sources:list[SourceResponse]  
