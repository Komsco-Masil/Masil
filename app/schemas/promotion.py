import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class PromotionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class PromotionCreate(PromotionBase):
    store_id: int

class PromotionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)

class PromotionResponse(PromotionBase):
    id: int
    store_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
