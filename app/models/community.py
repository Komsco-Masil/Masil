import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    board = Column(String(20), index=True, nullable=False)
    title = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    ps = Column(Text, default="", nullable=False)
    anonymous = Column(Boolean, default=False, nullable=False)
    author_name = Column(String(80), nullable=False)
    location = Column(String(120), nullable=False)
    badge = Column(String(80), nullable=True)
    avatar = Column(String(20), default="mono", nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    views = Column(Integer, default=0, nullable=False)
    promo_category = Column(String(30), nullable=True)
    gift_certificate = Column(Boolean, default=False, nullable=False)
    meeting_at = Column(String(80), nullable=True)
    meeting_place = Column(String(120), nullable=True)
    meeting_max_people = Column(Integer, nullable=True)
    meeting_applicants = Column(Integer, nullable=True)
    meeting_status = Column(String(30), nullable=True)
    reports = Column(Integer, default=0, nullable=False)
    blinded = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    comments = relationship(
        "CommunityComment",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(Integer, ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=True)
    board_label = Column(String(30), nullable=False)
    author_name = Column(String(80), nullable=False)
    body = Column(Text, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    post = relationship("CommunityPost", back_populates="comments")
    replies = relationship("CommunityComment", cascade="all, delete-orphan")
