# 배포 가이드 (Vercel + Railway)

이 문서는 Voice Split RAG 프로젝트를 Vercel(프론트엔드)과 Railway(백엔드)에 배포하는 단계별 가이드입니다.

## 📋 사전 준비사항

- [ ] GitHub 계정
- [ ] Vercel 계정 (GitHub으로 로그인 가능)
- [ ] Railway 계정 (GitHub으로 로그인 가능)
- [ ] Google Cloud Platform 프로젝트 및 Service Account Key
- [ ] 프로젝트를 GitHub에 푸시

## 🚀 배포 순서

### 1단계: 백엔드 배포 (Railway) - 먼저!

#### 1.1. Railway 프로젝트 생성

1. [Railway](https://railway.app)에 접속
2. "Login" → GitHub 계정으로 로그인
3. "New Project" 클릭
4. "Deploy from GitHub repo" 선택
5. `voice-split-rag` 저장소 선택
6. "Deploy Now" 클릭

#### 1.2. Root Directory 설정

1. 생성된 프로젝트 클릭
2. Settings 탭 → "Root Directory"
3. `back` 입력하고 저장

#### 1.3. 환경 변수 설정

Variables 탭에서 다음 환경 변수를 추가:

```env
# 필수: 프론트엔드 URL (일단 임시로 설정, 나중에 업데이트)
VSR_URL=https://temporary-url.vercel.app

# Google Cloud 설정 (필수)
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GCS_BUCKET_NAME=your-bucket-name

# Google Service Account JSON (방법 1 - 권장)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"...전체 JSON 내용..."}

# 또는 개별 필드로 설정 (방법 2)
# GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
# 이 경우 startup 스크립트 필요

# 선택 사항
OPENAI_API_KEY=your-openai-key-if-needed
LANGCHAIN_API_KEY=your-langsmith-key-if-needed
```

**Google Service Account JSON 가져오기:**
1. Google Cloud Console → IAM & Admin → Service Accounts
2. Service Account 선택 → Keys 탭
3. "Add Key" → "Create new key" → JSON 선택
4. 다운로드된 JSON 파일을 열어서 **전체 내용**을 복사
5. Railway Variables에 `GOOGLE_APPLICATION_CREDENTIALS_JSON`으로 추가

#### 1.4. 배포 시작

환경 변수를 저장하면 자동으로 배포가 시작됩니다.

#### 1.5. 배포 URL 확인

1. Settings 탭 → "Networking" 섹션
2. "Generate Domain" 클릭 (아직 없다면)
3. 생성된 URL 복사 (예: `https://your-backend.railway.app`)

#### 1.6. 배포 확인

브라우저에서 다음 URL 접속:
- API 문서: `https://your-backend.railway.app/docs`
- 상태 확인: `https://your-backend.railway.app/metrics`

---

### 2단계: 프론트엔드 배포 (Vercel)

#### 2.1. Vercel 프로젝트 생성

1. [Vercel](https://vercel.com)에 접속
2. "Login" → GitHub 계정으로 로그인
3. "Add New..." → "Project" 클릭
4. `voice-split-rag` 저장소를 Import

#### 2.2. 프로젝트 설정

**Configure Project** 화면에서:

1. **Framework Preset**: Next.js (자동 선택됨)
2. **Root Directory**: `front` 입력 후 체크
3. **Build Command**: `npm run build` (기본값)
4. **Output Directory**: `.next` (기본값)

#### 2.3. 환경 변수 설정

Environment Variables 섹션에서:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app
```

Railway에서 복사한 백엔드 URL을 입력하세요.

#### 2.4. 배포 시작

"Deploy" 버튼 클릭!

#### 2.5. 배포 URL 확인

배포가 완료되면 Vercel이 자동으로 생성한 URL을 확인하세요.
- 예: `https://voice-split-rag.vercel.app`

---

### 3단계: CORS 설정 업데이트 (중요!)

프론트엔드 배포가 완료되면, Railway로 돌아가서 백엔드 환경 변수를 업데이트하세요.

#### 3.1. Railway 환경 변수 업데이트

1. Railway Dashboard → 백엔드 프로젝트
2. Variables 탭
3. `VSR_URL` 값을 **실제 Vercel URL**로 변경:

```env
VSR_URL=https://voice-split-rag.vercel.app
```

4. 저장하면 자동으로 재배포됩니다.

---

## ✅ 배포 확인 체크리스트

### 백엔드 확인
- [ ] Railway 배포 성공 (Deployments 탭에서 확인)
- [ ] API 문서 접속 가능: `https://your-backend.railway.app/docs`
- [ ] 환경 변수 모두 설정됨
- [ ] Google Cloud 인증 성공

### 프론트엔드 확인
- [ ] Vercel 배포 성공
- [ ] 프론트엔드 접속 가능: `https://your-frontend.vercel.app`
- [ ] `NEXT_PUBLIC_API_BASE_URL` 설정됨

### 통합 테스트
- [ ] 프론트엔드에서 오디오 파일 업로드 가능
- [ ] 화자 구분 처리 정상 작동
- [ ] 결과 화면 정상 표시
- [ ] CORS 오류 없음

---

## 🔧 문제 해결

### Railway 빌드 실패

**증상**: "Build failed" 메시지

**해결 방법**:
1. Deployments 탭에서 로그 확인
2. 대부분 환경 변수 누락 문제
3. `nixpacks.toml` 파일이 있는지 확인
4. Python 버전 확인 (`runtime.txt`)

### Google Cloud 인증 오류

**증상**: "Could not automatically determine credentials"

**해결 방법**:
1. `GOOGLE_APPLICATION_CREDENTIALS_JSON` 환경 변수 확인
2. JSON 형식이 올바른지 확인 (전체 내용 복사)
3. Service Account에 필요한 권한이 있는지 확인:
   - Cloud Speech-to-Text Admin
   - Storage Admin (GCS 사용 시)

### CORS 오류

**증상**: "blocked by CORS policy"

**해결 방법**:
1. Railway의 `VSR_URL` 환경 변수가 Vercel URL과 **정확히** 일치하는지 확인
2. `https://` 포함 여부 확인
3. 뒤에 슬래시(`/`) 없이 입력

### 프론트엔드에서 API 호출 실패

**증상**: Network error, fetch failed

**해결 방법**:
1. Vercel 환경 변수 `NEXT_PUBLIC_API_BASE_URL` 확인
2. Railway 백엔드가 실행 중인지 확인
3. Railway URL이 올바른지 확인
4. 브라우저 개발자 도구 Network 탭 확인

---

## 🔄 재배포 방법

### 코드 변경 후 재배포

1. **GitHub에 코드 푸시**
```bash
git add .
git commit -m "Update code"
git push origin main
```

2. **자동 배포**
   - Railway와 Vercel 모두 GitHub push를 감지하여 자동 재배포됩니다.

### 환경 변수만 변경

1. Railway 또는 Vercel Dashboard에서 환경 변수 수정
2. 저장하면 자동으로 재배포됩니다.

---

## 📚 추가 리소스

- [Railway 문서](https://docs.railway.app/)
- [Vercel 문서](https://vercel.com/docs)
- [Next.js 배포 가이드](https://nextjs.org/docs/deployment)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)

---

## 💡 팁

1. **무료 플랜 제한**
   - Railway: $5 크레딧/월 (작은 프로젝트에 충분)
   - Vercel: 무제한 (Fair Use Policy)

2. **커스텀 도메인**
   - Vercel과 Railway 모두 커스텀 도메인 지원
   - Settings → Domains에서 설정 가능

3. **로그 확인**
   - Railway: Deployments 탭 → View Logs
   - Vercel: Deployments 탭 → Function Logs

4. **환경 분리**
   - Railway와 Vercel 모두 Preview/Production 환경 지원
   - `main` 브랜치는 Production, 다른 브랜치는 Preview

---

문제가 발생하면 각 플랫폼의 로그를 먼저 확인하세요!
