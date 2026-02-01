#####################################################
#                                                   #
#                   STT 라우터 정의                   #
#                                                   #
#####################################################

from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from config.dependencies import get_assemblyai_api_key, get_s3_client, get_s3_bucket_name
from auth.dependencies import get_current_active_user
from models.user import User
from models.voice_record import VoiceRecord
from models.voice_upload import VoiceUpload
from models.client import Client
from database import get_db, SessionLocal
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
import asyncio
from datetime import datetime

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice", level=logging.INFO)

router = APIRouter(prefix="/voice")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP_LINES = 2
RAG_TOP_K = 4


def build_semantic_chunks(segments: list[dict]) -> list[str]:
    """발화 세그먼트를 문맥 단위로 묶어 청킹"""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for seg in segments:
        speaker = str(seg.get("speaker_id", "")).strip()
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        line = f"{speaker}: {text}" if speaker else text
        line_len = len(line)

        if current and current_len + line_len + 1 > CHUNK_MAX_CHARS:
            chunks.append("\n".join(current))
            if CHUNK_OVERLAP_LINES > 0:
                current = current[-CHUNK_OVERLAP_LINES:]
                current_len = sum(len(item) for item in current) + max(0, len(current) - 1)
            else:
                current = []
                current_len = 0

        current.append(line)
        current_len += line_len + (1 if current_len > 0 else 0)

    if current:
        chunks.append("\n".join(current))

    return chunks


def vector_to_pg(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"


def ensure_vector_tables(db: Session):
    try:
        db.execute(text(
            f"""
            CREATE TABLE IF NOT EXISTS voice_record_chunks (
                id SERIAL PRIMARY KEY,
                voice_record_id INTEGER NOT NULL REFERENCES voice_records(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                session_number INTEGER,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            );
            """
        ))
        db.execute(text(
            """
            CREATE INDEX IF NOT EXISTS voice_record_chunks_record_idx
            ON voice_record_chunks (voice_record_id);
            """
        ))
        db.execute(text(
            """
            CREATE INDEX IF NOT EXISTS voice_record_chunks_embedding_idx
            ON voice_record_chunks USING ivfflat (embedding vector_cosine_ops);
            """
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to ensure vector tables: {str(e)}")
        raise


async def embed_texts(openai_client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    batch_size = 32
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        response = await openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        embeddings.extend([item.embedding for item in response.data])
    return embeddings


async def build_rag_context(
    db: Session,
    openai_client: AsyncOpenAI,
    voice_record_id: int,
) -> list[str]:
    query_texts = [
        "상담신청 배경을 파악할 수 있는 발화",
        "내담자의 주호소문제와 핵심 어려움이 드러난 발화",
        "내담자의 현재 증상이나 상태를 설명한 발화",
    ]

    response = await openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query_texts,
    )

    contexts: list[str] = []
    seen: set[str] = set()

    for item in response.data:
        query_embedding = vector_to_pg(item.embedding)
        rows = db.execute(
            text(
                """
                SELECT content
                FROM voice_record_chunks
                WHERE voice_record_id = :record_id
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                "record_id": voice_record_id,
                "embedding": query_embedding,
                "limit": RAG_TOP_K,
            },
        ).fetchall()

        for row in rows:
            content = row[0]
            if content and content not in seen:
                contexts.append(content)
                seen.add(content)

    return contexts


async def analyze_first_session(
    db: Session,
    client: Client,
    voice_record_id: int,
    fallback_dialogue: str,
):
    """1회기 상담 내용을 바탕으로 AI 분석 수행 (RAG 사용)"""
    try:
        from config.clients import initialize_clients
        client_container = initialize_clients()
        
        if not client_container.openai_client:
            logger.warning("OpenAI client not available, skipping AI analysis")
            return
        
        # 상담 경력 텍스트 변환
        counseling_history = "있음" if client.has_previous_counseling else "없음"

        try:
            rag_chunks = await build_rag_context(db, client_container.openai_client, voice_record_id)
        except Exception as e:
            logger.warning(f"RAG context build failed, fallback to dialogue: {str(e)}")
            rag_chunks = []

        if rag_chunks:
            context_block = "\n\n".join([f"[{idx + 1}] {chunk}" for idx, chunk in enumerate(rag_chunks)])
        else:
            context_block = fallback_dialogue or ""

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

## 1회기 상담 근거 발화
{context_block}

## 요청사항
1회기 실제 상담 내용을 바탕으로 다음 3가지를 **전문적이고 상세하게** 재평가해주세요:

1. **상담신청 배경**: 1회기 상담을 통해 파악된 실제 상담신청 배경과 맥락을 전문적 관점에서 분석
2. **주호소문제**: 1회기 상담에서 드러난 주요 문제들을 심리학적 관점에서 체계적으로 정리
3. **현재 증상**: 1회기 상담에서 관찰되고 파악된 증상들을 구체적으로 기술

각 항목은 최소 3-4문장 이상으로 전문적이면서도 이해하기 쉽게 작성해주세요.
텍스트에 근거가 없으면 "확인 불가"라고 명시해주세요.
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


async def identify_counselor_speaker_id(
    openai_client: AsyncOpenAI | None,
    segments: list[dict],
) -> str | None:
    """첫 5개 발화를 기반으로 상담사 화자 ID를 추정"""
    if not openai_client:
        logger.warning("OpenAI client not available, skipping counselor identification")
        return None

    if not segments:
        return None

    speaker_ids: list[str] = []
    for seg in segments:
        speaker_id = str(seg.get("speaker_id"))
        if speaker_id not in speaker_ids:
            speaker_ids.append(speaker_id)

    if len(speaker_ids) < 2:
        return None

    sample_segments = segments[:5]
    lines = []
    for idx, seg in enumerate(sample_segments, start=1):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        speaker_id = str(seg.get("speaker_id"))
        lines.append(f"{idx}. 발화자 {speaker_id}: {text}")

    if not lines:
        return None

    prompt = f"""
다음은 상담 도입부의 발화 {len(lines)}개입니다.
발화자 ID는 {speaker_ids} 중 하나입니다.
상담사(전문가)로 판단되는 발화자 ID를 하나 선택하세요.
확신이 없으면 null을 반환하세요.

응답은 반드시 JSON 형식으로만 작성:
{{"counselor_speaker_id": "A", "confidence": 0.0}}

발화 목록:
{chr(10).join(lines)}
"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 상담 대화에서 상담사와 내담자를 구분하는 전문가입니다. "
                        "상담사는 질문, 반영, 정리, 공감, 진행을 주도하는 경향이 있고 "
                        "내담자는 개인 경험, 감정, 사건을 서술하는 경향이 있습니다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        counselor_id = result.get("counselor_speaker_id")
        if counselor_id is None:
            return None
        counselor_id = str(counselor_id).strip()
        if counselor_id not in speaker_ids:
            logger.warning(
                f"Counselor speaker id not in list, skipping: {counselor_id}"
            )
            return None
        return counselor_id
    except Exception as e:
        logger.warning(f"Counselor identification failed: {str(e)}")
        return None


def build_speaker_label_map(speaker_ids: list[str], counselor_id: str) -> dict[str, str]:
    """상담사/내담자 라벨 매핑 생성"""
    label_map: dict[str, str] = {counselor_id: "상담사"}
    client_index = 0
    for speaker_id in speaker_ids:
        if speaker_id == counselor_id:
            continue
        if client_index < 26:
            suffix = chr(ord("A") + client_index)
        else:
            suffix = str(client_index + 1)
        label_map[speaker_id] = f"내담자 {suffix}"
        client_index += 1
    return label_map


def run_stt_processing_background(
    upload_id: int,
    s3_key: str,
    user_id: int,
    client_id: int,
    session_number: Optional[int],
    language_code: str,
):
    """백그라운드에서 STT 및 기록 저장 처리"""
    temp_file_path = None
    db = SessionLocal()
    upload = None
    try:
        upload = db.query(VoiceUpload).filter(
            VoiceUpload.id == upload_id,
            VoiceUpload.user_id == user_id,
        ).first()
        if not upload:
            logger.warning(f"Upload not found for processing: upload_id={upload_id}, user_id={user_id}")
            return
        upload.status = "processing"
        db.commit()

        client = db.query(Client).filter(
            Client.id == client_id,
            Client.user_id == user_id,
        ).first()
        if not client:
            logger.warning(f"Client not found or unauthorized: client_id={client_id}, user_id={user_id}")
            upload.status = "failed"
            upload.error_message = "Client not found or unauthorized"
            db.commit()
            return

        from config.clients import initialize_clients
        client_container = initialize_clients()

        if not client_container.assemblyai_api_key:
            logger.error("ASSEMBLYAI_API_KEY not configured; skipping STT")
            upload.status = "failed"
            upload.error_message = "ASSEMBLYAI_API_KEY not configured"
            db.commit()
            return

        if not client_container.s3_client:
            logger.error("S3 client not configured; skipping STT")
            upload.status = "failed"
            upload.error_message = "S3 client not configured"
            db.commit()
            return

        try:
            bucket_name = get_s3_bucket_name()
        except Exception as e:
            logger.error(f"S3 bucket name not configured: {str(e)}")
            raise

        suffix = os.path.splitext(s3_key)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name

        logger.info(f"[bg] Downloading from S3: s3://{bucket_name}/{s3_key}")
        client_container.s3_client.download_file(bucket_name, s3_key, temp_file_path)
        logger.info(f"[bg] File downloaded to: {temp_file_path}")

        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            language_code=language_code or "ko",
            punctuate=True,
            format_text=True,
            disfluencies=False,
            filter_profanity=False,
        )

        logger.info("[bg] Starting transcription with AssemblyAI...")
        transcript = transcriber.transcribe(temp_file_path, config)

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"AssemblyAI transcription failed: {transcript.error}")
            upload.status = "failed"
            upload.error_message = f"AssemblyAI transcription failed: {transcript.error}"
            db.commit()
            return

        logger.info(f"[bg] Transcription completed: {len(transcript.utterances)} utterances")

        speakers = {}
        segments = []

        for utterance in transcript.utterances:
            speaker_id = str(utterance.speaker)
            utterance_text = utterance.text
            start_time = utterance.start / 1000.0
            end_time = utterance.end / 1000.0

            segments.append({
                "speaker_id": speaker_id,
                "text": utterance_text,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
            })

            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "speaker_id": speaker_id,
                    "text": "",
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": 0,
                }

            speakers[speaker_id]["text"] += " " + utterance_text
            speakers[speaker_id]["end_time"] = max(speakers[speaker_id]["end_time"], end_time)
            speakers[speaker_id]["duration"] = (
                speakers[speaker_id]["end_time"] - speakers[speaker_id]["start_time"]
            )

        for speaker_id in speakers:
            speakers[speaker_id]["text"] = speakers[speaker_id]["text"].strip()

        full_transcript = transcript.text

        speaker_ids = []
        for seg in segments:
            seg_speaker_id = str(seg.get("speaker_id"))
            if seg_speaker_id not in speaker_ids:
                speaker_ids.append(seg_speaker_id)

        labels_applied = False
        counselor_id = None
        if client_container.openai_client:
            counselor_id = asyncio.run(
                identify_counselor_speaker_id(client_container.openai_client, segments)
            )

        if counselor_id:
            label_map = build_speaker_label_map(speaker_ids, counselor_id)
            for seg in segments:
                seg_speaker_id = str(seg.get("speaker_id"))
                seg["speaker_id"] = label_map.get(seg_speaker_id, seg_speaker_id)
            for speaker in speakers.values():
                spk_id = str(speaker.get("speaker_id"))
                speaker["speaker_id"] = label_map.get(spk_id, spk_id)
            labels_applied = True
            logger.info(f"[bg] Speaker labels applied: counselor={counselor_id}")

        sorted_speakers = sorted(speakers.values(), key=lambda x: x["start_time"])

        dialogue_prefix = "" if labels_applied else "발화자 "
        dialogue = "\n".join(
            [f"{dialogue_prefix}{seg['speaker_id']}: {seg['text']}" for seg in segments]
        )

        total_duration = int(segments[-1]["end_time"]) if segments else 0

        original_filename = os.path.basename(s3_key)

        if session_number:
            auto_title = f"{client.name} - {session_number}회기 상담"
        else:
            auto_title = f"{client.name} - 상담 기록 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

        voice_record = VoiceRecord(
            title=auto_title,
            user_id=user_id,
            client_id=client_id,
            session_number=session_number,
            s3_key=s3_key,
            original_filename=original_filename,
            total_speakers=len(speakers),
            full_transcript=full_transcript,
            speakers_data=sorted_speakers,
            segments_data=segments,
            dialogue=dialogue,
            language_code=language_code or "ko",
            duration=total_duration,
        )

        db.add(voice_record)
        db.commit()
        db.refresh(voice_record)

        logger.info(f"[bg] Voice record saved: id={voice_record.id}, user_id={user_id}, client_id={client_id}")

        if session_number == 1 and client_container.openai_client:
            if client.ai_analysis_completed:
                logger.info(f"[bg] AI analysis already completed for client_id={client_id}, skipping")
            else:
                try:
                    chunks = build_semantic_chunks(segments)
                    if chunks:
                        ensure_vector_tables(db)
                        embeddings = asyncio.run(embed_texts(client_container.openai_client, chunks))
                        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                            db.execute(
                                text(
                                    """
                                    INSERT INTO voice_record_chunks
                                    (voice_record_id, client_id, session_number, chunk_index, content, embedding)
                                VALUES (:voice_record_id, :client_id, :session_number, :chunk_index, :content, CAST(:embedding AS vector))
                                    """
                                ),
                                {
                                    "voice_record_id": voice_record.id,
                                    "client_id": client_id,
                                    "session_number": session_number,
                                    "chunk_index": idx,
                                    "content": chunk,
                                    "embedding": vector_to_pg(embedding),
                                },
                            )
                        db.commit()
                        logger.info(f"[bg] Stored {len(chunks)} chunks for voice_record_id={voice_record.id}")
                    else:
                        logger.warning(f"[bg] No chunks generated for voice_record_id={voice_record.id}")
                except Exception as e:
                    logger.warning(f"[bg] RAG chunking skipped due to error: {str(e)}")
                    db.rollback()

                try:
                    logger.info(f"[bg] First session detected for client_id={client_id}, running AI analysis")
                    asyncio.run(analyze_first_session(db, client, voice_record.id, dialogue))
                except Exception as e:
                    logger.warning(f"[bg] AI analysis failed: {str(e)}")

        upload.status = "completed"
        upload.voice_record_id = voice_record.id
        upload.error_message = None
        db.commit()
    except Exception as e:
        logger.exception(f"[bg] process-s3-file failed: {str(e)}")
        if upload:
            upload.status = "failed"
            upload.error_message = str(e)
            db.commit()
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"[bg] Temporary file deleted: {temp_file_path}")
            except Exception:
                logger.exception("[bg] Failed to delete temporary file")
        db.close()


# Pydantic 모델
class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "audio/mpeg"


class ProcessS3FileRequest(BaseModel):
    s3_key: str
    client_id: Optional[int] = None  # 내담자 ID (선택)
    session_number: Optional[int] = None  # 회기 번호 (선택)
    language_code: str = "ko"


class ProcessS3FileResponse(BaseModel):
    status: str
    message: str
    task_id: str

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


@router.post("/process-s3-file", response_model=ProcessS3FileResponse)
async def process_s3_file(
    request: ProcessS3FileRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    s3_client = Depends(get_s3_client),
    api_key: str | None = Depends(get_assemblyai_api_key),
):
    """S3에 업로드된 파일을 백그라운드에서 처리
    
    Args:
        request: S3 키, 내담자 ID, 언어 코드
        current_user: 현재 로그인한 사용자 (JWT 인증 필수)
        db: 데이터베이스 세션
    
    Returns:
        처리 요청 결과 (비동기)
    """
    try:
        logger.info(f"/voice/process-s3-file called: s3_key={request.s3_key}, client_id={request.client_id}, user_id={current_user.id}")

        if not request.client_id:
            raise BadRequest("client_id is required")
        
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
        
        upload = VoiceUpload(
            user_id=current_user.id,
            client_id=request.client_id,
            session_number=request.session_number,
            s3_key=request.s3_key,
            status="queued",
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        task_id = str(upload.id)
        background_tasks.add_task(
            run_stt_processing_background,
            upload.id,
            request.s3_key,
            current_user.id,
            request.client_id,
            request.session_number,
            request.language_code or "ko",
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "STT processing started",
                "task_id": task_id,
            },
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("process-s3-file failed")
        raise InternalError(f"STT 처리 요청 실패: {str(e)}")


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
