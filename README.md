# Voice Split RAG

음성 파일의 화자를 자동으로 구분하고 분석하는 웹 애플리케이션입니다.

## 프로젝트 구조

```
voice-split-rag/
├── front/              # Next.js 프론트엔드
│   ├── app/           # Next.js App Router
│   └── package.json
├── back/              # FastAPI 백엔드
│   ├── app.py
│   └── requirements.txt
└── vercel.json        # Vercel 배포 설정
```

## 시작하기

### 프론트엔드 (Next.js)

```bash
cd front
npm install
npm run dev
```

자세한 내용은 [front/README.md](./front/README.md)를 참고하세요.

### 백엔드 (FastAPI)

```bash
cd back
pip install -r requirements.txt
python app.py
```

## Vercel 배포

1. GitHub에 프로젝트 푸시
2. Vercel에서 프로젝트 import
3. Root Directory를 `front`로 설정하거나 프로젝트 루트의 `vercel.json` 사용
4. 환경 변수 `NEXT_PUBLIC_API_BASE_URL` 설정
5. Deploy

## 기능

- 🎤 오디오 파일 업로드 (드래그 앤 드롭)
- 🔊 자동 화자 구분 (Speaker Diarization)
- 📝 화자별 발화 내용 표시
- ⏱️ 시간순 대화 내용 표시

## 기술 스택

**Frontend:**
- Next.js 15
- TypeScript
- CSS Modules

**Backend:**
- FastAPI
- Python

**Deployment:**
- Vercel (Frontend)

## 라이선스

MIT
