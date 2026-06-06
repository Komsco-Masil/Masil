import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageThreadCreate(BaseModel):
    counterpart_name: str = Field(..., min_length=1, max_length=80)
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_image_url: Optional[str] = None
    tag: Optional[str] = None
    initial_message: Optional[str] = None


class MessageThreadUpdate(BaseModel):
    muted: Optional[bool] = None
    blocked: Optional[bool] = None
    unread_count: Optional[int] = None


class ChatMessageCreate(BaseModel):
    text: str = Field(..., min_length=1)
    kind: str = "text"


class ChatMessageResponse(BaseModel):
    id: int
    thread_id: int
    sender: str
    text: str
    kind: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class MessageThreadResponse(BaseModel):
    id: int
    counterpart_name: str
    store_name: Optional[str]
    store_address: Optional[str]
    store_image_url: Optional[str]
    tag: Optional[str]
    last_message: str
    unread_count: int
    muted: bool
    blocked: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
