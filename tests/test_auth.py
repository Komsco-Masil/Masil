def test_signup_success(client):
    """일반 회원가입 성공 테스트"""
    response = client.post(
        "/api/auth/signup",
        json={
            "nickname": "masil_user",
            "neighborhood": "서울시 마포구 망원동",
            "password": "testpassword",
            "is_terms_agreed": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nickname"] == "masil_user"
    assert data["neighborhood"] == "서울시 마포구 망원동"
    assert data["role"] == "USER"
    assert data["provider"] == "LOCAL"
    assert "id" in data


def test_signup_terms_disagreed(client):
    """약관 동의를 거부할 경우 400 Bad Request 반환 테스트"""
    response = client.post(
        "/api/auth/signup",
        json={
            "nickname": "disagree_user",
            "neighborhood": "서울시 마포구 합정동",
            "password": "testpassword",
            "is_terms_agreed": False
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Terms agreement is required"


def test_signup_duplicate_nickname(client):
    """닉네임 중복 시 400 Bad Request 및 중복 에러 메시지 반환 테스트"""
    # 첫번째 회원가입
    client.post(
        "/api/auth/signup",
        json={
            "nickname": "dup_user",
            "neighborhood": "동네1",
            "password": "testpassword",
            "is_terms_agreed": True
        }
    )
    # 중복 가입 시도
    response = client.post(
        "/api/auth/signup",
        json={
            "nickname": "dup_user",
            "neighborhood": "동네2",
            "password": "anotherpassword",
            "is_terms_agreed": True
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Nickname already exists"


def test_signup_oauth_success(client):
    """OAuth 가입 성공 테스트"""
    response = client.post(
        "/api/auth/signup",
        json={
            "nickname": "kakao_user",
            "neighborhood": "서울시 강남구 역삼동",
            "provider": "KAKAO",
            "social_id": "kakao_123456",
            "is_terms_agreed": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "KAKAO"
    assert data["social_id"] == "kakao_123456"


def test_login_success(client):
    """로그인 및 JWT 토큰 반환 성공 테스트"""
    # 가입
    client.post(
        "/api/auth/signup",
        json={
            "nickname": "login_user",
            "neighborhood": "서울시 마포구",
            "password": "correct_password",
            "is_terms_agreed": True
        }
    )
    # 로그인
    response = client.post(
        "/api/auth/login",
        data={
            "username": "login_user",
            "password": "correct_password"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_fail(client):
    """잘못된 자격 증명으로 로그인 시도 시 실패 테스트"""
    client.post(
        "/api/auth/signup",
        json={
            "nickname": "login_user2",
            "neighborhood": "서울시 마포구",
            "password": "correct_password",
            "is_terms_agreed": True
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "login_user2",
            "password": "wrong_password"
        }
    )
    assert response.status_code == 400
    assert "Incorrect nickname or password" in response.json()["detail"]
