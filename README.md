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

- 🎤 오디오 파일 업로드 (드래그 앤 드롭)
- 🔊 자동 화자 구분 (Speaker Diarization)
- 📝 화자별 발화 내용 표시
- ⏱️ 시간순 대화 내용 표시
- 🎵 화자별 오디오 분할

## 기술 스택

**Frontend:**
- Next.js 15 (App Router)
- TypeScript
- CSS Modules

**Backend:**
- FastAPI
- Python 3.11
- Google Cloud Speech-to-Text
- pydub + ffmpeg

**Deployment:**
- Vercel (Frontend)
- Railway (Backend)

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

### 1단계: 백엔드 배포 (Railway)

#### Railway 프로젝트 생성
1. [Railway](https://railway.app)에 접속 및 로그인
2. "New Project" → "Deploy from GitHub repo"
3. 저장소 선택

#### 설정
1. **Root Directory**: `back` 설정
2. **환경 변수** 추가:
   ```env
   VSR_URL=https://your-frontend-app.vercel.app
   # Google Cloud 설정 추가
   ```
3. Deploy 시작

#### 배포 URL 확인
- Settings → Domains에서 Railway URL 확인
- 예: `https://your-backend.railway.app`

자세한 내용: [back/README.md](./back/README.md)

### 2단계: 프론트엔드 배포 (Vercel)

#### Vercel 프로젝트 생성
1. [Vercel](https://vercel.com)에 접속 및 로그인
2. "New Project" → GitHub 저장소 선택

#### 설정
1. **Root Directory**: `front` 설정
2. **Framework Preset**: Next.js (자동 감지)
3. **환경 변수** 추가:
   ```env
   NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app
   ```
4. Deploy 클릭

자세한 내용: [front/README.md](./front/README.md)

### 3단계: CORS 설정 업데이트

Railway에서 백엔드 환경 변수 업데이트:

```env
VSR_URL=https://your-actual-frontend.vercel.app
```

저장 후 Railway가 자동으로 재배포됩니다.

## 환경 변수 설정

### 프론트엔드 (front/.env.local)

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  # 로컬 개발
# 또는
NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app  # 프로덕션
```

### 백엔드 (back/.env)

```env
# 프론트엔드 URL
VSR_URL=http://localhost:3000  # 로컬 개발
# 또는
VSR_URL=https://your-frontend.vercel.app  # 프로덕션

# Google Cloud (필수)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCS_BUCKET_NAME=your-bucket-name

# 선택 사항
OPENAI_API_KEY=your-key
LANGCHAIN_API_KEY=your-key
```

## API 엔드포인트

- `POST /voice/speaker-diarization-v2`: 화자 구분
- `POST /voice/speaker-diarization/split-audio`: 화자 구분 + 오디오 분할
- `GET /metrics`: Prometheus 메트릭
- `GET /docs`: API 문서 (Swagger UI)

## 문제 해결

### CORS 오류
- 백엔드의 `VSR_URL` 환경 변수 확인
- 프론트엔드 URL과 정확히 일치하는지 확인

### API 연결 오류
- 프론트엔드의 `NEXT_PUBLIC_API_BASE_URL` 확인
- Railway 백엔드가 정상 실행 중인지 확인

### Google Cloud 인증 오류
- Service Account Key 파일 확인
- 환경 변수 설정 확인
- Railway에서는 JSON 문자열로 설정 필요

## 개발 로드맵

- [ ] 화자 이름 수동 지정 기능
- [ ] 화자별 오디오 다운로드 기능
- [ ] 대화 내용 편집 기능
- [ ] 다국어 지원
- [ ] 실시간 음성 처리

## 라이선스

MIT
