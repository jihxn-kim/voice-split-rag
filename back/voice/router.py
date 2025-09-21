#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter
from config.dependencies import (
    get_openai_client,
    get_langsmith_client,
    get_google_speech_client,
    get_gcs_client,
    get_gcs_bucket_name
)
from fastapi import Depends, Body, UploadFile, File, Form, HTTPException
from openai import AsyncOpenAI
from logs.logging_util import LoggerSingleton
import logging
from google.cloud.speech_v1p1beta1 import SpeechClient, RecognitionConfig, RecognitionAudio
from google.cloud.speech_v1p1beta1.types import RecognitionConfig as RecognitionConfigTypes
from typing import Optional
from pydub import AudioSegment
from pydub.utils import which
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")

@router.post("/speech-to-text")
async def speech_to_text(
    client: AsyncOpenAI = Depends(get_openai_client),
    prompt: str = Body(..., embed=True)
):
    logger.info("speech-to-text")
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    logger.info(response.choices[0].message.content)
    return {"message": response.choices[0].message.content}


@router.post("/google-stt")
async def google_speech_to_text(
    file: UploadFile = File(...),
    language_code: str = Form("ko-KR"),
    client: SpeechClient = Depends(get_google_speech_client),
):
    """업로드된 오디오 파일을 Google Speech-to-Text로 변환합니다.

    지원 확장자: .wav, .flac, .mp3, .ogg, .opus
    """
    try:
        logger.info(f"/voice/google-stt called: filename={file.filename}, content_type={file.content_type}")

        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        filename = (file.filename or "").lower()

        # ffmpeg 확인
        if which("ffmpeg") is None and which("ffmpeg.exe") is None:
            raise HTTPException(status_code=500, detail="ffmpeg가 필요합니다. 환경변수 PATH에 ffmpeg를 추가하세요.")

        # pydub로 디코딩 (원본 포맷 자동 감지 실패 대비 확장자 맵핑)
        ext = None
        if "." in filename:
            ext = filename.rsplit(".", 1)[-1]
        ext_map = {
            "m4a": "mp4",
            "mp4": "mp4",
            "mp3": "mp3",
            "wav": "wav",
            "ogg": "ogg",
            "opus": "ogg",
            "flac": "flac",
        }
        src_format = ext_map.get(ext) if ext else None

        try:
            audio_seg = AudioSegment.from_file(BytesIO(audio_bytes), format=src_format)
        except Exception:
            # 포맷 미지정으로 재시도 (ffmpeg에 맡김)
            audio_seg = AudioSegment.from_file(BytesIO(audio_bytes))

        # 표준화: mono, 16kHz, 16-bit
        audio_seg = audio_seg.set_channels(1).set_frame_rate(16000).set_sample_width(2)

        # 5분(300초) 단위로 1차 분할
        chunk_ms = 300_000
        total_ms = len(audio_seg)
        chunks = []
        for start in range(0, total_ms, chunk_ms):
            end = min(start + chunk_ms, total_ms)
            chunks.append(audio_seg[start:end])

        # Google 인식 설정 (OGG_OPUS로 통일)
        config = RecognitionConfig(
            encoding=RecognitionConfigTypes.AudioEncoding.OGG_OPUS,
            language_code=language_code,
            enable_automatic_punctuation=True,
            audio_channel_count=1,
        )

        # 내부 헬퍼: 한 청크(AudioSegment)를 동기 STT API 한계에 맞춰 서브분할(<=58초) + 10MB 체크 후 인식
        def _transcribe_chunk(seg: AudioSegment) -> str:
            # 먼저 전체 청크로 인코딩해보고, 필요 시 시간/용량 조건으로 분해
            buf_all = BytesIO()
            seg.export(buf_all, format="ogg", codec="libopus", bitrate="64k")
            ogg_all = buf_all.getvalue()

            needs_split_duration = len(seg) > 58_000
            needs_split_size = len(ogg_all) > 9_500_000

            transcripts: list[str] = []
            if needs_split_duration or needs_split_size:
                base_ms = 58_000 if needs_split_duration else len(seg)
                for sub_start in range(0, len(seg), base_ms):
                    sub_end = min(sub_start + base_ms, len(seg))
                    sub_seg = seg[sub_start:sub_end]
                    sub_buf = BytesIO()
                    sub_seg.export(sub_buf, format="ogg", codec="libopus", bitrate="64k")
                    sub_bytes = sub_buf.getvalue()

                    # 여전히 10MB를 넘는다면 더 잘게 분할
                    if len(sub_bytes) > 9_500_000 and len(sub_seg) > 5_000:
                        # 용량 비율 기반 동적 분할
                        factor = max(2, int(len(sub_bytes) / 9_000_000) + 1)
                        sub_sub_ms = max(5_000, int(len(sub_seg) / factor))
                        for s in range(0, len(sub_seg), sub_sub_ms):
                            e = min(s + sub_sub_ms, len(sub_seg))
                            b = BytesIO()
                            sub_seg[s:e].export(b, format="ogg", codec="libopus", bitrate="64k")
                            audio_part = RecognitionAudio(content=b.getvalue())
                            resp = client.recognize(config=config, audio=audio_part)
                            for r in resp.results:
                                if r.alternatives:
                                    transcripts.append(r.alternatives[0].transcript)
                    else:
                        audio_part = RecognitionAudio(content=sub_bytes)
                        resp = client.recognize(config=config, audio=audio_part)
                        for r in resp.results:
                            if r.alternatives:
                                transcripts.append(r.alternatives[0].transcript)
            else:
                audio_all = RecognitionAudio(content=ogg_all)
                resp = client.recognize(config=config, audio=audio_all)
                for r in resp.results:
                    if r.alternatives:
                        transcripts.append(r.alternatives[0].transcript)

            return " ".join(transcripts).strip()

        # 최대 5개까지 병렬 처리
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [loop.run_in_executor(executor, _transcribe_chunk, seg) for seg in chunks]
            chunk_results = await asyncio.gather(*tasks)

        transcript_text = " ".join(chunk_results).strip()
        logger.info(f"google-stt transcript: {transcript_text[:200]}")

        return {"text": transcript_text, "language_code": language_code}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("google-stt failed")
        raise HTTPException(status_code=500, detail=f"STT 처리 실패: {str(e)}")


@router.post("/google-stt/async")
async def google_speech_to_text_async(
    file: UploadFile = File(...),
    language_code: str = Form("ko-KR"),
    bucket_name: Optional[str] = Form(None),
    wait: bool = Form(False),
    speech_client: SpeechClient = Depends(get_google_speech_client),
    storage_client = Depends(get_gcs_client),
    default_bucket_name: Optional[str] = Depends(get_gcs_bucket_name),
):
    """긴 오디오를 GCS에 업로드한 뒤 long_running_recognize로 비동기 인식합니다.

    - bucket_name 미지정 시 환경변수 GCS_BUCKET_NAME 사용
    - wait=true면 완료까지 대기 후 결과 반환, 아니면 operation 이름만 반환
    """
    try:
        logger.info(f"/voice/google-stt/async called: filename={file.filename}, wait={wait}")

        # 버킷 결정
        # 우선순위: 요청 파라미터 > 컨테이너 기본값 > 환경변수
        bucket = bucket_name or default_bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not bucket:
            raise HTTPException(status_code=400, detail="bucket_name 또는 GCS_BUCKET_NAME이 필요합니다.")

        # 파일 읽기
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        # 업로드 객체명
        safe_name = (file.filename or "audio").replace(" ", "_")
        object_name = f"uploads/{int(asyncio.get_event_loop().time()*1000)}_{safe_name}"

        # 업로드
        bucket_ref = storage_client.bucket(bucket)
        blob = bucket_ref.blob(object_name)
        blob.upload_from_string(data)

        gcs_uri = f"gs://{bucket}/{object_name}"
        logger.info(f"Uploaded to {gcs_uri}")

        # 인식 설정 (GCS는 형식 자동 감지 가능. 필요시 encoding 지정 가능)
        config = RecognitionConfig(
            language_code=language_code,
            enable_automatic_punctuation=True,
        )
        audio = {"uri": gcs_uri}

        operation = speech_client.long_running_recognize(config=config, audio=audio)

        if not wait:
            return {"operation": operation.operation.name, "gcs_uri": gcs_uri}

        # 완료까지 대기
        result = operation.result(timeout=14400)  # 최대 4시간 대기
        transcripts = []
        for r in result.results:
            if r.alternatives:
                transcripts.append(r.alternatives[0].transcript)

        return {"text": " ".join(transcripts).strip(), "gcs_uri": gcs_uri}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("google-stt/async failed")
        raise HTTPException(status_code=500, detail=f"Async STT 처리 실패: {str(e)}")