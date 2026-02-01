# 🔒 보안 설정 가이드

AssemblyAI 크레딧 보호를 위한 API 키 인증이 추가되었습니다!

## 🎯 보안 문제와 해결책

### ❌ 이전 문제

```bash
# 누구나 우리 백엔드를 직접 호출 가능!
curl -X POST https://voice-split-rag-production.up.railway.app/voice/... \
  -F "file=@audio.mp3"

→ 우리 AssemblyAI 크레딧 소진! 💸
```

### ✅ 해결 방법

**프론트엔드 ↔ 백엔드 간 API 키 인증**

```
클라이언트 → Next.js API Route → Railway (API 키 검증) → AssemblyAI
```

---

## 🔧 환경 변수 설정

### 1. API 키 생성

강력한 랜덤 키를 생성하세요:

```bash
# 터미널에서 실행
openssl rand -hex 32
```

출력 예시:
```
a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

### 2. Railway 환경 변수 (백엔드)

Railway → Variables 탭:

```env
# 프론트엔드 인증 키 (새로 추가!)
FRONTEND_API_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# AssemblyAI 키
ASSEMBLYAI_API_KEY=your-assemblyai-key

# CORS 설정
VSR_URL=https://your-vercel-app.vercel.app
```

### 3. Vercel 환경 변수 (프론트엔드)

Vercel → Settings → Environment Variables:

```env
# 백엔드 URL (NEXT_PUBLIC 제거!)
BACKEND_URL=https://voice-split-rag-production.up.railway.app

# 프론트엔드 API 키 (동일한 값!)
FRONTEND_API_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**중요:** `NEXT_PUBLIC_` 없이 설정! (클라이언트에 노출 안 됨)

**Environment 모두 체크:**
- ✅ Production
- ✅ Preview
- ✅ Development

---

## 🔐 보안 계층

### 레벨 1: 브라우저 CORS
```
https://other-site.com → Railway
❌ CORS 차단
```

### 레벨 2: API 키 검증 (신규!)
```
Postman/curl → Railway
❌ X-API-Key 헤더 검증 실패 → 401 Unauthorized
```

### 레벨 3: AssemblyAI 키
```
Railway 백엔드에만 존재
❌ 외부 노출 불가
```

---

## 📝 변경된 파일

### 백엔드
- `back/voice/router.py`: API 키 검증 추가

### 프론트엔드
- `front/app/api/diarize/route.ts`: Next.js API Route 생성 (NEW!)
- `front/app/page.tsx`: API Route 호출로 변경

---

## ✅ 테스트

### 1. 정상 동작 확인

프론트엔드에서 파일 업로드 → 정상 작동

### 2. 무단 접근 차단 확인

```bash
# API 키 없이 호출
curl -X POST https://voice-split-rag-production.up.railway.app/voice/speaker-diarization-v2 \
  -F "file=@audio.mp3"

# 응답:
# {"detail":"Invalid API Key"}
# Status: 400
```

```bash
# 잘못된 API 키로 호출
curl -X POST https://voice-split-rag-production.up.railway.app/voice/speaker-diarization-v2 \
  -H "X-API-Key: wrong-key" \
  -F "file=@audio.mp3"

# 응답:
# {"detail":"Invalid API Key"}
# Status: 400
```

---

## 💡 추가 보안 옵션 (선택사항)

### Rate Limiting 추가

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("10/minute")  # 분당 10회 제한
@router.post("/speaker-diarization-v2")
```

### IP 화이트리스트

```python
ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",")

if request.client.host not in ALLOWED_IPS:
    raise BadRequest("IP not allowed")
```

---

## 🎉 완료!

이제 인증된 요청만 처리됩니다:

- ✅ CORS로 브라우저 보호
- ✅ API 키로 무단 접근 차단
- ✅ AssemblyAI 크레딧 보호

안전하게 서비스를 운영하세요! 🚀
