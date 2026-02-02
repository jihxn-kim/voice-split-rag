"""
내담자 관리 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from models.client import Client
from models.voice_record import VoiceRecord
from models.voice_upload import VoiceUpload
from schemas.client import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse, ClientListItem
from auth.dependencies import get_current_active_user
from models.user import User
from logs.logging_util import LoggerSingleton
import logging

logger = LoggerSingleton.get_logger(logger_name="client", level=logging.INFO)

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_data: ClientCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """내담자 등록 (AI 분석 없이)"""
    logger.info(f"Creating client: name={client_data.name}, counselor_id={current_user.id}")
    
    # 내담자 생성 (AI 분석 없이, 회기 수는 0으로 시작)
    new_client = Client(
        user_id=current_user.id,
        name=client_data.name,
        age=client_data.age,
        gender=client_data.gender,
        total_sessions=0,  # 등록 후 추가
        consultation_background=client_data.consultation_background,
        main_complaint=client_data.main_complaint,
        has_previous_counseling=client_data.has_previous_counseling,
        current_symptoms=client_data.current_symptoms,
        ai_analysis_completed=False
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    logger.info(f"Client created: id={new_client.id}, name={new_client.name}")
    return new_client


@router.get("", response_model=ClientListResponse)
def get_clients(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """내담자 목록 조회"""
    logger.info(f"Fetching clients for counselor_id={current_user.id}")
    
    query = db.query(Client).filter(Client.user_id == current_user.id)
    total = query.count()
    
    clients = query.order_by(Client.created_at.desc())\
                   .offset(skip)\
                   .limit(limit)\
                   .all()

    client_ids = [client.id for client in clients]
    upload_counts = {}
    if client_ids:
        upload_counts = dict(
            db.query(VoiceRecord.client_id, func.count(VoiceRecord.id))
            .filter(VoiceRecord.client_id.in_(client_ids))
            .group_by(VoiceRecord.client_id)
            .all()
        )

    client_items = []
    for client in clients:
        client_items.append(
            ClientListItem(
                id=client.id,
                name=client.name,
                age=client.age,
                gender=client.gender,
                total_sessions=client.total_sessions or 0,
                uploaded_sessions=upload_counts.get(client.id, 0),
                main_complaint=client.main_complaint,
                created_at=client.created_at,
            )
        )
    
    return ClientListResponse(total=total, clients=client_items)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """내담자 상세 조회"""
    logger.info(f"Fetching client: id={client_id}, counselor_id={current_user.id}")
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        logger.warning(f"Client not found or unauthorized: id={client_id}, counselor_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_update: ClientUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """내담자 정보 수정"""
    logger.info(f"Updating client: id={client_id}, counselor_id={current_user.id}")
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        logger.warning(f"Client not found for update: id={client_id}, counselor_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # 업데이트할 필드만 적용
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    logger.info(f"Client updated: id={client.id}")
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """내담자 삭제 (관련 음성 기록도 함께 삭제)"""
    logger.info(f"Deleting client: id={client_id}, counselor_id={current_user.id}")
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        logger.warning(f"Client not found for deletion: id={client_id}, counselor_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    db.delete(client)
    db.commit()
    
    logger.info(f"Client deleted: id={client_id}")
    return


@router.get("/{client_id}/voice-records", response_model=dict)
def get_client_voice_records(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """특정 내담자의 음성 기록 목록 조회"""
    logger.info(f"Fetching voice records for client: id={client_id}, counselor_id={current_user.id}")
    
    # 내담자가 현재 사용자의 것인지 확인
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        logger.warning(f"Client not found for voice records: id={client_id}, counselor_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    query = db.query(VoiceRecord).filter(VoiceRecord.client_id == client_id)
    total = query.count()
    
    records = query.order_by(VoiceRecord.created_at.desc())\
                   .offset(skip)\
                   .limit(limit)\
                   .all()

    uploads = db.query(VoiceUpload).filter(
        VoiceUpload.client_id == client_id,
        VoiceUpload.user_id == current_user.id,
        VoiceUpload.status.in_(["queued", "processing", "failed"]),
    ).order_by(VoiceUpload.created_at.desc()).all()
    
    return {
        "total": total,
        "records": [
            {
                "id": record.id,
                "title": record.title,
                "session_number": record.session_number,
                "total_speakers": record.total_speakers,
                "duration": record.duration,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            for record in records
        ],
        "uploads": [
            {
                "id": upload.id,
                "session_number": upload.session_number,
                "status": upload.status,
                "error_message": upload.error_message,
                "created_at": upload.created_at.isoformat(),
                "updated_at": upload.updated_at.isoformat() if upload.updated_at else None,
            }
            for upload in uploads
        ],
    }


@router.get("/{client_id}/upload-status", response_model=dict)
def get_client_upload_status(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """특정 내담자의 업로드 상태만 조회 (경량)"""
    logger.info(f"Fetching upload status for client: id={client_id}, counselor_id={current_user.id}")

    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()

    if not client:
        logger.warning(f"Client not found for upload status: id={client_id}, counselor_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    uploads = db.query(VoiceUpload).filter(
        VoiceUpload.client_id == client_id,
        VoiceUpload.user_id == current_user.id,
        VoiceUpload.status.in_(["queued", "processing", "failed"]),
    ).order_by(VoiceUpload.created_at.desc()).all()

    return {
        "uploads": [
            {
                "id": upload.id,
                "session_number": upload.session_number,
                "status": upload.status,
                "error_message": upload.error_message,
                "created_at": upload.created_at.isoformat(),
                "updated_at": upload.updated_at.isoformat() if upload.updated_at else None,
            }
            for upload in uploads
        ],
    }
