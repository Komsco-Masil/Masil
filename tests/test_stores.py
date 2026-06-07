from app.models.user import User
from app.models.store import Store, StoreUser


def test_verify_store_success(client, db):
    """가맹점 인증 및 사장 권한 격상 성공 테스트"""
    # 1. 회원가입 및 로그인
    client.post(
        "/api/auth/signup",
        json={
            "nickname": "owner_user",
            "neighborhood": "서울시 마포구",
            "password": "ownerpassword",
            "is_terms_agreed": True
        }
    )
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "owner_user", "password": "ownerpassword"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 가맹점 인증 요청
    response = client.post(
        "/api/stores/verify",
        json={
            "business_number": "123-45-67890",
            "name": "마실카페",
            "address": "서울시 마포구 망원동 123"
        },
        headers=headers
    )
    assert response.status_code == 201
    store_data = response.json()
    assert store_data["business_number"] == "123-45-67890"
    assert store_data["is_manual_review"] is False

    # 3. DB 상태 검증
    user = db.query(User).filter(User.nickname == "owner_user").first()
    assert user.role == "OWNER"

    store = db.query(Store).filter(Store.business_number == "123-45-67890").first()
    assert store is not None

    mapping = db.query(StoreUser).filter(
        StoreUser.store_id == store.id, 
        StoreUser.user_id == user.id
    ).first()
    assert mapping is not None
    assert mapping.role == "OWNER"


def test_verify_store_duplicate_business_number(client, db):
    """이미 다른 유저가 등록한 사업자등록번호일 경우 409 Conflict 발생 테스트"""
    # 1. 사장 1 가맹점 등록
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner1", "neighborhood": "동네1", "password": "password", "is_terms_agreed": True}
    )
    t1 = client.post("/api/auth/login", data={"username": "owner1", "password": "password"}).json()["access_token"]
    client.post(
        "/api/stores/verify",
        json={"business_number": "999-99-99999", "name": "가게1", "address": "주소1"},
        headers={"Authorization": f"Bearer {t1}"}
    )

    # 2. 사장 2 동일 사업자등록번호로 등록 시도
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner2", "neighborhood": "동네2", "password": "password", "is_terms_agreed": True}
    )
    t2 = client.post("/api/auth/login", data={"username": "owner2", "password": "password"}).json()["access_token"]
    
    response = client.post(
        "/api/stores/verify",
        json={"business_number": "999-99-99999", "name": "가게2", "address": "주소2"},
        headers={"Authorization": f"Bearer {t2}"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Store already registered"


def test_verify_store_details_mismatch(client):
    """가게 세부 정보 대조 실패 시 400 Bad Request 테스트"""
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner3", "neighborhood": "동네3", "password": "password", "is_terms_agreed": True}
    )
    t3 = client.post("/api/auth/login", data={"username": "owner3", "password": "password"}).json()["access_token"]
    
    response = client.post(
        "/api/stores/verify",
        json={"business_number": "invalid-store", "name": "가게3", "address": "주소3"},
        headers={"Authorization": f"Bearer {t3}"}
    )
    assert response.status_code == 400
    assert "사업자 정보 불일치" in response.json()["detail"]


def test_verify_store_timeout_fallback(client, db):
    """외부 API 타임아웃/오류 발생 시 500 에러 없이 is_manual_review=True로 저장 및 승인 테스트"""
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner4", "neighborhood": "동네4", "password": "password", "is_terms_agreed": True}
    )
    t4 = client.post("/api/auth/login", data={"username": "owner4", "password": "password"}).json()["access_token"]
    
    response = client.post(
        "/api/stores/verify",
        json={"business_number": "timeout-555", "name": "타임아웃가게", "address": "대기주소"},
        headers={"Authorization": f"Bearer {t4}"}
    )
    assert response.status_code == 201
    assert response.json()["is_manual_review"] is True
    assert response.json()["message"] == "인증 서버 지연으로 인해 관리자 수동 검토로 전환되었습니다."

    # DB 검증 (수동 검토 플래그 및 권한 격상 완료 확인)
    user = db.query(User).filter(User.nickname == "owner4").first()
    assert user.role == "OWNER"

    store = db.query(Store).filter(Store.business_number == "timeout-555").first()
    assert store.is_manual_review is True

    mapping = db.query(StoreUser).filter(
        StoreUser.store_id == store.id, 
        StoreUser.user_id == user.id
    ).first()
    assert mapping.role == "OWNER"


def test_verify_store_nts_fields(client, db):
    """국세청 파라미터(개업일자, 대표자명)가 전달되었을 때의 성공 테스트"""
    # 1. 회원가입 및 로그인
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner5", "neighborhood": "서울시 서초구", "password": "password", "is_terms_agreed": True}
    )
    t = client.post("/api/auth/login", data={"username": "owner5", "password": "password"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {t}"}

    # 2. 가맹점 인증 요청 (국세청 파라미터 포함)
    response = client.post(
        "/api/stores/verify",
        json={
            "business_number": "123-45-67890",
            "name": "마실카페2",
            "address": "서울시 서초구 서초동 123",
            "start_date": "20200101",
            "representative_name": "홍길동"
        },
        headers=headers
    )
    assert response.status_code == 201
    store_data = response.json()
    assert store_data["business_number"] == "123-45-67890"
    assert store_data["is_manual_review"] is False

