from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.message import ChatMessage, MessageThread
from app.models.user import User
from app.schemas.message import (
    ChatMessageCreate,
    ChatMessageResponse,
    MessageThreadCreate,
    MessageThreadResponse,
    MessageThreadUpdate,
)

router = APIRouter()


def get_owned_thread(db: Session, thread_id: int, user_id: int) -> MessageThread:
    thread = (
        db.query(MessageThread)
        .filter(MessageThread.id == thread_id, MessageThread.user_id == user_id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message thread not found")
    return thread


@router.get("/threads", response_model=List[MessageThreadResponse])
def list_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageThread]:
    return (
        db.query(MessageThread)
        .filter(MessageThread.user_id == current_user.id)
        .order_by(MessageThread.updated_at.desc())
        .all()
    )


@router.post(
    "/threads",
    response_model=MessageThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_thread(
    payload: MessageThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageThread:
    initial_message = payload.initial_message or ""
    thread = MessageThread(
        user_id=current_user.id,
        counterpart_name=payload.counterpart_name,
        store_name=payload.store_name,
        store_address=payload.store_address,
        store_image_url=payload.store_image_url,
        tag=payload.tag,
        last_message=initial_message,
    )
    db.add(thread)
    db.flush()

    if initial_message:
        db.add(
            ChatMessage(
                thread_id=thread.id,
                sender="me",
                text=initial_message,
            )
        )

    db.commit()
    db.refresh(thread)
    return thread


@router.get("/threads/{thread_id}", response_model=MessageThreadResponse)
def get_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageThread:
    thread = get_owned_thread(db, thread_id, current_user.id)
    thread.unread_count = 0
    db.commit()
    db.refresh(thread)
    return thread


@router.patch("/threads/{thread_id}", response_model=MessageThreadResponse)
def update_thread(
    thread_id: int,
    payload: MessageThreadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageThread:
    thread = get_owned_thread(db, thread_id, current_user.id)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(thread, field, value)

    db.commit()
    db.refresh(thread)
    return thread


@router.post(
    "/threads/{thread_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    thread_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessage:
    thread = get_owned_thread(db, thread_id, current_user.id)
    if thread.blocked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thread is blocked")

    message = ChatMessage(
        thread_id=thread.id,
        sender="me",
        text=payload.text,
        kind=payload.kind,
    )
    thread.last_message = payload.text
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
