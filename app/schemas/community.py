import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CommunityPostCreate(BaseModel):
    board: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1)
    ps: str = ""
    anonymous: bool = False
    location: str = Field(..., min_length=1, max_length=120)
    badge: Optional[str] = None
    avatar: str = "mono"
    promo_category: Optional[str] = None
    gift_certificate: bool = False
    meeting_at: Optional[str] = None
    meeting_place: Optional[str] = None
    meeting_max_people: Optional[int] = None
    meeting_applicants: Optional[int] = None
    meeting_status: Optional[str] = None


class CommunityPostResponse(CommunityPostCreate):
    id: int
    author_name: str
    likes: int
    views: int
    comments_count: int
    reports: int
    blinded: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CommunityCommentCreate(BaseModel):
    body: str = Field(..., min_length=1)
    parent_id: Optional[int] = None


class CommunityCommentResponse(BaseModel):
    id: int
    post_id: int
    parent_id: Optional[int]
    board_label: str
    author_name: str
    body: str
    likes: int
    created_at: datetime.datetime
    replies: List["CommunityCommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class CommunityActivityItem(BaseModel):
    id: int
    title: str
    body: str
    meta: str
    post_id: Optional[int] = None


class CommunityActivityStats(BaseModel):
    posts: int
    comments: int
    received_likes: int


class CommunityActivityResponse(BaseModel):
    stats: CommunityActivityStats
    posts: List[CommunityActivityItem]
    comments: List[CommunityActivityItem]
