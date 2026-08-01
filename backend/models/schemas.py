from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DocumentResponse(BaseModel):
    id: int
    filename: str
    s3_url: str
    upload_time: str

    class Config:
        from_attributes = True

class AskRequest(BaseModel):
    question: str

class SourceCitation(BaseModel):
    filename: str
    page: int

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]

class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: str
    sources: List[SourceCitation]

    class Config:
        from_attributes = True
