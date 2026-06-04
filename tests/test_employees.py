import datetime
from app.models.user import User
from app.models.store import Store, StoreUser
from app.models.invite import StoreInvite


def test_employee_flow_success(client, db):
    """직원 초대 코드 발급, 등록 및 사장의 직원 해제 전체 성공 시나리오 테스트"""
    # 1. 사장 회원가입 및 로그인
    client.post(
        "/api/auth/signup", 
        json={"nickname": "owner", "neighborhood": "동네", "password": "password", "is_terms_agreed": True}
    )
    t_owner = client.post("/api/auth/login", data={"username": "owner", "password": "password"}).json()["access_token"]
    h_owner = {"Authorization": f"Bearer {t_owner}"}

    # 2. 사장 가맹점 등록
    store_resp = client.post(
        "/api/stores/verify",
        json={"business_number": "111-22-33333", "name": "가게", "address": "주소"},
        headers=h_owner
    )
    store_id = store_resp.json()["id"]

    # 3. 사장이 초대 코드 생성
    invite_resp = client.post(
        "/api/stores/invites",
        json={"store_id": store_id},
        headers=h_owner
    )
    assert invite_resp.status_code == 201
    invite_code = invite_resp.json()["invite_code"]

    # 4. 일반 유저(직원 지망) 가입 및 로그인
    client.post(
        "/api/auth/signup", 
        json={"nickname": "employee", "neighborhood": "동네", "password": "password", "is_terms_agreed": True}
    )
    t_emp = client.post("/api/auth/login", data={"username": "employee", "password": "password"}).json()["access_token"]
    h_emp = {"Authorization": f"Bearer {t_emp}"}

    # 5. 직원이 초대 코드 등록
    use_resp = client.post(
        "/api/stores/invites/use",
        json={"invite_code": invite_code},
        headers=h_emp
    )
    assert use_resp.status_code == 200
    assert use_resp.json()["role"] == "EMPLOYEE"

    # DB 확인: 직원 권한 격상 및 매핑 생성 확인
    emp_user = db.query(User).filter(User.nickname == "employee").first()
    assert emp_user.role == "EMPLOYEE"

    mapping = db.query(StoreUser).filter(
        StoreUser.store_id == store_id, 
        StoreUser.user_id == emp_user.id
    ).first()
    assert mapping is not None
    assert mapping.role == "EMPLOYEE"

    # 6. 사장이 직원 연동 해제
    del_resp = client.delete(
        f"/api/stores/employees/{emp_user.id}",
        headers=h_owner
    )
    assert del_resp.status_code == 200

    # DB 확인: 매핑 삭제 및 권한 USER 복귀 확인
    mapping = db.query(StoreUser).filter(
        StoreUser.store_id == store_id, 
        StoreUser.user_id == emp_user.id
    ).first()
    assert mapping is None

    db.refresh(emp_user)
    assert emp_user.role == "USER"


def test_create_invite_non_owner_forbidden(client):
    """일반 USER 권한 유저가 초대 생성 시도 시 403 Forbidden 반환 테스트"""
    client.post(
        "/api/auth/signup", 
        json={"nickname": "normal", "neighborhood": "동네", "password": "password", "is_terms_agreed": True}
    )
    t_normal = client.post("/api/auth/login", data={"username": "normal", "password": "password"}).json()["access_token"]
    h_normal = {"Authorization": f"Bearer {t_normal}"}

    response = client.post(
        "/api/stores/invites",
        json={"store_id": 999},
        headers=h_normal
    )
    assert response.status_code == 403
    assert "OWNER" in response.json()["detail"]


def test_use_invite_expired_or_used(client, db):
    """만료되거나 이미 사용된 초대 코드 등록 시도 시 400 Bad Request 테스트"""
    # 임시 유저 및 가맹점 직접 생성
    owner = User(nickname="owner2", neighborhood="동네", role="OWNER")
    db.add(owner)
    db.flush()

    store = Store(business_number="222-33-44444", name="가게2", address="주소2")
    db.add(store)
    db.flush()

    # 만료된 초대장 DB에 직접 추가
    expired_invite = StoreInvite(
        invite_code="EXPIRED_CODE",
        store_id=store.id,
        expires_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=1),
        is_used=False
    )
    db.add(expired_invite)

    # 사용된 초대장 DB에 직접 추가
    used_invite = StoreInvite(
        invite_code="USED_CODE",
        store_id=store.id,
        expires_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=24),
        is_used=True
    )
    db.add(used_invite)
    db.commit()

    # 일반 유저 가입 및 로그인
    client.post(
        "/api/auth/signup", 
        json={"nickname": "normal_user", "neighborhood": "동네", "password": "password", "is_terms_agreed": True}
    )
    t_user = client.post("/api/auth/login", data={"username": "normal_user", "password": "password"}).json()["access_token"]
    h_user = {"Authorization": f"Bearer {t_user}"}

    # 1. 만료된 코드 사용 시도
    response = client.post(
        "/api/stores/invites/use",
        json={"invite_code": "EXPIRED_CODE"},
        headers=h_user
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]

    # 2. 이미 사용된 코드 사용 시도
    response = client.post(
        "/api/stores/invites/use",
        json={"invite_code": "USED_CODE"},
        headers=h_user
    )
    assert response.status_code == 400
    assert "used" in response.json()["detail"]
