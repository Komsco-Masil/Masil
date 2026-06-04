from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_giftcard_client
from app.models.user import User
from app.models.store import Store, StoreUser
from app.schemas.store import StoreVerifyRequest, StoreResponse
from app.services.giftcard_client import LocalGiftCardClient, GiftCardAPIException

router = APIRouter()


@router.post("/verify", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def verify_and_register_store(
    payload: StoreVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    giftcard_client: LocalGiftCardClient = Depends(get_giftcard_client)
) -> Store:
    """
    가맹점 인증 및 권한 부여 API (MEM-02, MEM-03)
    
    - 이미 등록된 사업자등록번호인 경우: 409 Conflict
    - 외부 API 대조 성공 시: 사장 권한(OWNER) 부여 및 StoreUser 매핑 저장
    - 외부 API 불일치 시: 400 Bad Request
    - 외부 API 타임아웃/오류 발생 시: 500 에러를 내지 않고 is_manual_review=True로 강제 저장하며 권한 부여
    """
    # 이미 다른 유저가 등록한 사업자등록번호인지 조회 (MEM-03 예외 처리)
    existing_store = db.query(Store).filter(
        Store.business_number == payload.business_number
    ).first()
    if existing_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store already registered"
        )

    is_manual_review = False

    try:
        # 외부 조폐공사 API 연동
        verification_success = await giftcard_client.verify_store(
            business_number=payload.business_number,
            name=payload.name,
            address=payload.address
        )
        if not verification_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store details do not match"
            )
            
    except GiftCardAPIException:
        # 외부 API 타임아웃/오류 발생 시, 500 에러 대신 수동 검토 대기 플래그로 대체 (MEM-03 예외 처리)
        is_manual_review = True

    # 가맹점 정보 저장
    new_store = Store(
        business_number=payload.business_number,
        name=payload.name,
        address=payload.address,
        is_manual_review=is_manual_review
    )
    db.add(new_store)
    db.flush()  # ID 생성을 위한 flush

    # 유저 역할 OWNER로 업데이트
    current_user.role = "OWNER"

    # 유저-가게 관계 매핑 테이블 기록
    store_user = StoreUser(
        store_id=new_store.id,
        user_id=current_user.id,
        role="OWNER"
    )
    db.add(store_user)

    db.commit()
    db.refresh(new_store)
    return new_store
