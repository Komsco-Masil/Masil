from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.community import CommunityComment, CommunityPost
from app.models.user import User
from app.schemas.community import (
    CommunityActivityItem,
    CommunityActivityResponse,
    CommunityActivityStats,
    CommunityCommentCreate,
    CommunityCommentResponse,
    CommunityPostCreate,
    CommunityPostResponse,
)

router = APIRouter()


def serialize_post(post: CommunityPost) -> CommunityPostResponse:
    return CommunityPostResponse(
        id=post.id,
        board=post.board,
        title=post.title,
        body=post.body,
        ps=post.ps,
        anonymous=post.anonymous,
        location=post.location,
        badge=post.badge,
        avatar=post.avatar,
        promo_category=post.promo_category,
        gift_certificate=post.gift_certificate,
        meeting_at=post.meeting_at,
        meeting_place=post.meeting_place,
        meeting_max_people=post.meeting_max_people,
        meeting_applicants=post.meeting_applicants,
        meeting_status=post.meeting_status,
        author_name=post.author_name,
        likes=post.likes,
        views=post.views,
        comments_count=len(post.comments),
        reports=post.reports,
        blinded=post.blinded,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def serialize_comment(comment: CommunityComment) -> CommunityCommentResponse:
    return CommunityCommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        board_label=comment.board_label,
        author_name=comment.author_name,
        body=comment.body,
        likes=comment.likes,
        created_at=comment.created_at,
        replies=[serialize_comment(reply) for reply in comment.replies],
    )


def ensure_board_access(board: str, user: User) -> None:
    if board == "owner" and user.role not in ("OWNER", "EMPLOYEE"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다. 가맹점 인증 후 이용할 수 있어요.",
        )


def board_label(board: str) -> str:
    return {
        "hot": "핫게",
        "local": "동네 게시판",
        "promo": "가게 홍보게시판",
        "owner": "소상공인 익명 게시판",
        "meet": "유저모임 게시판",
    }.get(board, "커뮤니티")


@router.get("/me/activity", response_model=CommunityActivityResponse)
def my_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityActivityResponse:
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.user_id == current_user.id)
        .order_by(CommunityPost.created_at.desc())
        .all()
    )
    comments = (
        db.query(CommunityComment)
        .filter(CommunityComment.user_id == current_user.id)
        .order_by(CommunityComment.created_at.desc())
        .all()
    )

    return CommunityActivityResponse(
        stats=CommunityActivityStats(
            posts=len(posts),
            comments=len(comments),
            received_likes=sum(post.likes for post in posts),
        ),
        posts=[
            CommunityActivityItem(
                id=post.id,
                post_id=post.id,
                title=post.title,
                body=post.body,
                meta=f"{board_label(post.board)} · 댓글 {len(post.comments)} · 좋아요 {post.likes}",
            )
            for post in posts
        ],
        comments=[
            CommunityActivityItem(
                id=comment.id,
                post_id=comment.post_id,
                title=comment.post.title if comment.post else "삭제된 글",
                body=comment.body,
                meta=f"{comment.board_label} · 좋아요 {comment.likes}",
            )
            for comment in comments
        ],
    )


@router.get("/posts", response_model=List[CommunityPostResponse])
def list_posts(board: Optional[str] = None, db: Session = Depends(get_db)) -> List[CommunityPostResponse]:
    query = db.query(CommunityPost)
    if board and board != "hot":
        query = query.filter(CommunityPost.board == board)

    posts = query.order_by(CommunityPost.created_at.desc()).all()
    return [serialize_post(post) for post in posts]


@router.post(
    "/posts",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    payload: CommunityPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPostResponse:
    ensure_board_access(payload.board, current_user)

    author_name = "익명 사장님" if payload.board == "owner" else (
        "익명" if payload.anonymous else current_user.nickname
    )
    post = CommunityPost(
        user_id=current_user.id,
        board=payload.board,
        title=payload.title,
        body=payload.body,
        ps=payload.ps,
        anonymous=payload.anonymous or payload.board == "owner",
        author_name=author_name,
        location=payload.location,
        badge=payload.badge,
        avatar=payload.avatar,
        promo_category=payload.promo_category,
        gift_certificate=payload.gift_certificate,
        meeting_at=payload.meeting_at,
        meeting_place=payload.meeting_place,
        meeting_max_people=payload.meeting_max_people,
        meeting_applicants=payload.meeting_applicants,
        meeting_status=payload.meeting_status,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.get("/posts/{post_id}", response_model=CommunityPostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)) -> CommunityPostResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.views += 1
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.user_id != current_user.id and current_user.role not in ("OWNER", "EMPLOYEE"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    db.delete(post)
    db.commit()
    return {"detail": "Post successfully deleted"}


@router.get("/posts/{post_id}/comments", response_model=List[CommunityCommentResponse])
def list_comments(post_id: int, db: Session = Depends(get_db)) -> List[CommunityCommentResponse]:
    comments = (
        db.query(CommunityComment)
        .filter(CommunityComment.post_id == post_id, CommunityComment.parent_id.is_(None))
        .order_by(CommunityComment.created_at.desc())
        .all()
    )
    return [serialize_comment(comment) for comment in comments]


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommunityCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    payload: CommunityCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityCommentResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if payload.parent_id:
        parent = (
            db.query(CommunityComment)
            .filter(CommunityComment.id == payload.parent_id, CommunityComment.post_id == post_id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")

    board_label = {
        "owner": "소상공인",
        "local": "동네",
        "meet": "유저모임",
        "promo": "음식점",
    }.get(post.board, "동네")
    author_name = "익명" if post.board == "owner" else current_user.nickname
    comment = CommunityComment(
        post_id=post.id,
        user_id=current_user.id,
        parent_id=payload.parent_id,
        board_label=board_label,
        author_name=author_name,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return serialize_comment(comment)


@router.post("/posts/{post_id}/like", response_model=CommunityPostResponse)
def like_post(post_id: int, db: Session = Depends(get_db)) -> CommunityPostResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.likes += 1
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.delete("/posts/{post_id}/like", response_model=CommunityPostResponse)
def unlike_post(post_id: int, db: Session = Depends(get_db)) -> CommunityPostResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.likes = max(0, post.likes - 1)
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.post("/posts/{post_id}/report", response_model=CommunityPostResponse)
def report_post(post_id: int, db: Session = Depends(get_db)) -> CommunityPostResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.reports = min(5, post.reports + 1)
    post.blinded = post.reports >= 5
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.post("/posts/{post_id}/meeting/apply", response_model=CommunityPostResponse)
def apply_meeting(post_id: int, db: Session = Depends(get_db)) -> CommunityPostResponse:
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.board != "meet":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting post only")

    post.meeting_applicants = (post.meeting_applicants or 0) + 1
    if post.meeting_max_people and post.meeting_applicants >= post.meeting_max_people:
        post.meeting_status = "모집 마감"
    db.commit()
    db.refresh(post)
    return serialize_post(post)
