from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_owner
from app.models.user import User
from app.models.store import StoreUser
from app.models.invite import StoreInvite
from app.schemas.invite import InviteCreate, InviteResponse, InviteUseRequest

router = APIRouter()


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_owner)
) -> StoreInvite:
    """
    직원 초대 코드 생성 API (MEM-04)
    
    - OWNER 권한을 가진 사장님만 호출 가능
    - 사장 본인이 소유한 가맹점 ID인 경우에만 생성 가능
    - 24시간 동안 유효한 고유 무작위 초대 코드 생성
    """
    # 현재 로그인한 사장님이 해당 가맹점의 사장이 맞는지 확인
    ownership = db.query(StoreUser).filter(
        StoreUser.store_id == payload.store_id,
        StoreUser.user_id == current_owner.id,
        StoreUser.role == "OWNER"
    ).first()

    if not ownership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this store"
        )

    # 24시간 후 만료되는 초대코드 생성
    invite_code = secrets.token_hex(4).upper()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)

    new_invite = StoreInvite(
        invite_code=invite_code,
        store_id=payload.store_id,
        expires_at=expires_at,
        is_used=False
    )
    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)
    return new_invite


@router.post("/invites/use", status_code=status.HTTP_200_OK)
def use_invite(
    payload: InviteUseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    직원 초대 코드 등록 API (MEM-04)
    
    - 일반 직원이 초대 코드를 등록하여 가게와 연동
    - 코드가 유효한지(만료 여부, 사용 여부) 검증
    - 성공 시 유저의 role을 EMPLOYEE로 격상
    """
    invite = db.query(StoreInvite).filter(
        StoreInvite.invite_code == payload.invite_code
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation code not found"
        )

    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation code already used"
        )

    if invite.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation code expired"
        )

    # 이미 동일 가맹점에 소속되어 있는지 중복 연동 확인
    existing_mapping = db.query(StoreUser).filter(
        StoreUser.store_id == invite.store_id,
        StoreUser.user_id == current_user.id
    ).first()

    if existing_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already linked to this store"
        )

    # 권한 격상
    current_user.role = "EMPLOYEE"

    # 가맹점-직원 매핑 테이블 기록
    new_mapping = StoreUser(
        store_id=invite.store_id,
        user_id=current_user.id,
        role="EMPLOYEE"
    )
    db.add(new_mapping)

    # 초대장 사용 상태 변경
    invite.is_used = True
    db.commit()

    return {
        "status": "success",
        "detail": "Successfully joined the store as employee",
        "store_id": invite.store_id,
        "role": "EMPLOYEE"
    }


@router.delete("/employees/{employee_id}", status_code=status.HTTP_200_OK)
def remove_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_owner)
) -> dict:
    """
    직원 연동 해제 API (MEM-04)
    
    - OWNER 권한을 가진 사장님만 호출 가능
    - 사장의 가맹점에 속한 직원인지 확인 후 연동 해제 (매핑 테이블 행 삭제)
    - 해당 직원이 더 이상 다른 가맹점과 연동되어 있지 않다면 role을 USER로 원복
    """
    # 1. 사장이 소유한 모든 가맹점 ID 조회
    owned_store_ids = [
        mapping.store_id
        for mapping in db.query(StoreUser).filter(
            StoreUser.user_id == current_owner.id,
            StoreUser.role == "OWNER"
        ).all()
    ]

    if not owned_store_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own any stores"
        )

    # 2. 사장의 가맹점 중 하나에 employee_id가 속해있는지 매핑 조회
    employee_mapping = db.query(StoreUser).filter(
        StoreUser.user_id == employee_id,
        StoreUser.store_id.in_(owned_store_ids),
        StoreUser.role == "EMPLOYEE"
    ).first()

    if not employee_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your stores"
        )

    # 매핑 삭제
    db.delete(employee_mapping)
    db.flush()

    # 3. 해제된 직원이 더 이상 다른 어떤 가맹점에도 매핑되어 있지 않다면 USER로 역할 복귀
    other_mappings = db.query(StoreUser).filter(
        StoreUser.user_id == employee_id
    ).first()

    if not other_mappings:
        employee_user = db.query(User).filter(User.id == employee_id).first()
        if employee_user:
            employee_user.role = "USER"

    db.commit()
    return {
        "status": "success",
        "detail": f"Employee {employee_id} successfully unlinked"
    }
