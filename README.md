# Voice Split RAG

음성 파일의 화자를 자동으로 구분하고 분석하는 웹 애플리케이션입니다.

## 프로젝트 구조

```
voice-split-rag/
├── front/              # Next.js 프론트엔드
│   ├── app/           # Next.js App Router
│   └── package.json
└── back/              # FastAPI 백엔드
    ├── app.py
    ├── requirements.txt
    ├── nixpacks.toml  # Railway 설정
    └── Procfile
```

## 기능

- 🎤 대용량 오디오 파일 업로드 (S3 Pre-signed URL)
- 🔊 자동 화자 구분 (Speaker Diarization)
- 📝 화자별 발화 내용 표시
- ⏱️ 시간순 대화 내용 표시
- 🔒 API 키 기반 인증 (프론트엔드 ↔ 백엔드)

## 기술 스택

**Frontend:**
- Next.js 15 (App Router)
- TypeScript
- CSS Modules

**Backend:**
- FastAPI
- Python 3.11
- AssemblyAI (Speech-to-Text + Speaker Diarization)
- AWS S3 (Pre-signed URL 업로드)
- boto3

**Deployment:**
- Vercel (Frontend)
- Railway (Backend)
- AWS S3 (File Storage)

## 빠른 시작

### 로컬 개발 환경

#### 1. 프론트엔드 실행

```bash
cd front
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 확인

#### 2. 백엔드 실행

```bash
cd back
pip install -r requirements.txt
# .env 파일 설정 (아래 참조)
uvicorn app:app --reload --port 8000
```

API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

자세한 내용은 각 디렉토리의 README를 참고하세요:
- [프론트엔드 가이드](./front/README.md)
- [백엔드 가이드](./back/README.md)

## 배포 가이드

### 필수 준비 사항

1. **AssemblyAI API 키**: [ASSEMBLYAI_SETUP.md](./ASSEMBLYAI_SETUP.md) 참조
2. **AWS S3 버킷**: [S3_SETUP.md](./S3_SETUP.md) 참조
3. **API 키 생성**: [SECURITY_SETUP.md](./SECURITY_SETUP.md) 참조

### 1단계: AWS S3 설정

자세한 내용: [S3_SETUP.md](./S3_SETUP.md)

1. S3 버킷 생성
2. IAM 사용자 생성 및 권한 설정
3. 액세스 키 발급

### 2단계: 백엔드 배포 (Railway)

#### Railway 프로젝트 생성
1. [Railway](https://railway.app)에 접속 및 로그인
2. "New Project" → "Deploy from GitHub repo"
3. 저장소 선택

#### 설정
1. **Root Directory**: `back` 설정
2. **환경 변수** 추가:
   ```env
   # 프론트엔드 URL
   VSR_URL=https://your-frontend-app.vercel.app
   
   # AssemblyAI
   ASSEMBLYAI_API_KEY=your-assemblyai-api-key
   
   # AWS S3
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=voice-split-rag-uploads
   
   # API 인증
   FRONTEND_API_KEY=your-frontend-api-key
   ```
3. Deploy 시작

#### 배포 URL 확인
- Settings → Networking에서 Railway URL 확인
- 예: `https://voice-split-rag-production.up.railway.app`

자세한 내용: [DEPLOYMENT.md](./DEPLOYMENT.md)

### 3단계: 프론트엔드 배포 (Vercel)

#### Vercel 프로젝트 생성
1. [Vercel](https://vercel.com)에 접속 및 로그인
2. "New Project" → GitHub 저장소 선택

#### 설정
1. **Root Directory**: `front` 설정
2. **Framework Preset**: Next.js (자동 감지)
3. **환경 변수** 추가:
   ```env
   BACKEND_URL=https://voice-split-rag-production.up.railway.app
   FRONTEND_API_KEY=your-frontend-api-key
   ```
4. Deploy 클릭

자세한 내용: [DEPLOYMENT.md](./DEPLOYMENT.md)

### 4단계: CORS 설정 업데이트

Railway에서 백엔드 환경 변수 업데이트:

```env
VSR_URL=https://your-actual-frontend.vercel.app
```

저장 후 Railway가 자동으로 재배포됩니다.

## 환경 변수 설정

### 프론트엔드 (front/.env.local)

```env
BACKEND_URL=http://localhost:8000  # 로컬 개발
# 또는
BACKEND_URL=https://your-backend.railway.app  # 프로덕션

FRONTEND_API_KEY=your-frontend-api-key
```

### 백엔드 (back/.env)

```env
# 프론트엔드 URL
VSR_URL=http://localhost:3000  # 로컬 개발
# 또는
VSR_URL=https://your-frontend.vercel.app  # 프로덕션

# AssemblyAI (필수)
ASSEMBLYAI_API_KEY=your-assemblyai-api-key

# AWS S3 (필수)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads

# API 인증 (필수)
FRONTEND_API_KEY=your-frontend-api-key

# 선택 사항
OPENAI_API_KEY=your-key
LANGCHAIN_API_KEY=your-key
```

## API 엔드포인트

### 백엔드 (Railway)

- `POST /voice/generate-upload-url`: S3 Pre-signed URL 생성
- `POST /voice/process-s3-file`: S3 파일 처리 및 화자 구분
- `POST /voice/speaker-diarization-v2`: 직접 업로드 화자 구분 (레거시)
- `GET /metrics`: Prometheus 메트릭
- `GET /docs`: API 문서 (Swagger UI)

### 프론트엔드 (Next.js API Routes)

- `POST /api/upload-url`: Pre-signed URL 요청 (프록시)
- `POST /api/process-audio`: 오디오 처리 요청 (프록시)

## 문제 해결

### CORS 오류
- 백엔드의 `VSR_URL` 환경 변수 확인
- 프론트엔드 URL과 정확히 일치하는지 확인
- S3 CORS 설정 확인 ([S3_SETUP.md](./S3_SETUP.md) 참조)

### API 연결 오류
- 프론트엔드의 `BACKEND_URL` 확인
- Railway 백엔드가 정상 실행 중인지 확인
- `FRONTEND_API_KEY`가 양쪽에 동일하게 설정되었는지 확인

### "Request Entity Too Large" 오류
- ✅ **해결됨!** S3 Pre-signed URL 방식 사용
- Vercel 4.5MB 제한 우회

### S3 업로드 오류
- AWS 액세스 키 확인
- S3 버킷 이름 확인
- IAM 권한 확인 ([S3_SETUP.md](./S3_SETUP.md) 참조)

### AssemblyAI 오류
- API 키 확인
- 크레딧 잔액 확인
- 지원되는 오디오 형식인지 확인

## 아키텍처

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ 1. Pre-signed URL 요청
       ↓
┌─────────────────────┐
│  Next.js (Vercel)   │
│  API Routes         │
└──────┬──────────────┘
       │ 2. API Key 인증
       ↓
┌─────────────────────┐      ┌──────────────┐
│  FastAPI (Railway)  │ ───→ │  AWS S3      │
│  - Pre-signed URL   │      │  (Storage)   │
│  - AssemblyAI       │      └──────────────┘
└─────────────────────┘
       ↑
       │ 3. S3에서 다운로드 & 처리
       │
┌──────────────┐
│ AssemblyAI   │
│ (STT + Diar) │
└──────────────┘
```

### 데이터 흐름

1. **프론트엔드** → Next.js API Route: Pre-signed URL 요청
2. **Next.js** → Railway (API 키 인증): Pre-signed URL 생성 요청
3. **Railway** → S3: Pre-signed URL 생성
4. **프론트엔드** → S3: 파일 직접 업로드 (Vercel 우회!)
5. **프론트엔드** → Next.js API Route: 처리 요청 (S3 키 전달)
6. **Next.js** → Railway (API 키 인증): S3 파일 처리 요청
7. **Railway** → S3: 파일 다운로드
8. **Railway** → AssemblyAI: 화자 구분 처리
9. **Railway** → 프론트엔드: 결과 반환

## 개발 로드맵

- [x] S3 Pre-signed URL 업로드
- [x] API 키 인증
- [x] AssemblyAI 통합
- [ ] 화자 이름 수동 지정 기능
- [ ] 대화 내용 편집 기능
- [ ] 다국어 지원
- [ ] Rate Limiting

## 라이선스

MIT
