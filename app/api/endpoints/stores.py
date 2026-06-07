from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime

from app.api.deps import get_db, get_current_user, get_giftcard_client, get_nts_client
from app.models.user import User
from app.models.store import Store, StoreUser
from app.schemas.store import StoreVerifyRequest, StoreResponse, PublicDataSummaryResponse
from app.services.giftcard_client import LocalGiftCardClient, GiftCardAPIException, GiftCardTimeoutException
from app.services.nts_client import NTSBusinessClient, NTSAPIException, NTSTimeoutException

router = APIRouter()


@router.post("/verify", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def verify_and_register_store(
    payload: StoreVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    giftcard_client: LocalGiftCardClient = Depends(get_giftcard_client),
    nts_client: NTSBusinessClient = Depends(get_nts_client)
) -> Store:
    """
    가맹점 인증 및 권한 부여 API (MEM-02, MEM-03)
    
    - 이미 등록된 사업자등록번호인 경우: 409 Conflict
    - 국세청 API 및 지역사랑상품권 가맹점 공공데이터 대조 성공 시: 사장 권한(OWNER) 부여 및 StoreUser 매핑 저장
    - 국세청 API 불일치 시: 400 Bad Request
    - 외부 공공데이터 API 타임아웃/오류 발생 시: 500 에러를 내지 않고 is_manual_review=True로 저장하며 권한 부여 및 안내 메시지 반환
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
    nts_verified = False
    gift_card_verified = False
    custom_message = None

    try:
        # 1. 국세청 사업자등록정보 진위확인 API 연동
        result = await nts_client.verify_business(
            business_number=payload.business_number,
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
        nts_verified = True

        # 2. 한국조폐공사 지역사랑상품권 가맹점 공공데이터 대조
        gift_card_verified = await giftcard_client.verify_store(
            business_number=payload.business_number,
            name=payload.name,
            address=payload.address or ""
        )
        if not gift_card_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지역사랑상품권 가맹점 공공데이터에서 일치하는 매장을 찾지 못했습니다."
            )

    except (NTSTimeoutException, GiftCardTimeoutException):
        # 외부 API 타임아웃/오류 발생 시, 500 에러 대신 수동 검토 대기 플래그로 대체
        is_manual_review = True
        custom_message = "공공데이터 인증 서버 지연으로 인해 관리자 수동 검토로 전환되었습니다."
    except (NTSAPIException, GiftCardAPIException):
        is_manual_review = True
        custom_message = "공공데이터 연동 오류로 관리자 수동 검토가 접수되었습니다."

    # 가맹점 정보 저장
    new_store = Store(
        business_number=payload.business_number,
        name=payload.name,
        address=payload.address or "주소 미입력",
        is_manual_review=is_manual_review,
        nts_verified=nts_verified,
        gift_card_verified=gift_card_verified,
        public_data_source="국세청 사업자등록정보 진위확인 + 한국조폐공사 지역사랑상품권 가맹점 기본정보",
        verified_at=None if is_manual_review else datetime.datetime.now(datetime.timezone.utc)
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


@router.get("/public-data/summary", response_model=PublicDataSummaryResponse)
def get_public_data_summary(db: Session = Depends(get_db)) -> dict:
    """
    프론트에서 공공데이터 활용 지점을 보여주기 위한 요약 API.
    실제 인증된 가맹점이 있으면 DB 값을 우선 노출하고, 없을 때는 서비스 데모용
    지역사랑상품권 가맹점 예시를 반환합니다.
    """
    verified_stores = db.query(Store).filter(Store.gift_card_verified == True).order_by(Store.created_at.desc()).limit(5).all()
    stores = [
        {
            "id": str(store.id),
            "name": store.name,
            "address": store.address,
            "category": "인증 가맹점",
            "gift_card_verified": store.gift_card_verified,
            "source": store.public_data_source or "한국조폐공사 지역사랑상품권 가맹점 기본정보",
        }
        for store in verified_stores
    ]

    if not stores:
        stores = [
            {
                "id": "sample-1",
                "name": "아빠손칼국수",
                "address": "대전 유성구 덕명동",
                "category": "음식점",
                "gift_card_verified": True,
                "source": "한국조폐공사 지역사랑상품권 가맹점 기본정보",
            },
            {
                "id": "sample-2",
                "name": "서래갈매기",
                "address": "대전 유성구 덕명동",
                "category": "음식점",
                "gift_card_verified": True,
                "source": "한국조폐공사 지역사랑상품권 가맹점 기본정보",
            },
            {
                "id": "sample-3",
                "name": "스모어사이트",
                "address": "대전 유성구 덕명동",
                "category": "카페",
                "gift_card_verified": True,
                "source": "한국조폐공사 지역사랑상품권 가맹점 기본정보",
            },
        ]

    return {
        "title": "공공데이터 기반 지역사랑상품권 가맹점",
        "description": "국세청 사업자등록정보와 한국조폐공사 지역사랑상품권 가맹점 데이터를 함께 대조합니다.",
        "sources": [
            {
                "name": "사업자등록정보 진위확인",
                "provider": "국세청 / 공공데이터포털",
                "purpose": "사업자등록번호, 대표자성명, 사업장명 진위 확인",
                "status": "인증 단계 적용",
            },
            {
                "name": "지역사랑상품권 가맹점 기본정보",
                "provider": "한국조폐공사 / 공공데이터포털",
                "purpose": "지역사랑상품권 결제 가능 가맹점 여부 확인",
                "status": "가맹점 인증 및 추천 가게 표시 적용",
            },
        ],
        "stores": stores,
    }
