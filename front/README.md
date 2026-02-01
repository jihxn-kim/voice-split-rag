# Voice Split RAG - 음성 화자 구분 애플리케이션

Next.js 기반의 음성 파일 화자 구분 웹 애플리케이션입니다.

## 기능

- 오디오 파일 업로드 (드래그 앤 드롭 또는 파일 선택)
- 화자 자동 구분 (Speaker Diarization)
- 화자별 발화 내용 표시
- 시간순 대화 내용 표시

## 기술 스택

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: CSS Modules
- **Deployment**: Vercel

## 시작하기

### 1. 의존성 설치

```bash
npm install
```

### 2. 환경 변수 설정

`.env.local` 파일을 생성하고 다음 내용을 추가하세요:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

프로덕션 환경에서는 실제 백엔드 API URL로 변경하세요.

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열어 확인하세요.

## 빌드

프로덕션 빌드를 생성하려면:

```bash
npm run build
```

빌드된 애플리케이션을 실행하려면:

```bash
npm start
```

## Vercel 배포

이 프로젝트는 Vercel에 최적화되어 있습니다.

### 배포 방법

1. GitHub에 프로젝트를 푸시합니다
2. [Vercel](https://vercel.com)에 로그인합니다
3. "New Project"를 클릭하고 GitHub 저장소를 선택합니다
4. Root Directory를 `front`로 설정합니다
5. 환경 변수 설정:
   - `NEXT_PUBLIC_API_BASE_URL`: 백엔드 API URL을 입력하세요
6. "Deploy"를 클릭합니다

또는 프로젝트 루트에 있는 `vercel.json` 파일을 사용하여 자동으로 설정할 수 있습니다.

### 환경 변수 설정 (Vercel Dashboard)

배포 후 Vercel 대시보드에서 다음 환경 변수를 설정하세요:

- `NEXT_PUBLIC_API_BASE_URL`: 프로덕션 백엔드 API URL

## 프로젝트 구조

```
front/
├── app/
│   ├── layout.tsx       # 루트 레이아웃
│   ├── page.tsx         # 메인 페이지
│   ├── page.css         # 페이지 스타일
│   └── globals.css      # 글로벌 스타일
├── public/              # 정적 파일
├── package.json
├── next.config.js
└── tsconfig.json
```

## 백엔드 API

이 프론트엔드는 다음 백엔드 API 엔드포인트를 사용합니다:

- `POST /voice/speaker-diarization-v2`: 화자 구분
- `POST /voice/speaker-diarization/split-audio`: 화자 구분 및 오디오 분할

백엔드 서버는 `back/` 디렉토리에서 실행됩니다.

## 라이선스

MIT
