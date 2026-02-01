# AWS S3 설정 가이드

이 가이드는 Pre-signed URL 방식으로 대용량 오디오 파일을 업로드하기 위한 AWS S3 설정 방법을 설명합니다.

---

## 📋 목차

1. [AWS S3 버킷 생성](#1-aws-s3-버킷-생성)
2. [IAM 사용자 생성 및 권한 설정](#2-iam-사용자-생성-및-권한-설정)
3. [Railway 환경 변수 설정](#3-railway-환경-변수-설정)
4. [Vercel 환경 변수 설정](#4-vercel-환경-변수-설정)
5. [테스트](#5-테스트)

---

## 1. AWS S3 버킷 생성

### 1.1 AWS 콘솔 접속

1. [AWS Console](https://console.aws.amazon.com/)에 로그인
2. S3 서비스로 이동

### 1.2 버킷 생성

1. **"버킷 만들기"** 클릭
2. 다음 설정 입력:
   - **버킷 이름**: `voice-split-rag-uploads` (고유한 이름으로 변경 가능)
   - **AWS 리전**: `us-east-1` (또는 원하는 리전)
   - **퍼블릭 액세스 차단 설정**: 모두 체크 (기본값 유지)
     - ✅ 새 ACL(액세스 제어 목록)을 통해 부여된 버킷 및 객체에 대한 퍼블릭 액세스 차단
     - ✅ 임의의 ACL(액세스 제어 목록)을 통해 부여된 버킷 및 객체에 대한 퍼블릭 액세스 차단
     - ✅ 새 퍼블릭 버킷 또는 액세스 포인트 정책을 통해 부여된 버킷 및 객체에 대한 퍼블릭 액세스 차단
     - ✅ 임의의 퍼블릭 버킷 또는 액세스 포인트 정책을 통해 부여된 버킷 및 객체에 대한 퍼블릭 액세스 차단
   - **버킷 버전 관리**: 비활성화 (선택사항)
   - **기본 암호화**: 활성화 (SSE-S3 권장)

3. **"버킷 만들기"** 클릭

### 1.3 CORS 설정

1. 생성한 버킷 클릭
2. **"권한"** 탭 선택
3. **"CORS(Cross-Origin Resource Sharing)"** 섹션에서 **"편집"** 클릭
4. 다음 JSON 입력:

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "PUT",
            "POST",
            "GET"
        ],
        "AllowedOrigins": [
            "https://your-vercel-domain.vercel.app",
            "http://localhost:3000"
        ],
        "ExposeHeaders": [
            "ETag"
        ],
        "MaxAgeSeconds": 3000
    }
]
```

**⚠️ 중요:** `AllowedOrigins`에 실제 Vercel 도메인을 입력하세요!

5. **"변경 사항 저장"** 클릭

---

## 2. IAM 사용자 생성 및 권한 설정

### 2.1 IAM 콘솔 접속

1. AWS Console에서 **IAM** 서비스로 이동
2. 왼쪽 메뉴에서 **"사용자"** 클릭
3. **"사용자 추가"** 클릭

### 2.2 사용자 생성

1. **사용자 이름**: `voice-split-rag-s3-user`
2. **AWS 액세스 유형 선택**:
   - ✅ **액세스 키 - 프로그래밍 방식 액세스**
3. **"다음: 권한"** 클릭

### 2.3 권한 설정

1. **"기존 정책 직접 연결"** 선택
2. 검색창에 `S3` 입력
3. 다음 정책 중 하나 선택:
   - **추천**: 커스텀 정책 생성 (최소 권한 원칙)
   - **간단**: `AmazonS3FullAccess` (모든 S3 버킷 접근 가능)

### 2.4 커스텀 정책 생성 (추천)

1. **"정책 생성"** 클릭
2. **JSON** 탭 선택
3. 다음 JSON 입력:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::voice-split-rag-uploads/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::voice-split-rag-uploads"
        }
    ]
}
```

**⚠️ 중요:** `voice-split-rag-uploads`를 실제 버킷 이름으로 변경하세요!

4. **"정책 검토"** 클릭
5. **정책 이름**: `VoiceSplitRagS3Policy`
6. **"정책 생성"** 클릭

### 2.5 액세스 키 생성

1. 사용자 생성 완료 후 **"액세스 키 ID"**와 **"비밀 액세스 키"** 표시됨
2. **⚠️ 중요: 이 키는 다시 볼 수 없으므로 안전한 곳에 저장하세요!**
3. CSV 다운로드 또는 복사하여 저장

---

## 3. Railway 환경 변수 설정

Railway Dashboard → 프로젝트 → **Variables** 탭:

```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads

# 기존 환경 변수 (유지)
VSR_URL=https://your-vercel-domain.vercel.app
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
FRONTEND_API_KEY=your-frontend-api-key
```

**설정 방법:**
1. Railway Dashboard → 프로젝트 선택
2. **Variables** 탭 클릭
3. **New Variable** 클릭하여 각 환경 변수 추가
4. 자동으로 재배포됨

---

## 4. Vercel 환경 변수 설정

Vercel Dashboard → 프로젝트 → **Settings** → **Environment Variables**:

```env
# 백엔드 URL
BACKEND_URL=https://voice-split-rag-production.up.railway.app

# 프론트엔드 API 키
FRONTEND_API_KEY=your-frontend-api-key
```

**설정 방법:**
1. Vercel Dashboard → 프로젝트 선택
2. **Settings** → **Environment Variables**
3. 각 환경 변수 추가
4. **Production**, **Preview**, **Development** 모두 체크
5. **Save** 클릭
6. 재배포 필요 (Deployments → Redeploy)

---

## 5. 테스트

### 5.1 로컬 테스트

#### Backend (Railway)

1. `.env` 파일 생성:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-split-rag-uploads
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
FRONTEND_API_KEY=your-frontend-api-key
VSR_URL=http://localhost:3000
```

2. 서버 실행:

```bash
cd back
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

#### Frontend (Vercel)

1. `.env.local` 파일 생성:

```env
BACKEND_URL=http://localhost:8000
FRONTEND_API_KEY=your-frontend-api-key
```

2. 서버 실행:

```bash
cd front
npm install
npm run dev
```

3. 브라우저에서 `http://localhost:3000` 접속
4. 오디오 파일 업로드 테스트

### 5.2 프로덕션 테스트

1. Railway와 Vercel에 모두 배포 완료 확인
2. Vercel 도메인 접속
3. 대용량 오디오 파일 (5MB 이상) 업로드 테스트
4. 화자 구분 결과 확인

---

## 🔒 보안 체크리스트

- ✅ S3 버킷 퍼블릭 액세스 차단 활성화
- ✅ IAM 사용자는 최소 권한만 부여
- ✅ AWS 액세스 키는 환경 변수로만 관리 (코드에 하드코딩 금지)
- ✅ Pre-signed URL 만료 시간 설정 (15분)
- ✅ CORS 설정으로 허용된 도메인만 접근 가능
- ✅ FRONTEND_API_KEY로 Next.js ↔ Railway 인증
- ✅ 처리 완료 후 S3 파일 자동 삭제

---

## 💰 비용 예상

### AWS S3 (무료 티어 이후)

- **스토리지**: $0.023/GB/월
- **PUT 요청**: $0.005/1,000 요청
- **GET 요청**: $0.0004/1,000 요청

### 예상 비용 (월 100개 파일, 평균 10MB)

- 스토리지 (1GB): $0.023
- PUT (100회): $0.0005
- GET (200회): $0.00008
- **총: ~$0.02/월** (매우 저렴!)

**⚠️ 주의:** 파일을 삭제하지 않으면 스토리지 비용이 계속 증가합니다!

---

## 🛠️ 트러블슈팅

### 1. "Access Denied" 에러

**원인:** IAM 권한 부족

**해결:**
- IAM 정책에서 S3 버킷 ARN 확인
- `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` 권한 확인

### 2. CORS 에러

**원인:** S3 CORS 설정 문제

**해결:**
- S3 버킷 → 권한 → CORS 설정 확인
- `AllowedOrigins`에 Vercel 도메인 추가
- `AllowedMethods`에 `PUT` 포함 확인

### 3. "Signature Does Not Match" 에러

**원인:** AWS 액세스 키 불일치

**해결:**
- Railway 환경 변수에서 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` 재확인
- 공백이나 특수문자 포함 여부 확인

### 4. Pre-signed URL 만료

**원인:** 15분 이내에 업로드하지 않음

**해결:**
- 프론트엔드에서 파일 선택 후 즉시 업로드
- 백엔드에서 `ExpiresIn` 값 조정 (최대 7일)

---

## 📚 참고 자료

- [AWS S3 공식 문서](https://docs.aws.amazon.com/s3/)
- [Pre-signed URL 가이드](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [IAM 모범 사례](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [S3 CORS 설정](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html)

---

## ✅ 완료!

이제 대용량 오디오 파일을 S3를 통해 안전하게 업로드하고 처리할 수 있습니다! 🎉
