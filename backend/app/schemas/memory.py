from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "fact"


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None


class MemoryOut(BaseModel):
    id: str
    content: str
    memory_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
