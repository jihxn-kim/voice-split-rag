# Voice Split RAG - Backend (FastAPI)

음성 파일 화자 구분 API 서버입니다.

## 기술 스택

- **Framework**: FastAPI
- **Language**: Python 3.11
- **Speech Processing**: Google Cloud Speech-to-Text
- **Audio Processing**: pydub, ffmpeg
- **Deployment**: Railway

## 기능

- 음성 파일 업로드 및 화자 구분 (Speaker Diarization)
- Google Cloud Speech API 연동
- 화자별 발화 내용 추출
- 시간순 대화 내용 생성
- Prometheus 메트릭 수집

## 로컬 개발 환경 설정

### 1. 의존성 설치

#### Python 패키지
```bash
pip install -r requirements.txt
```

#### ffmpeg 설치 (필수)
**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
[FFmpeg 공식 사이트](https://ffmpeg.org/download.html)에서 다운로드

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 프론트엔드 URL
VSR_URL=http://localhost:3000

# Google Cloud 설정 (필수)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
GCS_BUCKET_NAME=your-bucket-name

# OpenAI API (필요시)
OPENAI_API_KEY=your-openai-api-key

# LangSmith (필요시)
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=your-project-name
```

### 3. 개발 서버 실행

```bash
uvicorn app:app --reload --port 8000
```

API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

## Railway 배포 가이드

### 1. Railway 계정 생성

1. [Railway](https://railway.app)에 접속
2. GitHub 계정으로 로그인

### 2. 새 프로젝트 생성

1. Dashboard → "New Project"
2. "Deploy from GitHub repo" 선택
3. 저장소 선택

### 3. 프로젝트 설정

Railway가 자동으로 Python 프로젝트를 감지하지만, 루트 디렉토리를 설정해야 합니다:

1. Settings → "Root Directory" → `back` 입력
2. Deploy를 클릭하여 자동 배포 시작

### 4. 환경 변수 설정 (중요)

Railway Dashboard → Variables 탭에서 다음 환경 변수를 추가:

#### 필수 환경 변수

```env
VSR_URL=https://your-frontend-app.vercel.app
```

#### Google Cloud 설정 (필수)

**방법 1: Service Account Key (JSON)**

1. Google Cloud Console에서 Service Account Key 다운로드
2. JSON 파일 내용을 복사
3. Railway Variables에 추가:
   ```
   GOOGLE_APPLICATION_CREDENTIALS_JSON=<JSON 파일 전체 내용>
   ```
4. `app.py`에서 JSON 문자열을 파일로 저장하는 코드 추가 필요

**방법 2: 개별 환경 변수**

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

#### 선택 환경 변수

```env
OPENAI_API_KEY=your-openai-api-key
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=your-project-name
```

### 5. 배포 확인

1. Deployments 탭에서 배포 로그 확인
2. Settings → Domains에서 Public URL 확인
3. `https://your-app.railway.app/docs`로 API 문서 확인

### 6. 프론트엔드 환경 변수 업데이트

Vercel 대시보드에서 프론트엔드의 환경 변수를 업데이트하세요:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-app.railway.app
```

그 다음 Vercel에서 재배포하세요.

## Railway 설정 파일 설명

### `nixpacks.toml`
- Railway의 빌드 시스템 설정
- ffmpeg 자동 설치
- 실행 명령어 정의

### `Procfile`
- Railway 실행 명령어 (백업용)
- `uvicorn app:app --host 0.0.0.0 --port $PORT`

### `runtime.txt`
- Python 버전 지정 (3.11)

## API 엔드포인트

### `POST /voice/speaker-diarization-v2`
음성 파일의 화자를 구분합니다.

**Request:**
- `file`: 오디오 파일 (multipart/form-data)

**Response:**
```json
{
  "total_speakers": 2,
  "dialogue": "...",
  "full_transcript": "...",
  "speakers": [...]
}
```

### `POST /voice/speaker-diarization/split-audio`
화자를 구분하고 오디오를 분할합니다.

### `GET /metrics`
Prometheus 메트릭

## 문제 해결

### ffmpeg 오류
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```
→ Railway에서는 `nixpacks.toml`이 자동으로 ffmpeg를 설치합니다. 로컬에서는 수동 설치 필요.

### Google Cloud 인증 오류
```
google.auth.exceptions.DefaultCredentialsError
```
→ `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수를 확인하세요.

### CORS 오류
```
Access to fetch has been blocked by CORS policy
```
→ `VSR_URL` 환경 변수에 프론트엔드 URL이 정확히 설정되었는지 확인하세요.

### Railway 배포 타임아웃
- Railway는 기본적으로 실행 시간 제한이 없습니다.
- 하지만 긴 요청은 프록시 타임아웃이 발생할 수 있습니다 (5분)
- 매우 긴 오디오 파일은 백그라운드 작업으로 처리하는 것을 권장합니다.

## 프로젝트 구조

```
back/
├── app.py              # FastAPI 메인 애플리케이션
├── config/             # 설정 및 의존성
│   ├── clients.py
│   ├── dependencies.py
│   └── exception.py
├── voice/              # 음성 처리 라우터
│   └── router.py
├── requirements.txt    # Python 패키지
├── nixpacks.toml      # Railway 빌드 설정
├── Procfile           # 실행 명령어
├── runtime.txt        # Python 버전
└── .env.example       # 환경 변수 예시
```

## 라이선스

MIT
