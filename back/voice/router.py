#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from config.dependencies import get_openai_client, get_assemblyai_api_key
from logs.logging_util import LoggerSingleton
import logging
from openai import AsyncOpenAI
from config.exception import BadRequest, InternalError, AppException
import assemblyai as aai
import tempfile
import os

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")

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


@router.post("/speaker-diarization-v2")
async def speaker_diarization_v2(
    file: UploadFile = File(...),
    language_code: str = Form("ko"),
    min_speaker_count: int = Form(2),
    max_speaker_count: int = Form(10),
    api_key: str | None = Depends(get_assemblyai_api_key),
):
    """AssemblyAI를 사용한 화자 구분 및 음성 인식
    
    Args:
        file: 업로드된 오디오 파일
        language_code: 언어 코드 (ko, en 등)
        min_speaker_count: 최소 화자 수 (기본값: 2) - AssemblyAI는 사용 안 함
        max_speaker_count: 최대 화자 수 (기본값: 10) - AssemblyAI는 사용 안 함
    """
    temp_file_path = None
    
    try:
        logger.info(f"/voice/speaker-diarization-v2 called: filename={file.filename}")
        
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
