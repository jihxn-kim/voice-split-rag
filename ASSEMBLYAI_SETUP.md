# AssemblyAI 설정 가이드

Google Cloud Speech에서 AssemblyAI로 마이그레이션되었습니다!

## ✅ 장점

- ✅ **더 나은 정확도** (특히 한국어)
- ✅ **간단한 API** (GCS 불필요)
- ✅ **빠른 처리**
- ✅ **저렴한 가격**

## 🚀 AssemblyAI API 키 발급

### 1단계: 계정 생성

1. [AssemblyAI](https://www.assemblyai.com/) 접속
2. **"Start Building for Free"** 클릭
3. 이메일로 가입 (또는 GitHub 로그인)

### 2단계: API 키 확인

1. 대시보드 로그인
2. 좌측 메뉴 → **"API Keys"** 또는 **"Settings"**
3. **API Key** 복사

예시:
```
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3단계: Railway 환경 변수 설정

Railway Dashboard → Variables 탭:

```env
# AssemblyAI API Key (필수!)
ASSEMBLYAI_API_KEY=your-assemblyai-api-key-here

# 프론트엔드 URL
VSR_URL=https://your-vercel-app.vercel.app

# 선택사항 (OpenAI 사용 시)
OPENAI_API_KEY=your-openai-key
```

**Google Cloud 관련 환경 변수는 모두 삭제하세요:**
- ~~GOOGLE_APPLICATION_CREDENTIALS_JSON~~
- ~~GOOGLE_CLOUD_PROJECT_ID~~
- ~~GCS_BUCKET_NAME~~
- ~~GOOGLE_CLOUD_LOCATION~~

## 💰 가격

### 무료 크레딧
- 신규 가입 시: **$50 무료 크레딧**
- 약 **5,000분** 처리 가능

### 유료 가격
- **$0.00025/초** = **$0.015/분** = **$0.90/시간**

### Google Cloud와 비교
| 서비스 | 가격 (시간당) | 무료 크레딧 |
|--------|--------------|-------------|
| AssemblyAI | $0.90 | $50 (5,000분) |
| Google Cloud | $1.44 | 60분/월 |

## 📝 지원되는 언어

- 한국어 (ko)
- 영어 (en)
- 스페인어 (es)
- 프랑스어 (fr)
- 독일어 (de)
- 이탈리아어 (it)
- 포르투갈어 (pt)
- 네덜란드어 (nl)
- 일본어 (ja)
- 중국어 (zh)
- 그 외 다수...

## 🎯 API 사용 예시

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

transcriber = aai.Transcriber()
config = aai.TranscriptionConfig(
    speaker_labels=True,
    language_code="ko"
)

transcript = transcriber.transcribe("audio.mp3", config)

for utterance in transcript.utterances:
    print(f"Speaker {utterance.speaker}: {utterance.text}")
```

## 🔧 마이그레이션 완료 체크리스트

- [x] requirements.txt 업데이트
- [x] config/clients.py AssemblyAI 추가
- [x] config/dependencies.py 수정
- [x] voice/router.py 재작성
- [ ] AssemblyAI API 키 발급
- [ ] Railway 환경 변수 설정
- [ ] GitHub 푸시
- [ ] Railway 재배포 확인

## 📊 성능 비교

### Google Cloud Speech-to-Text
- 정확도: ⭐⭐⭐☆☆
- 속도: 보통
- 가격: 비쌈
- 설정: 복잡 (GCS 필요)

### AssemblyAI
- 정확도: ⭐⭐⭐⭐⭐
- 속도: 빠름
- 가격: 저렴
- 설정: 간단 (API 키만)

## 🎉 다음 단계

1. **AssemblyAI API 키 발급** (위 가이드 참조)
2. **Railway 환경 변수 설정**
   ```
   ASSEMBLYAI_API_KEY=your-key
   VSR_URL=https://your-vercel-app.vercel.app
   ```
3. **코드 푸시**
   ```bash
   git add .
   git commit -m "Migrate to AssemblyAI for better accuracy"
   git push
   ```
4. **Railway 자동 재배포 대기**
5. **테스트!**

## 📞 문제 해결

### API 키 오류
```
ASSEMBLYAI_API_KEY 환경 변수가 설정되지 않았습니다
```
→ Railway Variables에 `ASSEMBLYAI_API_KEY` 추가

### 지원되지 않는 언어
→ `language_code`를 확인하세요 (ko, en, es 등)

### 처리 시간 초과
→ AssemblyAI는 매우 빠르므로 거의 발생하지 않음

## 🔗 참고 링크

- [AssemblyAI 공식 문서](https://www.assemblyai.com/docs)
- [지원 언어 목록](https://www.assemblyai.com/docs/concepts/supported-languages)
- [가격 안내](https://www.assemblyai.com/pricing)

---

마이그레이션 완료! 🚀 이제 더 나은 성능을 경험하세요!
