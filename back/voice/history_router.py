"""
음성 기록 관리 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.dependencies import get_current_active_user
from models.user import User
from models.voice_record import VoiceRecord
from schemas.voice_record import VoiceRecordResponse, VoiceRecordListResponse, VoiceRecordUpdate
from database import get_db
from logs.logging_util import LoggerSingleton
from config.exception import BadRequest, InternalError, AppException
from datetime import datetime
import logging

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="voice_history", level=logging.INFO)

router = APIRouter(prefix="/voice/records", tags=["Voice Records"])


@router.get("", response_model=VoiceRecordListResponse)
async def get_voice_records(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """음성 기록 목록 조회
    
    Args:
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
        skip: 건너뛸 개수 (페이지네이션)
        limit: 가져올 최대 개수
    
    Returns:
        음성 기록 목록
    """
    try:
        logger.info(f"GET /voice/records called: user_id={current_user.id}, skip={skip}, limit={limit}")
        
        # 사용자의 음성 기록 조회 (최신순)
        records = db.query(VoiceRecord).filter(
            VoiceRecord.user_id == current_user.id
        ).order_by(
            VoiceRecord.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        # 총 개수
        total = db.query(VoiceRecord).filter(
            VoiceRecord.user_id == current_user.id
        ).count()
        
        logger.info(f"Retrieved {len(records)} records (total: {total})")
        
        return {
            "total": total,
            "records": records
        }
        
    except Exception as e:
        logger.exception("get_voice_records failed")
        raise InternalError(f"기록 목록 조회 실패: {str(e)}")


@router.get("/{record_id}", response_model=VoiceRecordResponse)
async def get_voice_record(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """음성 기록 상세 조회
    
    Args:
        record_id: 기록 ID
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        음성 기록 상세 정보
    """
    try:
        logger.info(f"GET /voice/records/{record_id} called: user_id={current_user.id}")
        
        # 기록 조회
        record = db.query(VoiceRecord).filter(
            VoiceRecord.id == record_id,
            VoiceRecord.user_id == current_user.id
        ).first()
        
        if not record:
            raise BadRequest("기록을 찾을 수 없습니다.", code="RECORD_NOT_FOUND")
        
        logger.info(f"Record retrieved: id={record.id}")
        
        return record
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("get_voice_record failed")
        raise InternalError(f"기록 조회 실패: {str(e)}")


@router.patch("/{record_id}", response_model=VoiceRecordResponse)
async def update_voice_record(
    record_id: int,
    update_data: VoiceRecordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """음성 기록 제목 수정
    
    Args:
        record_id: 기록 ID
        update_data: 수정할 데이터 (제목)
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        수정된 음성 기록
    """
    try:
        logger.info(f"PATCH /voice/records/{record_id} called: user_id={current_user.id}, new_title={update_data.title}")
        
        # 기록 조회
        record = db.query(VoiceRecord).filter(
            VoiceRecord.id == record_id,
            VoiceRecord.user_id == current_user.id
        ).first()
        
        if not record:
            raise BadRequest("기록을 찾을 수 없습니다.", code="RECORD_NOT_FOUND")
        
        # 제목 수정
        record.title = update_data.title
        record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(record)
        
        logger.info(f"Record updated: id={record.id}, title={record.title}")
        
        return record
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("update_voice_record failed")
        raise InternalError(f"기록 수정 실패: {str(e)}")


@router.delete("/{record_id}")
async def delete_voice_record(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """음성 기록 삭제
    
    Args:
        record_id: 기록 ID
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        삭제 성공 메시지
    """
    try:
        logger.info(f"DELETE /voice/records/{record_id} called: user_id={current_user.id}")
        
        # 기록 조회
        record = db.query(VoiceRecord).filter(
            VoiceRecord.id == record_id,
            VoiceRecord.user_id == current_user.id
        ).first()
        
        if not record:
            raise BadRequest("기록을 찾을 수 없습니다.", code="RECORD_NOT_FOUND")
        
        # 삭제
        db.delete(record)
        db.commit()
        
        logger.info(f"Record deleted: id={record_id}")
        
        return {"message": "기록이 삭제되었습니다.", "id": record_id}
        
    except AppException:
        raise
    except Exception as e:
        logger.exception("delete_voice_record failed")
        raise InternalError(f"기록 삭제 실패: {str(e)}")
