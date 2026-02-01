# 🚀 빠른 시작 가이드

S3 Pre-signed URL 방식으로 대용량 오디오 파일 업로드를 구현했습니다!

---

## ✅ 완료된 작업

1. ✅ Backend: boto3 설치 및 S3 클라이언트 설정
2. ✅ Backend: Pre-signed URL 생성 API 엔드포인트
3. ✅ Backend: S3에서 파일 다운로드 후 처리
4. ✅ Frontend: Next.js API Routes (upload-url, process-audio)
5. ✅ Frontend: S3 직접 업로드 로직
6. ✅ 문서 작성 (S3_SETUP.md)

---

## 📋 다음 단계

### 1. AWS S3 설정 (필수)

버킷은 이미 생성했으니, IAM 사용자와 액세스 키를 발급받으세요:

👉 **자세한 가이드**: [S3_SETUP.md](./S3_SETUP.md)

**필요한 정보:**
- AWS Access Key ID
- AWS Secret Access Key
- S3 Bucket Name
- AWS Region

---

### 2. Railway 환경 변수 추가

Railway Dashboard → 프로젝트 → **Variables** 탭:

```env
# 기존 환경 변수 (유지)
VSR_URL=https://your-vercel-domain.vercel.app
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
FRONTEND_API_KEY=your-frontend-api-key

# 새로 추가 (S3 관련)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads
```

**저장하면 자동으로 재배포됩니다!**

---

### 3. Vercel 환경 변수 (변경 없음)

기존 환경 변수 그대로 유지:

```env
BACKEND_URL=https://voice-split-rag-production.up.railway.app
FRONTEND_API_KEY=your-frontend-api-key
```

---

### 4. 로컬 테스트 (선택사항)

#### Backend

`back/.env` 파일 생성:

```env
VSR_URL=http://localhost:3000
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
FRONTEND_API_KEY=your-frontend-api-key
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads
```

실행:

```bash
cd back
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

#### Frontend

`front/.env.local` 파일 생성:

```env
BACKEND_URL=http://localhost:8000
FRONTEND_API_KEY=your-frontend-api-key
```

실행:

```bash
cd front
npm install
npm run dev
```

---

### 5. Git 푸시 및 배포

```bash
git add .
git commit -m "feat: S3 Pre-signed URL upload for large files"
git push
```

- **Railway**: 자동 재배포
- **Vercel**: 자동 재배포

---

## 🎯 테스트

1. Vercel 도메인 접속
2. **대용량 오디오 파일** (5MB 이상) 업로드
3. 화자 구분 결과 확인

**이제 "Request Entity Too Large" 에러가 나지 않습니다!** 🎉

---

## 🔒 보안 체크리스트

- ✅ S3 버킷 퍼블릭 액세스 차단
- ✅ IAM 최소 권한 설정
- ✅ Pre-signed URL 15분 만료
- ✅ CORS 도메인 제한
- ✅ FRONTEND_API_KEY 인증
- ✅ 처리 완료 후 S3 파일 자동 삭제

---

## 📊 아키텍처

```
프론트엔드 (Vercel)
    ↓ 1. Pre-signed URL 요청
Next.js API Route
    ↓ 2. API Key 인증
Railway Backend
    ↓ 3. Pre-signed URL 생성
AWS S3
    ↑ 4. 파일 직접 업로드 (Vercel 우회!)
프론트엔드
    ↓ 5. 처리 요청 (S3 키 전달)
Next.js API Route
    ↓ 6. API Key 인증
Railway Backend
    ↓ 7. S3에서 다운로드
AssemblyAI
    ↓ 8. 화자 구분
프론트엔드 (결과 표시)
```

---

## 💰 비용

### AWS S3 (무료 티어 이후)

월 100개 파일 (평균 10MB) 기준:
- 스토리지: $0.023
- PUT: $0.0005
- GET: $0.00008
- **총: ~$0.02/월** (매우 저렴!)

---

## 🛠️ 문제 해결

### S3 업로드 실패

**증상:** "Access Denied" 또는 "Signature Does Not Match"

**해결:**
1. Railway 환경 변수에서 AWS 키 확인
2. IAM 권한 확인 ([S3_SETUP.md](./S3_SETUP.md) 참조)
3. S3 버킷 이름 확인

### CORS 에러

**증상:** "CORS policy" 에러

**해결:**
1. S3 버킷 → 권한 → CORS 설정 확인
2. `AllowedOrigins`에 Vercel 도메인 추가
3. `AllowedMethods`에 `PUT` 포함 확인

---

## 📚 관련 문서

- [S3_SETUP.md](./S3_SETUP.md) - AWS S3 설정 가이드
- [SECURITY_SETUP.md](./SECURITY_SETUP.md) - API 키 인증 가이드
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 전체 배포 가이드
- [README.md](./README.md) - 프로젝트 개요

---

## ✨ 완료!

이제 대용량 오디오 파일을 안전하게 업로드하고 처리할 수 있습니다! 🚀
