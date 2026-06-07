# 🏡 마실 (Masil) - FastAPI 백엔드 서비스

> **한국조폐공사(KOMSCO) 대회 출품작**
>
> 공공데이터, 지역사랑상품권 가맹점, 로컬 이벤트 및 동네 활동을 연결하여 지역 공동체를 활성화하는 로컬 커뮤니티 애플리케이션 **'마실(Masil)'**의 FastAPI 백엔드 저장소입니다.

---

## 🛠 기술 스택 (Tech Stack)

- **Backend Framework**: `FastAPI` (Python 3.12+)
- **Database ORM**: `SQLAlchemy 2.0` (기본 PostgreSQL, 테스트/개발용 SQLite 지원)
- **Data Validation**: `Pydantic V2`
- **Security & Authentication**: `PyJWT` (python-jose), `Direct bcrypt` (passlib 72바이트 제한 우회)
- **Asynchronous HTTP Client**: `httpx` (한국조폐공사 가맹점 조회 OpenAPI 연동)
- **Testing**: `pytest`

---

## ✨ 구현된 핵심 기능 (Done)

현재 회원(User) 및 가맹점(Store) 연동과 관련된 핵심 기능(MEM-01 ~ MEM-04 마일스톤) 개발 및 단위 테스트가 완료되었습니다.

### 1. 회원 가입 및 JWT 인증 (`app/api/endpoints/auth.py`)
- **회원 가입 (`POST /api/auth/signup`)**:
  - 일반(LOCAL) 비밀번호 회원가입 및 OAuth 정보를 기록할 수 있는 확장식 설계.
  - Pydantic V2 `@field_validator`를 활용하여 필수 약관 동의(`is_terms_agreed=False`) 시 즉시 `400 Bad Request` 에러를 반환하는 강력한 유효성 검사 적용.
  - bcrypt 단독 해싱 모듈을 직접 연동하여 passlib의 72바이트 패스워드 버그와 Python 3.12+ 버그 우회.
- **로그인 (`POST /api/auth/login`)**:
  - 사용자 자격 증명 검증 및 JWT Access Token 발급.

### 2. 조폐공사 가맹점 실시간 대조 및 점주 권한 획득 (`app/api/endpoints/stores.py`)
- **가맹점 검증 및 등록 (`POST /api/stores/verify`)**:
  - 한국조폐공사 지역사랑상품권 가맹점 조회 OpenAPI와 실시간 비동기 연동(`httpx.AsyncClient` 사용).
  - API 연동 성공 시, 사용자를 해당 가맹점의 `OWNER` 역할로 승격시킵니다.
  - 외부 공공데이터 API 장애, 타임아웃 혹은 네트워크 순간 단절 시 `500 Internal Server Error`를 방출하지 않고 `is_manual_review=True`(수동 검토 대상) 플래그를 할당하여 임시 승인 처리하는 뛰어난 비즈니스 예외 복구(Graceful Degradation) 설계 적용.

### 3. 가맹점 직원 초대 및 해제 (`app/api/endpoints/employees.py`)
- **초대 코드 생성 (`POST /api/stores/invites`)**:
  - 가맹점주(OWNER)만 호출 가능하며, 24시간 동안 유효한 고유 무작위 직원 초대 코드를 생성합니다.
- **초대 코드 사용 (`POST /api/stores/invites/use`)**:
  - 가입한 일반 사용자가 초대 코드를 등록하여 해당 가맹점의 `EMPLOYEE`로 등록됩니다.
- **직원 연동 해제 (`DELETE /api/stores/employees/{employee_id}`)**:
  - 가맹점주가 등록된 직원을 연동 해제합니다. 직원이 다른 가맹점과 연동되어 있지 않은 상태라면 자동으로 일반 `USER` 역할로 강등 처리됩니다.

---

## 📂 프로젝트 구조 (Project Structure)

```text
c:\Workspace\Masil
│  .env.example          # 환경 변수 설정 템플릿
│  agent.md              # 개발 기록 및 에이전트 로그
│  README.md             # 프로젝트 소개 (현재 파일)
│  requirements.txt      # 의존성 패키지 목록
│
├─app
│  │  main.py            # FastAPI 애플리케이션 진입점 (라우터 등록 및 초기화)
│  │
│  ├─api                 # API 엔드포인트 계층
│  │  │  deps.py         # DB 세션 및 JWT 사용자 권한 의존성 주입(Dependency)
│  │  │
│  │  └─endpoints        # 컨트롤러
│  │          auth.py       # 회원가입 및 로그인 API
│  │          employees.py  # 가맹점 직원 초대 및 해제 API
│  │          stores.py     # 가맹점 검증 및 등록 API
│  │
│  ├─core                # 핵심 공통 설정 및 데이터베이스 연결
│  │      config.py      # 환경 변수 및 설정 파일 매핑 클래스
│  │      database.py    # SQLAlchemy DB 엔진 및 기본 클래스(Base) 정의
│  │      security.py    # Direct bcrypt 비밀번호 해싱 및 JWT 유틸리티
│  │
│  ├─models              # SQLAlchemy DB 모델 정의
│  │      base.py        # 선언적 베이스 클래스
│  │      invite.py      # 가맹점 직원 초대 테이블 모델
│  │      store.py       # 가맹점 테이블 모델
│  │      user.py        # 사용자 테이블 모델
│  │
│  ├─schemas             # Pydantic V2 데이터 검증/직렬화 스키마
│  │      invite.py
│  │      store.py
│  │      user.py
│  │
│  └─services            # 비즈니스 서비스 & 외부 연동 모듈
│          giftcard_client.py   # 조폐공사 가맹점 OpenAPI 연동 비동기 클라이언트
│
└─tests                  # Pytest 기반 단위 테스트 디렉토리
        conftest.py      # 독립된 임시 SQLite 환경 설정 Fixture 제공
        test_auth.py     # 인증 API 테스트 (6개 케이스)
        test_employees.py# 가맹점 직원 API 테스트 (4개 케이스)
        test_stores.py   # 가맹점 검증 API 테스트 (3개 케이스)
```

---

## 🚀 시작하기 (Getting Started)

### 1. 가상환경 구축 및 패키지 설치
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows PowerShell 기준)
.\venv\Scripts\activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
설정 디렉토리의 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 공공데이터 포털 서비스 키 및 연결할 DB 정보를 입력합니다.
```bash
cp .env.example .env
```
- `DATABASE_URL`: PostgreSQL 데이터베이스 주소
- `KOREA_MINTING_SERVICE_KEY`: 공공데이터포털(data.go.kr)에서 발급받은 한국조폐공사 가맹점 조회 서비스 일반 인증키 (Decoding/Encoding 키 테스트 필요)

### 3. 애플리케이션 실행
```bash
uvicorn app.main:app --reload
```
실행 후 브라우저에서 `http://127.0.0.1:8000/docs` 로 접속하면 FastAPI OpenAPI Swagger 문서 인터페이스를 이용해 API를 대화형으로 테스트할 수 있습니다.

---

## 🧪 테스트 실행 방법 (Running Tests)

테스트는 실제 DB에 영향을 주지 않도록 `tests/conftest.py`에 정의된 독립적인 임시 SQLite 파일(`test_temp.db`) 환경에서 수행됩니다.

파이썬 경로를 포함하여 pytest를 다음과 같이 실행합니다.

```bash
# python 모듈 경로 모드로 pytest 실행 (권장)
python -m pytest

# 또는 환경 변수를 지정해 실행
set PYTHONPATH=.
pytest
```

---

## 📅 향후 작업 계획 (To-Do)

1. **JWT 토큰 정책 고도화**
   - Refresh Token 도입 및 Redis 혹은 DB를 활용한 JWT Blacklist 만료/무효화 기법 연동
2. **배치 스케줄러 도입**
   - 24시간 유효 기간이 만료된 미사용 `StoreInvite` 초대 코드를 주기적으로 삭제 또는 무효화하는 백그라운드 배치 작업 스케줄링
3. **홍보 게시판 (PROMOTION) CRUD 개발**
   - 지역 가맹점 및 동네 생활 소식을 전달하는 게시판용 DB 스키마 설계 및 CRUD API 신규 개발
