from pydantic import BaseModel, Field
from typing import Optional


class GenerateRequest(BaseModel):
    prompt: str
    width: Optional[int] = Field(None, ge=400, le=2400)
    height: Optional[int] = Field(None, ge=400, le=2400)
    brand: Optional[str] = None


class RecompileRequest(BaseModel):
    generation_id: str
    html: str
