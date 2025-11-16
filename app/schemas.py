from pydantic import BaseModel
from typing import List, Optional, Literal



Role = Literal["system","user","assistant"]



class Message(BaseModel):

    role: Role

    content: str



class ChatRequest(BaseModel):

    session_id: Optional[str] = None

    message: str



class ChatResponse(BaseModel):

    answer: str

    session_id: str

    tokens_in: int | None = None

    tokens_out: int | None = None

