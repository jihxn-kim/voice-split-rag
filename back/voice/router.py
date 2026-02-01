#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, BackgroundTasks
from sqlalchemy.orm import Session
from config.dependencies import get_assemblyai_api_key, get_s3_client, get_s3_bucket_name, get_openai_client
from auth.dependencies import get_current_active_user
from models.user import User
from models.voice_record import VoiceRecord
from models.client import Client
from schemas.voice_record import VoiceRecordCreate, VoiceRecordResponse, VoiceRecordListResponse, VoiceRecordUpdate
from database import get_db
from logs.logging_util import LoggerSingleton
import logging
from config.exception import BadRequest, InternalError, AppException
from pydantic import BaseModel
from openai import AsyncOpenAI
import assemblyai as aai
import tempfile
import os
import uuid
import json
from datetime import datetime, timedelta

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")


async def analyze_first_session(db: Session, client: Client, dialogue: str, full_transcript: str):
    """1회기 상담 내용을 바탕으로 AI 분석 수행"""
    try:
        from config.clients import initialize_clients
        client_container = initialize_clients()
        
        if not client_container.openai_client:
            logger.warning("OpenAI client not available, skipping AI analysis")
            return
        
        # 상담 경력 텍스트 변환
        counseling_history = "있음" if client.has_previous_counseling else "없음"
        
        prompt = f"""
당신은 전문 심리 상담사입니다. 1회기 상담 내용을 바탕으로 내담자를 재평가해주세요.

## 내담자 초기 정보
- 이름: {client.name}
- 나이: {client.age}세
- 성별: {client.gender}
- 초기 상담신청배경: {client.consultation_background}
- 초기 주호소문제: {client.main_complaint}
- 상담이전경력: {counseling_history}
- 초기 증상(본인호소): {client.current_symptoms}

## 1회기 상담 내용
{dialogue}

## 요청사항
1회기 실제 상담 내용을 바탕으로 다음 3가지를 **전문적이고 상세하게** 재평가해주세요:

1. **상담신청 배경**: 1회기 상담을 통해 파악된 실제 상담신청 배경과 맥락을 전문적 관점에서 분석
2. **주호소문제**: 1회기 상담에서 드러난 주요 문제들을 심리학적 관점에서 체계적으로 정리
3. **현재 증상**: 1회기 상담에서 관찰되고 파악된 증상들을 구체적으로 기술

각 항목은 최소 3-4문장 이상으로 전문적이면서도 이해하기 쉽게 작성해주세요.
**중요**: 모든 값은 반드시 문자열(string) 형식으로 작성해주세요.

JSON 형식으로 응답:
{{
    "consultation_background": "1회기 기반 상담신청 배경 분석",
    "main_complaint": "1회기 기반 주호소문제 분석",
    "current_symptoms": "1회기 기반 현재 증상 분석"
}}
"""
        
        response = await client_container.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 임상심리 전문가이자 전문 상담사입니다. 1회기 상담 내용을 분석하여 내담자의 실제 상태를 정확히 파악합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # dict 타입의 값들을 JSON 문자열로 변환
        for key, value in result.items():
            if isinstance(value, dict):
                result[key] = json.dumps(value, ensure_ascii=False)
        
        # 클라이언트 정보 업데이트
        client.ai_consultation_background = result.get("consultation_background")
        client.ai_main_complaint = result.get("main_complaint")
        client.ai_current_symptoms = result.get("current_symptoms")
        client.ai_analysis_completed = True
        
        db.commit()
        logger.info(f"AI analysis completed for client_id={client.id}")
        
    except Exception as e:
        logger.error(f"AI analysis failed for client_id={client.id}: {str(e)}")
        # 분석 실패해도 음성 기록 자체는 유지


# Pydantic 모델
class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "audio/mpeg"


class ProcessS3FileRequest(BaseModel):
    s3_key: str
    client_id: int  # 내담자 ID (필수)
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
        current_user: 현재 로그인한 사용자 (JWT 인증 필수)
    
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


@router.post("/process-s3-file", response_model=VoiceRecordResponse)
async def process_s3_file(
    request: ProcessS3FileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    s3_client = Depends(get_s3_client),
    bucket_name: str = Depends(get_s3_bucket_name),
    api_key: str | None = Depends(get_assemblyai_api_key),
):
    """S3에 업로드된 파일을 다운로드하여 화자 구분 처리 및 DB 저장
    
    Args:
        request: S3 키, 내담자 ID, 언어 코드
        current_user: 현재 로그인한 사용자 (JWT 인증 필수)
        db: 데이터베이스 세션
    
    Returns:
        화자 구분 결과 및 저장된 기록
    """
    temp_file_path = None
    
    try:
        logger.info(f"/voice/process-s3-file called: s3_key={request.s3_key}, client_id={request.client_id}, user_id={current_user.id}")
        
        # 내담자가 현재 사용자의 것인지 확인
        client = db.query(Client).filter(
            Client.id == request.client_id,
            Client.user_id == current_user.id
        ).first()
        
        if not client:
            raise BadRequest(f"Client not found or unauthorized: client_id={request.client_id}")
        
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
            punctuate=True,  # 자동 구두점 (기본값: True)
            format_text=True,  # 텍스트 포맷팅 (숫자, 날짜 등)
            disfluencies=False,  # 필러 단어 제거 ("음", "어" 등) - False면 유지
            filter_profanity=False,  # 욕설 필터링 - 상담 분석용이므로 False
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
        
        # 총 길이 계산 (초)
        total_duration = int(segments[-1]["end_time"]) if segments else 0
        
        # 원본 파일명 추출
        original_filename = os.path.basename(request.s3_key)
        
        # 자동 제목 생성 (내담자 이름 + 날짜)
        auto_title = f"{client.name} - 상담 기록 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # DB에 저장
        voice_record = VoiceRecord(
            title=auto_title,
            user_id=current_user.id,
            client_id=request.client_id,
            s3_key=request.s3_key,
            original_filename=original_filename,
            total_speakers=len(speakers),
            full_transcript=full_transcript,
            speakers_data=sorted_speakers,
            segments_data=segments,
            dialogue=dialogue,
            language_code=request.language_code,
            duration=total_duration,
        )
        
        db.add(voice_record)
        db.commit()
        db.refresh(voice_record)
        
        logger.info(f"Voice record saved: id={voice_record.id}, user_id={current_user.id}")
        
        # 1회기 확인: 해당 내담자의 첫 번째 음성 기록인지 확인
        total_records = db.query(VoiceRecord).filter(VoiceRecord.client_id == request.client_id).count()
        
        if total_records == 1:
            # 1회기이면 백그라운드에서 AI 분석 수행
            logger.info(f"First session detected for client_id={request.client_id}, scheduling AI analysis")
            # 여기서는 동기적으로 처리 (간단한 방법)
            # 프로덕션에서는 Celery 등의 백그라운드 작업 큐 사용 권장
            await analyze_first_session(db, client, dialogue, full_transcript)
        
        return voice_record
        
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
            punctuate=True,  # 자동 구두점 (기본값: True)
            format_text=True,  # 텍스트 포맷팅 (숫자, 날짜 등)
            disfluencies=False,  # 필러 단어 제거 ("음", "어" 등) - False면 유지
            filter_profanity=False,  # 욕설 필터링 - 상담 분석용이므로 False
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
