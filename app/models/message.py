import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class MessageThread(Base):
    __tablename__ = "message_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    counterpart_name = Column(String(80), nullable=False)
    store_name = Column(String(120), nullable=True)
    store_address = Column(String(160), nullable=True)
    store_image_url = Column(Text, nullable=True)
    tag = Column(String(30), nullable=True)
    last_message = Column(Text, default="", nullable=False)
    unread_count = Column(Integer, default=0, nullable=False)
    muted = Column(Boolean, default=False, nullable=False)
    blocked = Column(Boolean, default=False, nullable=False)
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

    messages = relationship(
        "ChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    kind = Column(String(20), default="text", nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    thread = relationship("MessageThread", back_populates="messages")
