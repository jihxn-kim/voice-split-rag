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
    get_google_speech_v2_client,
    get_speech_v2_recognizer,
)
from fastapi import Depends, UploadFile, File, Form, Body
from logs.logging_util import LoggerSingleton
import logging
from google.cloud.speech_v1p1beta1 import SpeechClient, RecognitionConfig
from google.cloud.speech_v1p1beta1.types import SpeakerDiarizationConfig
from google.cloud import speech_v2
from typing import Optional
import asyncio
import os
from openai import AsyncOpenAI
from config.exception import BadRequest, InternalError, AppException
from io import BytesIO
from pydub import AudioSegment

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
    blob = None
    gcs_uri = None
    process_succeeded = False
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

        # 오디오를 WAV(PCM LINEAR16, 16kHz, mono)로 변환
        try:
            audio_seg = AudioSegment.from_file(BytesIO(data))
            audio_seg = audio_seg.set_channels(1).set_frame_rate(16000)
            wav_buffer = BytesIO()
            audio_seg.export(wav_buffer, format="wav")
            converted_bytes = wav_buffer.getvalue()
            wav_buffer.close()
        except Exception:
            logger.exception("audio conversion failed")
            raise BadRequest("지원되지 않는 오디오 형식입니다. WAV/FLAC/MP3/OGG 업로드 또는 ffmpeg 설치가 필요합니다.")

        # 업로드 객체명 (확장자 .wav로 저장)
        safe_name = (file.filename or "audio").replace(" ", "_")
        base_name, _ = os.path.splitext(safe_name)
        object_name = f"diarization/{int(asyncio.get_event_loop().time()*1000)}_{base_name}.wav"

        # GCS에 업로드
        bucket_ref = storage_client.bucket(bucket)
        blob = bucket_ref.blob(object_name)
        blob.upload_from_string(converted_bytes, content_type="audio/wav")

        gcs_uri = f"gs://{bucket}/{object_name}"
        logger.info(f"Uploaded to {gcs_uri} (converted to WAV LINEAR16 16kHz mono)")
        
        # 화자 구분 설정 (v1)
        speaker_diarization_config = SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=min_speaker_count,
            max_speaker_count=max_speaker_count,
        )
        
        # 인식 설정 (v1)
        config = RecognitionConfig(
            language_code=language_code,
            enable_automatic_punctuation=True,
            diarization_config=speaker_diarization_config,
            encoding=RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
            enable_word_time_offsets=True,
        )
        audio = {"uri": gcs_uri}
        
        # 비동기 인식 실행 (v1)
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        result = await asyncio.to_thread(operation.result, 14400)
        
        # 결과 처리: 화자 분리 단어는 마지막 result에 누적되어 제공되므로 마지막 것만 사용
        speakers = {}
        words_all: list[dict] = []
        diarized_words = []
        for result_item in result.results:
            if getattr(result_item, "alternatives", None) and result_item.alternatives and result_item.alternatives[0].words:
                diarized_words = result_item.alternatives[0].words

        # 안전장치: 혹시 마지막 결과에 words가 없으면 전체를 순회하여 수집
        if not diarized_words:
            for result_item in result.results:
                if getattr(result_item, "alternatives", None) and result_item.alternatives and result_item.alternatives[0].words:
                    diarized_words.extend(result_item.alternatives[0].words)

        for word_info in diarized_words:
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
            # 혹시 정렬이 어긋난 경우를 대비해 시작시간 기준 정렬
            words_all.sort(key=lambda x: x["start_time"]) 
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
        process_succeeded = True
        
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
    finally:
        # 처리 도중 예외가 발생한 경우, 업로드된 원본 객체를 정리
        if not process_succeeded and blob is not None:
            try:
                blob.delete()
                if gcs_uri:
                    logger.info(f"Deleted source object after failure: {gcs_uri}")
            except Exception:
                logger.exception("failed to delete uploaded object after failure")


@router.post("/speaker-diarization-v2")
async def speaker_diarization_v2(
    file: UploadFile = File(...),
    language_code: str = Form("ko-KR"),
    min_speaker_count: int = Form(2),
    max_speaker_count: int = Form(10),
    delete_after_process: bool = Form(True),
    storage_client = Depends(get_gcs_client),
    default_bucket_name: Optional[str] = Depends(get_gcs_bucket_name),
    v2_client = Depends(get_google_speech_v2_client),
    recognizer_path: Optional[str] = Depends(get_speech_v2_recognizer),
):
    """Speech-to-Text v2(Chirp 3)로 화자 구분 수행"""
    blob = None
    gcs_uri = None
    process_succeeded = False
    try:
        logger.info(f"/voice/speaker-diarization-v2 called: filename={file.filename}")

        bucket = default_bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not bucket:
            raise BadRequest("GCS_BUCKET_NAME이 필요합니다.")

        data = await file.read()
        if not data:
            raise BadRequest("빈 파일입니다.")

        try:
            audio_seg = AudioSegment.from_file(BytesIO(data))
            audio_seg = audio_seg.set_channels(1).set_frame_rate(16000)
            wav_buffer = BytesIO()
            audio_seg.export(wav_buffer, format="wav")
            converted_bytes = wav_buffer.getvalue()
            wav_buffer.close()
        except Exception:
            logger.exception("audio conversion failed")
            raise BadRequest("지원되지 않는 오디오 형식입니다. WAV/FLAC/MP3/OGG 업로드 또는 ffmpeg 설치가 필요합니다.")

        safe_name = (file.filename or "audio").replace(" ", "_")
        base_name, _ = os.path.splitext(safe_name)
        object_name = f"diarization/{int(asyncio.get_event_loop().time()*1000)}_{base_name}.wav"

        bucket_ref = storage_client.bucket(bucket)
        blob = bucket_ref.blob(object_name)
        blob.upload_from_string(converted_bytes, content_type="audio/wav")
        gcs_uri = f"gs://{bucket}/{object_name}"

        if not recognizer_path:
            raise BadRequest("SPEECH_V2_RECOGNIZER 또는 PROJECT_ID가 필요합니다.")

        request = {
            "recognizer": recognizer_path,
            "config": {
                "auto_decoding_config": {},
                "language_codes": [language_code],
                "features": {
                    "enable_automatic_punctuation": True,
                    "enable_word_time_offsets": True,
                    "diarization_config": {
                        "min_speaker_count": min_speaker_count,
                        "max_speaker_count": max_speaker_count,
                    },
                },
            },
            "uri": gcs_uri,
        }

        response = await asyncio.to_thread(v2_client.recognize, request=request)

        speakers = {}
        words_all: list[dict] = []
        diarized_words = []
        for result_item in getattr(response, "results", []) or []:
            alternatives = getattr(result_item, "alternatives", []) or []
            if alternatives and getattr(alternatives[0], "words", None):
                diarized_words = alternatives[0].words

        if not diarized_words:
            for result_item in getattr(response, "results", []) or []:
                alternatives = getattr(result_item, "alternatives", []) or []
                if alternatives and getattr(alternatives[0], "words", None):
                    diarized_words.extend(alternatives[0].words)

        for word_info in diarized_words:
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

            speakers[speaker_tag]["start_time"] = min(speakers[speaker_tag]["start_time"], start_s)
            speakers[speaker_tag]["end_time"] = max(speakers[speaker_tag]["end_time"], end_s)

        for speaker_id, speaker_data in speakers.items():
            speaker_data["text"] = " ".join([word["word"] for word in speaker_data["words"]])
            speaker_data["duration"] = speaker_data["end_time"] - speaker_data["start_time"]

        sorted_speakers = sorted(speakers.values(), key=lambda x: x["start_time"])
        full_transcript = " ".join([speaker["text"] for speaker in sorted_speakers])

        segments: list[dict] = []
        if words_all:
            words_all.sort(key=lambda x: x["start_time"]) 
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
            segments.append({
                "speaker_id": current["speaker_id"],
                "start_time": current["start_time"],
                "end_time": current["end_time"],
                "duration": current["end_time"] - current["start_time"],
                "text": " ".join(current["text_parts"]).strip(),
            })

        dialogue = "\n".join([f"발화자 {seg['speaker_id']}: {seg['text']}" for seg in segments])

        deleted_source = False
        if delete_after_process and gcs_uri:
            try:
                blob.delete()
                logger.info(f"Deleted source object: {gcs_uri}")
                deleted_source = True
            except Exception:
                logger.exception("failed to delete uploaded object after process")
                deleted_source = False

        process_succeeded = True
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
        logger.exception("speaker-diarization-v2 failed")
        raise InternalError(f"화자 구분(v2) 처리 실패: {str(e)}")
    finally:
        if not process_succeeded and blob is not None:
            try:
                blob.delete()
                if gcs_uri:
                    logger.info(f"Deleted source object after failure: {gcs_uri}")
            except Exception:
                logger.exception("failed to delete uploaded object after failure")
