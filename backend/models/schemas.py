from pydantic import BaseModel
from typing import Optional, Dict, Any


class GenerateRequest(BaseModel):
    prompt: str
    width: Optional[int] = None
    height: Optional[int] = None
    brand: Optional[str] = None


class RecompileRequest(BaseModel):
    generation_id: str
    html: str
    format: Optional[str] = "png"


class GenerateResponse(BaseModel):
    generation_id: str
    analysis: Dict[str, Any]
    creative: Dict[str, Any]
    html: str
    preview_url: str
