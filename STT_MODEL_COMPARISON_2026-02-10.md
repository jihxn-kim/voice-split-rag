# STT/화자분리/비언어 이벤트 모델 비교 (기준일: 2026-02-10)

## 범위
- 본 문서는 이번 대화에서 언급된 모델/서비스를 대상으로 최신 공개 문서 기준으로 비교합니다.
- 비교 대상: Speechmatics, Deepgram, AssemblyAI, RTZR VITO, NAVER CLOVA Speech, Mistral Voxtral Transcribe 2, Whisper, pyannote, YAMNet
- 주의: 공급사별 벤치마크 기준(데이터셋/평가셋/지표)이 달라 절대 수치의 단순 가로 비교는 왜곡될 수 있습니다.

## 통합 비교표

| 모델/서비스 | 최신 버전/라인업(확인) | 가격(공식 공개) | 한국어 STT | 화자분리 | 비언어 이벤트(웃음/울음) | 성능(공개 수치) | 비고 |
|---|---|---|---|---|---|---|---|
| **Speechmatics** | Standard / Enhanced (버전 번호 비공개), 55+ 언어 | Pro 플랜 `from $0.24/hr` (무료 480분/월) | 지원 (`ko`) | 지원 (speaker diarization) | **지원: music/laughter/applause** (추가요금 없음) / **울음은 명시 없음** | 한국어 전용 WER 공개치 확인 어려움. 한국어 제품 페이지에 `90% accuracy, <1s latency` 문구 존재(자체 주장) | 비언어 이벤트를 STT와 한 번에 처리 가능. 울음 탐지는 별도 모델 결합 권장 |
| **Deepgram (Nova-3)** | `nova-3` (최신 주력), `nova-2` 병행 | Pre-recorded PAYG: Nova-3 mono `$0.0043/min`, multi `$0.0052/min`; Streaming PAYG: mono `$0.0077/min`, multi `$0.0092/min`; diarization add-on `$0.0020/min` | 지원 (`ko`, `ko-KR`) | 지원 (`diarize=true`, all available languages) | 문서상 전용 오디오 이벤트 클래스(웃음/울음) 명시 확인 어려움 | Nova-3: 경쟁사 대비 WER 감소(Streaming 54.2%, Batch 47.4%) 자체 발표 | 한국어+화자분리는 강함. 웃음/울음은 별도 AED 필요 |
| **AssemblyAI** | `Universal-3-Pro` (최신), `Universal-2` fallback | Universal-3-Pro `$0.21/hr`, Universal-2 `$0.15/hr`, Universal-Streaming `$0.15/hr` | 직접 고정은 U2 fallback 필요 (`speech_models=[u3-pro,u2]`) | 지원 (`speaker_labels=true`) | Prompting으로 audio event tags 가능(예: laughter/music/applause/noise/cough/sigh). **울음은 예시 미명시** | 공개 벤치마크(2025-06, FLEURS): 한국어 WER `14.54%` | 한국어에서는 U2 fallback 경로 고려 필수 |
| **RTZR VITO OpenAPI** | `sommers`(기본), `whisper`(fine-tuned) | 누진 과금(일반/스트리밍 동일): T1 `1000원/시간`, T2 `500원/시간`, T3 `400원/시간`, T4 `300원/시간`; 무료 600분 | Sommers: `ko`,`ja` / Whisper: 다국어 | 지원 (`use_diarization`, `spk_count`) | 공식 문서상 웃음/울음 이벤트 API 항목 미확인 | 마케팅 페이지: 경쟁사 대비 오류율 35~46%↓, 속도 2.5x~30x(자체 주장) | 한국어 운영 친화적. 이벤트 탐지는 별도 모델 결합 필요 |
| **NAVER CLOVA Speech** | 장문/단문/스트리밍 API (응답 예시 엔진 버전: `ncp_v2_v2.3.0...`) | 화자분리 `15초당 2원`, 이벤트 탐지 `15초당 2원`, 동시 사용 시 `15초당 4원` (사용자 확인값 반영) | 지원 (`ko-KR`) | 지원 (`diarization.enable`) | 지원 (`sed.enable`, `events/eventTypes` 반환). 문서 예시는 `music`; 웃음/울음 라벨 목록은 명시 확인 어려움 | 공개 한국어 WER/DER 정량 테이블 확인 어려움 | 한국어 제품 적합성 높음. 이벤트 라벨 체계는 사전 PoC 필요 |
| **Mistral Voxtral Transcribe 2** | `voxtral-mini-2602` (batch), `voxtral-mini-transcribe-realtime-2602` (realtime, open-weights) | Batch `$0.003/min`, Realtime `$0.006/min` | 지원(13개 언어에 한국어 포함) | 지원 (`diarize`) / Realtime은 `diarize` 비호환 | 공식 문서상 웃음/울음 같은 오디오 이벤트 taxonomy 미확인 | 블로그 기준 FLEURS 약 `4% WER`(자체 발표), Realtime 지연 sub-200ms 구성 가능 | 가격 경쟁력 높음. 비언어 이벤트는 별도 AED 결합 필요 |
| **OpenAI Whisper (OSS)** | `turbo`(optimized large-v3), `large-v3` 등 | 모델 자체 무료(MIT, self-host) | 지원(다국어) | 미지원(단독으로는 diarization 없음) | 미지원(단독으로는 오디오 이벤트 분류 없음) | 공식: 언어별 성능 편차 큼, large-v3/large-v2 언어별 WER/CER 도표 제공 | STT 본체로 우수하나 화자/이벤트는 외부 결합 필요 |
| **pyannote (OSS/API)** | OSS `speaker-diarization-3.1`, 상용 `Precision-2` | OSS는 self-host 비용만 발생. pyannoteAI: Developer `€19/월`, Starter `€99/월`, 모델 과금 예시 `0.14€/h`(Precision-2), `0.035€/h`(Hosted Community-1) | STT 모델 아님 | **강점(화자분리 핵심 컴포넌트)** | 이벤트 분류 모델 아님 | v3.1 DER 예시: DIHARD3 21.7, AMI(IHM) 18.8, Earnings21 9.4 | Whisper/Deepgram/AssemblyAI와 조합해 화자분리 강화용으로 적합 |
| **YAMNet (TF Hub)** | `tfhub.dev/google/yamnet/1` | 무료(오픈소스/사전학습 모델) | STT 모델 아님 | 미지원 | **지원 가능(오디오 이벤트 분류): Laughter, Crying/Sobbing 클래스 포함** | AudioSet eval 기준 balanced mAP `0.306`; 3.7M weights; 69.2M multiplies/0.96s frame | 웃음/울음 보강용 컴포넌트. STT/diarization과 병렬 또는 후처리 결합 권장 |

## 핵심 해석
- **한국어 STT + 화자분리 + 비언어 이벤트까지 즉시 한 번에**는 현재 기준으로 Speechmatics와 CLOVA Speech가 가장 가까움.
- **울음(crying/sobbing)까지 명시적으로 다루려면** YAMNet(또는 동급 AED) 결합이 가장 안전함.
- Deepgram/VITO/Whisper는 한국어 STT·화자분리 축에서 강점이 있지만, 비언어 이벤트는 별도 모듈 결합이 현실적임.

## 빠른 비용 환산(참고)
- Speechmatics Pro 시작가: `$0.24/hr` ≈ `$0.004/min`
- AssemblyAI Universal-3-Pro: `$0.21/hr` ≈ `$0.0035/min`
- AssemblyAI Universal-2: `$0.15/hr` ≈ `$0.0025/min`
- Deepgram Nova-3 (batch mono): `$0.0043/min`
- RTZR T1: `1000원/시간` ≈ `16.67원/분`
- CLOVA 화자분리 + 이벤트 탐지: `15초당 4원` (각 2원 합산) = `분당 16원`
- Voxtral Mini Transcribe 2 (batch): `$0.003/min`
- Voxtral Realtime: `$0.006/min`

## 출처
- Speechmatics Pricing: https://www.speechmatics.com/pricing
- Speechmatics Audio Events: https://www.speechmatics.com/product/audio-events
- Speechmatics Korean page: https://www.speechmatics.com/speech-to-text/korean
- Deepgram Pricing: https://deepgram.com/pricing
- Deepgram Models & Languages: https://developers.deepgram.com/docs/models-languages-overview
- Deepgram Model Options: https://developers.deepgram.com/docs/model
- Deepgram Diarization: https://developers.deepgram.com/docs/diarization
- AssemblyAI Models/Pricing: https://www.assemblyai.com/docs/getting-started/models
- AssemblyAI Universal-3-Pro: https://www.assemblyai.com/docs/getting-started/universal-3-pro
- AssemblyAI Speaker Diarization: https://www.assemblyai.com/docs/pre-recorded-audio/speaker-diarization
- AssemblyAI Prompting (audio event tags): https://www.assemblyai.com/docs/pre-recorded-audio/prompting
- AssemblyAI Benchmarks: https://www.assemblyai.com/docs/evaluations/benchmarks
- RTZR Pricing: https://developers.rtzr.ai/docs/pricing/
- RTZR Batch STT model/diarization: https://developers.rtzr.ai/docs/en/stt-file/
- RTZR model docs: https://developers.rtzr.ai/docs/en/stt-file/model/
- RTZR diarization docs: https://developers.rtzr.ai/docs/en/stt-file/diarization/
- RTZR marketing claims: https://www.rtzr.ai/stt
- CLOVA Speech pricing snippet (Financial cloud): https://www.fin-ncloud.com/charge/region/ko
- CLOVA Speech API (local file): https://api.ncloud-docs.com/docs/en/ai-application-service-clovaspeech-longsentence-local
- CLOVA Speech API (external file): https://api.ncloud-docs.com/docs/en/ai-application-service-clovaspeech-longsentence-externalurl
- CLOVA Speech API (Object Storage/events): https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-longsentence
- Mistral Voxtral Transcribe 2 blog: https://mistral.ai/news/voxtral-transcribe-2
- Mistral Voxtral Mini Transcribe 2 model doc: https://docs.mistral.ai/models/voxtral-mini-transcribe-26-02
- Mistral Voxtral Realtime model doc: https://docs.mistral.ai/models/voxtral-mini-transcribe-realtime-26-02
- Mistral Audio & Transcription docs: https://docs.mistral.ai/capabilities/audio_transcription
- Voxtral Realtime open weights (HF): https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602
- OpenAI Whisper repo: https://github.com/openai/whisper
- Whisper paper: https://arxiv.org/abs/2212.04356
- pyannote pricing: https://www.pyannote.ai/pricing
- pyannote benchmark (v3.1): https://pypi.org/project/pyannote.audio/3.3.1/
- YAMNet tutorial: https://www.tensorflow.org/hub/tutorials/yamnet
- YAMNet code/perf notes: https://github.com/antonyharfield/tflite-models-audioset-yamnet
- YAMNet class examples (laughter/crying): https://www.tensorflow.org/tutorials/audio/transfer_learning_audio
- AudioSet Crying/Sobbing ontology: https://research.google.com/audioset/ontology/crying_sobbing.html

## 검증 메모
- CLOVA Speech 화자분리/이벤트 단가는 사용자 콘솔 확인값(각 `15초당 2원`)을 반영했습니다.
- 공급사별 성능 지표는 동일 실험 조건이 아니므로, 실제 의사결정은 반드시 동일 샘플셋 기반 PoC 재평가를 권장합니다.
