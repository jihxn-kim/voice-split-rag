#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter
from config.dependencies import (
    get_google_speech_client,
    get_gcs_client,
    get_gcs_bucket_name,
    get_openai_client,
)
from fastapi import Depends, UploadFile, File, Form, Body
from logs.logging_util import LoggerSingleton
import logging
from google.cloud.speech_v1p1beta1 import SpeechClient, RecognitionConfig
from google.cloud.speech_v1p1beta1.types import SpeakerDiarizationConfig
from typing import Optional
import asyncio
import os
from openai import AsyncOpenAI
from config.exception import BadRequest, InternalError, AppException

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")

@router.post("/ai-chat")
async def speech_to_text(
    client: AsyncOpenAI = Depends(get_openai_client),
    prompt: str = Body(..., embed=True)
):
    logger.info("ai-chat")
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    logger.info(response.choices[0].message.content)
    return {"message": response.choices[0].message.content}

@router.post("/speaker-diarization")
async def speaker_diarization(
    file: UploadFile = File(...),
    language_code: str = Form("ko-KR"),
    min_speaker_count: int = Form(2),
    max_speaker_count: int = Form(10),
    delete_after_process: bool = Form(True),
    speech_client: SpeechClient = Depends(get_google_speech_client),
    storage_client = Depends(get_gcs_client),
    default_bucket_name: Optional[str] = Depends(get_gcs_bucket_name),
):
    """음성 파일에서 화자를 구분하여 각 화자별로 음성을 추출합니다.
    
    Args:
        file: 업로드된 오디오 파일
        language_code: 언어 코드 (기본값: ko-KR)
        min_speaker_count: 최소 화자 수 (기본값: 2)
        max_speaker_count: 최대 화자 수 (기본값: 10)
    """
    try:
        logger.info(f"/voice/speaker-diarization called: filename={file.filename}")
        
        # 버킷 결정
        bucket = default_bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not bucket:
            raise BadRequest("GCS_BUCKET_NAME이 필요합니다.")
        
        # 파일 읽기
        data = await file.read()
        if not data:
            raise BadRequest("빈 파일입니다.")
        
        # 업로드 객체명
        safe_name = (file.filename or "audio").replace(" ", "_")
        object_name = f"diarization/{int(asyncio.get_event_loop().time()*1000)}_{safe_name}"
        
        # GCS에 업로드
        bucket_ref = storage_client.bucket(bucket)
        blob = bucket_ref.blob(object_name)
        blob.upload_from_string(data)
        
        gcs_uri = f"gs://{bucket}/{object_name}"
        logger.info(f"Uploaded to {gcs_uri}")
        
        # 화자 구분 설정
        speaker_diarization_config = SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=min_speaker_count,
            max_speaker_count=max_speaker_count,
        )
        
        # 인식 설정
        config = RecognitionConfig(
            language_code=language_code,
            enable_automatic_punctuation=True,
            diarization_config=speaker_diarization_config,
        )
        audio = {"uri": gcs_uri}
        
        # 비동기 인식 실행
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        result = operation.result(timeout=14400)  # 최대 4시간 대기
        
        # 결과 처리
        speakers = {}
        # 시간 순 단어 리스트 수집 (세그먼트 생성을 위해)
        words_all: list[dict] = []
        for result_item in result.results:
            if result_item.alternatives:
                words = result_item.alternatives[0].words
                for word_info in words:
                    speaker_tag = word_info.speaker_tag
                    start_s = word_info.start_time.total_seconds() if word_info.start_time else 0
                    end_s = word_info.end_time.total_seconds() if word_info.end_time else 0

                    words_all.append({
                        "speaker_id": speaker_tag,
                        "word": word_info.word,
                        "start_time": start_s,
                        "end_time": end_s,
                    })

                    if speaker_tag not in speakers:
                        speakers[speaker_tag] = {
                            "speaker_id": speaker_tag,
                            "words": [],
                            "start_time": start_s,
                            "end_time": end_s,
                        }

                    speakers[speaker_tag]["words"].append({
                        "word": word_info.word,
                        "start_time": start_s,
                        "end_time": end_s,
                        "confidence": word_info.confidence,
                    })

                    # 전체 발화 시간 업데이트
                    speakers[speaker_tag]["start_time"] = min(speakers[speaker_tag]["start_time"], start_s)
                    speakers[speaker_tag]["end_time"] = max(speakers[speaker_tag]["end_time"], end_s)
        
        # 각 화자별 텍스트 생성
        for speaker_id, speaker_data in speakers.items():
            speaker_data["text"] = " ".join([word["word"] for word in speaker_data["words"]])
            speaker_data["duration"] = speaker_data["end_time"] - speaker_data["start_time"]
        
        # 화자별로 정렬 (시작 시간 기준)
        sorted_speakers = sorted(speakers.values(), key=lambda x: x["start_time"])
        
        # 전체 대화 텍스트 생성
        full_transcript = " ".join([speaker["text"] for speaker in sorted_speakers])

        # 시간 순 세그먼트 생성 (연속된 동일 화자 단위로 병합)
        segments: list[dict] = []
        if words_all:
            current = {
                "speaker_id": words_all[0]["speaker_id"],
                "start_time": words_all[0]["start_time"],
                "end_time": words_all[0]["end_time"],
                "text_parts": [words_all[0]["word"]],
            }
            for w in words_all[1:]:
                if w["speaker_id"] == current["speaker_id"]:
                    current["end_time"] = w["end_time"]
                    current["text_parts"].append(w["word"])
                else:
                    segments.append({
                        "speaker_id": current["speaker_id"],
                        "start_time": current["start_time"],
                        "end_time": current["end_time"],
                        "duration": current["end_time"] - current["start_time"],
                        "text": " ".join(current["text_parts"]).strip(),
                    })
                    current = {
                        "speaker_id": w["speaker_id"],
                        "start_time": w["start_time"],
                        "end_time": w["end_time"],
                        "text_parts": [w["word"]],
                    }
            # 마지막 세그먼트 flush
            segments.append({
                "speaker_id": current["speaker_id"],
                "start_time": current["start_time"],
                "end_time": current["end_time"],
                "duration": current["end_time"] - current["start_time"],
                "text": " ".join(current["text_parts"]).strip(),
            })

        # 사용자가 보기 쉬운 대화 문자열 생성
        dialogue = "\n".join([f"발화자 {seg['speaker_id']}: {seg['text']}" for seg in segments])
        
        # 처리 후 원본 업로드 객체 삭제 옵션
        deleted_source = False
        if delete_after_process:
            try:
                blob.delete()
                logger.info(f"Deleted source object: {gcs_uri}")
                deleted_source = True
            except Exception:
                logger.exception("failed to delete uploaded object after process")
                deleted_source = False

        logger.info(f"Speaker diarization completed: {len(speakers)} speakers detected")
        
        return {
            "gcs_uri": gcs_uri,
            "total_speakers": len(speakers),
            "full_transcript": full_transcript,
            "speakers": sorted_speakers,
            "segments": segments,
            "dialogue": dialogue,
            "deleted_source": deleted_source,
        }
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("speaker-diarization failed")
        raise InternalError(f"화자 구분 처리 실패: {str(e)}")


# (불필요한 STT 엔드포인트들은 제거되었습니다)