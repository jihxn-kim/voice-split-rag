#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter, Depends, UploadFile, File, Form, Body, Header
from config.dependencies import get_openai_client, get_assemblyai_api_key, get_s3_client, get_s3_bucket_name
from auth.dependencies import get_current_active_user
from models.user import User
from logs.logging_util import LoggerSingleton
import logging
from openai import AsyncOpenAI
from config.exception import BadRequest, InternalError, AppException
from pydantic import BaseModel
import assemblyai as aai
import tempfile
import os
import uuid
from datetime import datetime, timedelta

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")


# Pydantic 모델
class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "audio/mpeg"


class ProcessS3FileRequest(BaseModel):
    s3_key: str
    language_code: str = "ko"

@router.post("/generate-upload-url")
async def generate_upload_url(
    request: PresignedUrlRequest,
    current_user: User = Depends(get_current_active_user),
    s3_client = Depends(get_s3_client),
    bucket_name: str = Depends(get_s3_bucket_name),
):
    """S3 Pre-signed URL 생성
    
    Args:
        request: 파일명과 Content-Type
        current_user: 현재 로그인한 사용자 (JWT 인증)
    
    Returns:
        upload_url: S3 업로드 URL
        s3_key: S3 객체 키 (나중에 처리 요청할 때 사용)
    """
    try:
        logger.info(f"/voice/generate-upload-url called: filename={request.filename}, user_id={current_user.id}")
        
        if not s3_client:
            raise InternalError("S3 클라이언트가 초기화되지 않았습니다.")
        
        # 고유한 S3 키 생성 (날짜 + UUID + 원본 파일명)
        file_extension = os.path.splitext(request.filename)[1] or ".mp3"
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"uploads/{timestamp}-{unique_id}{file_extension}"
        
        # Pre-signed URL 생성 (15분 유효)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': request.content_type,
            },
            ExpiresIn=900  # 15분
        )
        
        logger.info(f"Pre-signed URL generated: s3_key={s3_key}")
        
        return {
            "upload_url": presigned_url,
            "s3_key": s3_key,
        }
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("generate-upload-url failed")
        raise InternalError(f"Pre-signed URL 생성 실패: {str(e)}")


@router.post("/ai-chat")
async def speech_to_text(
    client: AsyncOpenAI = Depends(get_openai_client),
    prompt: str = Body(..., embed=True)
):
    """OpenAI Chat API"""
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


@router.post("/process-s3-file")
async def process_s3_file(
    request: ProcessS3FileRequest,
    current_user: User = Depends(get_current_active_user),
    s3_client = Depends(get_s3_client),
    bucket_name: str = Depends(get_s3_bucket_name),
    api_key: str | None = Depends(get_assemblyai_api_key),
):
    """S3에 업로드된 파일을 다운로드하여 화자 구분 처리
    
    Args:
        request: S3 키와 언어 코드
        current_user: 현재 로그인한 사용자 (JWT 인증)
    
    Returns:
        화자 구분 결과
    """
    temp_file_path = None
    
    try:
        logger.info(f"/voice/process-s3-file called: s3_key={request.s3_key}, user_id={current_user.id}")
        
        if not api_key:
            raise BadRequest("ASSEMBLYAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        if not s3_client:
            raise InternalError("S3 클라이언트가 초기화되지 않았습니다.")
        
        # S3에서 파일 다운로드
        suffix = os.path.splitext(request.s3_key)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
        
        logger.info(f"Downloading from S3: s3://{bucket_name}/{request.s3_key}")
        s3_client.download_file(bucket_name, request.s3_key, temp_file_path)
        logger.info(f"File downloaded to: {temp_file_path}")
        
        # AssemblyAI 트랜스크라이버 설정
        transcriber = aai.Transcriber()
        
        # 트랜스크립션 설정
        config = aai.TranscriptionConfig(
            speaker_labels=True,  # 화자 구분 활성화
            language_code=request.language_code,  # 언어 설정
        )
        
        logger.info("Starting transcription with AssemblyAI...")
        
        # 트랜스크립션 실행 (동기 방식)
        transcript = transcriber.transcribe(temp_file_path, config)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise InternalError(f"AssemblyAI transcription failed: {transcript.error}")
        
        logger.info(f"Transcription completed: {len(transcript.utterances)} utterances")
        
        # 화자별 데이터 수집
        speakers = {}
        segments = []
        
        for utterance in transcript.utterances:
            speaker_id = utterance.speaker
            text = utterance.text
            start_time = utterance.start / 1000.0  # 밀리초 -> 초
            end_time = utterance.end / 1000.0
            
            # 세그먼트 추가 (시간순 대화)
            segments.append({
                "speaker_id": speaker_id,
                "text": text,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
            })
            
            # 화자별 데이터 수집
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "speaker_id": speaker_id,
                    "text": "",
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": 0,
                }
            
            speakers[speaker_id]["text"] += " " + text
            speakers[speaker_id]["end_time"] = max(speakers[speaker_id]["end_time"], end_time)
            speakers[speaker_id]["duration"] = speakers[speaker_id]["end_time"] - speakers[speaker_id]["start_time"]
        
        # 화자 텍스트 정리 (앞뒤 공백 제거)
        for speaker_id in speakers:
            speakers[speaker_id]["text"] = speakers[speaker_id]["text"].strip()
        
        # 화자별로 정렬 (시작 시간 기준)
        sorted_speakers = sorted(speakers.values(), key=lambda x: x["start_time"])
        
        # 전체 대화 텍스트
        full_transcript = transcript.text
        
        # 시간순 대화 문자열 생성
        dialogue = "\n".join([f"발화자 {seg['speaker_id']}: {seg['text']}" for seg in segments])
        
        logger.info(f"Speaker diarization completed: {len(speakers)} speakers detected")
        
        # S3에서 파일 삭제 (선택사항)
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=request.s3_key)
            logger.info(f"S3 file deleted: {request.s3_key}")
        except Exception as e:
            logger.warning(f"Failed to delete S3 file: {e}")
        
        return {
            "total_speakers": len(speakers),
            "full_transcript": full_transcript,
            "speakers": sorted_speakers,
            "segments": segments,
            "dialogue": dialogue,
        }
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("process-s3-file failed")
        raise InternalError(f"화자 구분 처리 실패: {str(e)}")
    finally:
        # 임시 파일 삭제
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"Temporary file deleted: {temp_file_path}")
            except Exception:
                logger.exception("Failed to delete temporary file")


@router.post("/speaker-diarization-v2")
async def speaker_diarization_v2(
    file: UploadFile = File(...),
    language_code: str = Form("ko"),
    min_speaker_count: int = Form(2),
    max_speaker_count: int = Form(10),
    x_api_key: str = Header(..., alias="X-API-Key"),
    api_key: str | None = Depends(get_assemblyai_api_key),
):
    """AssemblyAI를 사용한 화자 구분 및 음성 인식 (레거시 - 직접 업로드)
    
    Args:
        file: 업로드된 오디오 파일
        language_code: 언어 코드 (ko, en 등)
        min_speaker_count: 최소 화자 수 (기본값: 2) - AssemblyAI는 사용 안 함
        max_speaker_count: 최대 화자 수 (기본값: 10) - AssemblyAI는 사용 안 함
    """
    temp_file_path = None
    
    try:
        logger.info(f"/voice/speaker-diarization-v2 called: filename={file.filename}")
        
        # API 키 검증 (프론트엔드 인증)
        expected_key = os.getenv("FRONTEND_API_KEY")
        if not expected_key:
            raise InternalError("FRONTEND_API_KEY가 설정되지 않았습니다.")
        
        if x_api_key != expected_key:
            logger.warning(f"Unauthorized access attempt with key: {x_api_key[:10]}...")
            raise BadRequest("Invalid API Key", code="UNAUTHORIZED")
        
        if not api_key:
            raise BadRequest("ASSEMBLYAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        # 파일 읽기
        data = await file.read()
        if not data:
            raise BadRequest("빈 파일입니다.")
        
        # 임시 파일로 저장 (AssemblyAI는 파일 경로 또는 URL 필요)
        suffix = os.path.splitext(file.filename or "audio.mp3")[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(data)
            temp_file_path = temp_file.name
        
        logger.info(f"Temporary file created: {temp_file_path}")
        
        # AssemblyAI 트랜스크라이버 설정
        transcriber = aai.Transcriber()
        
        # 트랜스크립션 설정
        config = aai.TranscriptionConfig(
            speaker_labels=True,  # 화자 구분 활성화
            language_code=language_code,  # 언어 설정
        )
        
        logger.info("Starting transcription with AssemblyAI...")
        
        # 트랜스크립션 실행 (동기 방식)
        transcript = transcriber.transcribe(temp_file_path, config)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise InternalError(f"AssemblyAI transcription failed: {transcript.error}")
        
        logger.info(f"Transcription completed: {len(transcript.utterances)} utterances")
        
        # 화자별 데이터 수집
        speakers = {}
        segments = []
        
        for utterance in transcript.utterances:
            speaker_id = utterance.speaker
            text = utterance.text
            start_time = utterance.start / 1000.0  # 밀리초 -> 초
            end_time = utterance.end / 1000.0
            
            # 세그먼트 추가 (시간순 대화)
            segments.append({
                "speaker_id": speaker_id,
                "text": text,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
            })
            
            # 화자별 데이터 수집
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "speaker_id": speaker_id,
                    "text": "",
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": 0,
                }
            
            speakers[speaker_id]["text"] += " " + text
            speakers[speaker_id]["end_time"] = max(speakers[speaker_id]["end_time"], end_time)
            speakers[speaker_id]["duration"] = speakers[speaker_id]["end_time"] - speakers[speaker_id]["start_time"]
        
        # 화자 텍스트 정리 (앞뒤 공백 제거)
        for speaker_id in speakers:
            speakers[speaker_id]["text"] = speakers[speaker_id]["text"].strip()
        
        # 화자별로 정렬 (시작 시간 기준)
        sorted_speakers = sorted(speakers.values(), key=lambda x: x["start_time"])
        
        # 전체 대화 텍스트
        full_transcript = transcript.text
        
        # 시간순 대화 문자열 생성
        dialogue = "\n".join([f"발화자 {seg['speaker_id']}: {seg['text']}" for seg in segments])
        
        logger.info(f"Speaker diarization completed: {len(speakers)} speakers detected")
        
        return {
            "total_speakers": len(speakers),
            "full_transcript": full_transcript,
            "speakers": sorted_speakers,
            "segments": segments,
            "dialogue": dialogue,
        }
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("speaker-diarization-v2 failed")
        raise InternalError(f"화자 구분 처리 실패: {str(e)}")
    finally:
        # 임시 파일 삭제
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"Temporary file deleted: {temp_file_path}")
            except Exception:
                logger.exception("Failed to delete temporary file")
