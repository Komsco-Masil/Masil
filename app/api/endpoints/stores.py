from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_giftcard_client, get_nts_client
from app.models.user import User
from app.models.store import Store, StoreUser
from app.schemas.store import StoreVerifyRequest, StoreResponse
from app.services.giftcard_client import LocalGiftCardClient, GiftCardAPIException
from app.services.nts_client import NTSBusinessClient, NTSAPIException

router = APIRouter()


@router.post("/verify", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def verify_and_register_store(
    payload: StoreVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    nts_client: NTSBusinessClient = Depends(get_nts_client)
) -> Store:
    """
    가맹점 인증 및 권한 부여 API (MEM-02, MEM-03)
    
    - 이미 등록된 사업자등록번호인 경우: 409 Conflict
    - 국세청 API 대조 성공 시: 사장 권한(OWNER) 부여 및 StoreUser 매핑 저장
    - 국세청 API 불일치 시: 400 Bad Request
    - 국세청 API 타임아웃/오류 발생 시: 500 에러를 내지 않고 is_manual_review=True로 강제 저장하며 권한 부여 및 안내 메시지 반환
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
    custom_message = None

    try:
        # 국세청 API 연동
        result = await nts_client.verify_business(
            business_number=payload.business_number,
            start_date=payload.start_date,
            representative_name=payload.representative_name,
            name=payload.name
        )
        valid = result.get("valid")
        valid_msg = result.get("valid_msg", "")
        
        if valid != "01":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"사업자 정보 불일치: {valid_msg}"
            )
            
    except NTSAPIException:
        # 외부 API 타임아웃/오류 발생 시, 500 에러 대신 수동 검토 대기 플래그로 대체
        is_manual_review = True
        custom_message = "인증 서버 지연으로 인해 관리자 수동 검토로 전환되었습니다."

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
    
    if custom_message:
        new_store.message = custom_message
        
    return new_store
