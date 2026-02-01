# JWT 인증 시스템 가이드

이 가이드는 상담사 전용 로그인 기능을 설정하는 방법을 설명합니다.

---

## 📋 목차

1. [Railway PostgreSQL 설정](#1-railway-postgresql-설정)
2. [환경 변수 설정](#2-환경 변수-설정)
3. [첫 사용자 등록](#3-첫-사용자-등록)
4. [사용 방법](#4-사용-방법)
5. [보안 설정](#5-보안-설정)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. Railway PostgreSQL 설정

### 1.1 PostgreSQL 추가

1. Railway Dashboard → 프로젝트 선택
2. **"New"** 클릭 → **"Database"** → **"Add PostgreSQL"**
3. 자동으로 PostgreSQL 인스턴스 생성됨

### 1.2 DATABASE_URL 확인

PostgreSQL이 추가되면 자동으로 `DATABASE_URL` 환경 변수가 생성됩니다.

확인 방법:
1. PostgreSQL 서비스 클릭
2. **"Variables"** 탭
3. `DATABASE_URL` 복사 (형식: `postgres://user:password@host:port/database`)

**⚠️ 중요:** 백엔드 서비스에 자동으로 연결되지만, 확인해주세요!

---

## 2. 환경 변수 설정

### 2.1 Railway 환경 변수

Railway Dashboard → 백엔드 서비스 → **Variables** 탭:

```env
# 데이터베이스 (자동 설정됨)
DATABASE_URL=postgres://...

# JWT 설정 (새로 추가)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRE_MINUTES=10080

# 기존 환경 변수 (유지)
VSR_URL=https://your-vercel-domain.vercel.app
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads
```

#### JWT_SECRET_KEY 생성 방법:

**옵션 1: OpenSSL (추천)**
```bash
openssl rand -hex 32
# 출력: a1b2c3d4e5f6...
```

**옵션 2: Python**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**옵션 3: 온라인**
- https://randomkeygen.com/ (Fort Knox Passwords 사용)

#### JWT_EXPIRE_MINUTES 설명:
- `10080` = 7일 (기본값)
- `1440` = 1일
- `60` = 1시간

### 2.2 Vercel 환경 변수

변경 없음! 기존 설정 유지:

```env
BACKEND_URL=https://voice-split-rag-production.up.railway.app
```

**⚠️ 중요:** `FRONTEND_API_KEY`는 더 이상 필요 없습니다! 삭제해도 됩니다.

---

## 3. 첫 사용자 등록

### 3.1 배포 확인

1. Railway가 자동으로 재배포되었는지 확인
2. Vercel도 자동 재배포 확인

### 3.2 회원가입

1. Vercel 도메인 접속: `https://your-domain.vercel.app`
2. 자동으로 로그인 페이지로 이동
3. **"회원가입"** 탭 클릭
4. 정보 입력:
   - **아이디**: 최소 3자 (예: `admin`)
   - **이메일**: 유효한 이메일 (예: `admin@company.com`)
   - **이름**: 선택사항 (예: `홍길동`)
   - **비밀번호**: 최소 6자
5. **"회원가입"** 클릭
6. 성공 메시지 확인
7. **"로그인"** 탭으로 전환

### 3.3 로그인

1. 아이디와 비밀번호 입력
2. **"로그인"** 클릭
3. 메인 페이지로 이동
4. 우측 상단에 **"로그아웃"** 버튼 확인

---

## 4. 사용 방법

### 4.1 로그인

1. `https://your-domain.vercel.app` 접속
2. 로그인하지 않았으면 자동으로 로그인 페이지로 이동
3. 아이디와 비밀번호 입력
4. 로그인 성공 → 메인 페이지

### 4.2 음성 파일 업로드

로그인한 사용자만 음성 파일을 업로드하고 화자 구분을 실행할 수 있습니다.

### 4.3 로그아웃

메인 페이지 우측 상단 **"로그아웃"** 버튼 클릭

### 4.4 토큰 만료

- JWT 토큰은 7일 후 만료됩니다 (기본 설정)
- 만료되면 자동으로 로그인 페이지로 이동
- 다시 로그인하면 새 토큰 발급

---

## 5. 보안 설정

### 5.1 JWT_SECRET_KEY 변경

**⚠️ 매우 중요:** 프로덕션 환경에서는 반드시 강력한 JWT_SECRET_KEY를 사용하세요!

```bash
openssl rand -hex 32
```

Railway Variables에서 업데이트:
1. Railway Dashboard → 백엔드 서비스
2. **Variables** → `JWT_SECRET_KEY` 편집
3. 새 키 입력 → 저장
4. 자동 재배포

**⚠️ 주의:** JWT_SECRET_KEY를 변경하면 기존 토큰이 모두 무효화됩니다!

### 5.2 비밀번호 정책

현재 설정:
- **최소 길이**: 6자
- **해싱 알고리즘**: bcrypt
- **솔트 라운드**: 12 (기본값)

더 강력한 정책이 필요하면 `back/schemas/user.py` 수정:

```python
password: str = Field(..., min_length=8, max_length=100)  # 최소 8자로 변경
```

### 5.3 관리자 계정

첫 번째 등록한 사용자를 관리자로 설정하려면:

1. Railway PostgreSQL 접속 (psql 사용)
2. 다음 쿼리 실행:

```sql
UPDATE users SET is_superuser = true WHERE email = 'admin@company.com';
```

또는 Railway Dashboard → PostgreSQL → **Query** 탭에서 실행

---

## 6. 트러블슈팅

### 6.1 "Cannot connect to database" 에러

**원인:** DATABASE_URL이 설정되지 않음

**해결:**
1. Railway → PostgreSQL 서비스 확인
2. 백엔드 서비스에 PostgreSQL이 연결되었는지 확인
3. 수동 연결:
   - 백엔드 Variables → **New Variable**
   - `DATABASE_URL` = PostgreSQL의 `DATABASE_URL` 복사

### 6.2 "Invalid authentication credentials" 에러

**원인:** JWT 토큰이 만료되거나 유효하지 않음

**해결:**
1. 로그아웃 후 다시 로그인
2. localStorage 클리어:
   ```javascript
   localStorage.removeItem('access_token');
   ```
3. JWT_SECRET_KEY가 변경되었는지 확인

### 6.3 회원가입 시 "Email already registered" 에러

**원인:** 이미 등록된 이메일

**해결:**
- 다른 이메일 사용
- 또는 기존 계정으로 로그인

### 6.4 "User not found" 에러

**원인:** 데이터베이스 테이블이 생성되지 않음

**해결:**
1. Railway 배포 로그 확인:
   ```
   Creating database tables...
   Database tables created successfully
   ```
2. 로그에 에러가 있다면 DATABASE_URL 확인
3. Railway 재배포

---

## 📊 데이터베이스 구조

### Users 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer | 기본 키 (자동 증가) |
| `email` | String | 이메일 (고유, 인덱스) |
| `username` | String | 아이디 (고유, 인덱스) |
| `hashed_password` | String | 해시된 비밀번호 |
| `full_name` | String | 이름 (선택사항) |
| `is_active` | Boolean | 활성 상태 (기본: true) |
| `is_superuser` | Boolean | 관리자 여부 (기본: false) |
| `created_at` | DateTime | 생성 시간 |
| `updated_at` | DateTime | 수정 시간 |

---

## 🔐 API 엔드포인트

### 인증 API

#### 회원가입
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "홍길동" // 선택사항
}
```

#### 로그인
```http
POST /auth/login
Content-Type: application/json

{
  "username": "username",
  "password": "password123"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 내 정보 조회
```http
GET /auth/me
Authorization: Bearer <access_token>

Response:
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "홍길동",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-01T12:00:00Z"
}
```

### 보호된 API (JWT 필요)

#### Pre-signed URL 생성
```http
POST /voice/generate-upload-url
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filename": "audio.mp3",
  "content_type": "audio/mpeg"
}
```

#### 음성 파일 처리
```http
POST /voice/process-s3-file
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "s3_key": "uploads/20260201-093239-09f3f353.m4a",
  "language_code": "ko"
}
```

---

## ✅ 체크리스트

설정 완료 확인:

- [ ] Railway PostgreSQL 추가
- [ ] `DATABASE_URL` 환경 변수 자동 설정 확인
- [ ] `JWT_SECRET_KEY` 생성 및 설정
- [ ] `JWT_EXPIRE_MINUTES` 설정 (선택사항)
- [ ] Railway 재배포 완료
- [ ] Vercel 재배포 완료
- [ ] 회원가입 테스트
- [ ] 로그인 테스트
- [ ] 음성 파일 업로드 테스트
- [ ] 로그아웃 테스트

---

## 📚 참고 자료

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Railway PostgreSQL](https://docs.railway.app/databases/postgresql)

---

## ✨ 완료!

이제 상담사 전용 로그인 시스템이 완성되었습니다! 🎉

안전하고 편리하게 음성 화자 구분 서비스를 사용하세요!
