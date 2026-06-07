from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.store import StoreUser
from app.models.promotion import Promotion
from app.schemas.promotion import PromotionCreate, PromotionUpdate, PromotionResponse

router = APIRouter()

def check_store_staff(db: Session, store_id: int, user_id: int):
    """사용자가 해당 가게의 직원(OWNER/EMPLOYEE)인지 확인합니다."""
    staff_mapping = db.query(StoreUser).filter(
        StoreUser.store_id == store_id,
        StoreUser.user_id == user_id
    ).first()
    if not staff_mapping:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage promotions for this store"
        )
    return staff_mapping

@router.post("/", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
def create_promotion(
    payload: PromotionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Promotion:
    """홍보 게시글 생성 (해당 가맹점의 사장 또는 직원만 생성 가능)"""
    check_store_staff(db, payload.store_id, current_user.id)

    db_promotion = Promotion(
        store_id=payload.store_id,
        title=payload.title,
        content=payload.content
    )
    db.add(db_promotion)
    db.commit()
    db.refresh(db_promotion)
    return db_promotion

@router.get("/", response_model=List[PromotionResponse])
def read_promotions(
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> List[Promotion]:
    """홍보 게시글 목록 조회 (가맹점 ID별 필터 지원)"""
    query = db.query(Promotion)
    if store_id is not None:
        query = query.filter(Promotion.store_id == store_id)
    return query.order_by(Promotion.created_at.desc()).all()

@router.get("/{id}", response_model=PromotionResponse)
def read_promotion(
    id: int,
    db: Session = Depends(get_db)
) -> Promotion:
    """특정 홍보 게시글 상세 조회"""
    promotion = db.query(Promotion).filter(Promotion.id == id).first()
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    return promotion

@router.put("/{id}", response_model=PromotionResponse)
def update_promotion(
    id: int,
    payload: PromotionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Promotion:
    """홍보 게시글 수정 (해당 가맹점의 사장 또는 직원만 수정 가능)"""
    promotion = db.query(Promotion).filter(Promotion.id == id).first()
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )

    # 해당 게시글이 속한 가맹점의 권한이 있는지 체크
    check_store_staff(db, promotion.store_id, current_user.id)

    # 전달받은 필드 업데이트
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promotion, field, value)

    db.commit()
    db.refresh(promotion)
    return promotion

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_promotion(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """홍보 게시글 삭제 (해당 가맹점의 사장 또는 직원만 삭제 가능)"""
    promotion = db.query(Promotion).filter(Promotion.id == id).first()
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )

    # 해당 게시글이 속한 가맹점의 권한이 있는지 체크
    check_store_staff(db, promotion.store_id, current_user.id)

    db.delete(promotion)
    db.commit()
    return {"detail": "Promotion successfully deleted"}
