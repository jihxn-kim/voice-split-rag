"""
내담자 관리 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.client import Client
from models.voice_record import VoiceRecord
from schemas.client import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse, ClientListItem
from auth.dependencies import get_current_active_user
from models.user import User
from logs.logging_util import LoggerSingleton
from config.dependencies import get_openai_client
from openai import AsyncOpenAI
import logging
import json

logger = LoggerSingleton.get_logger(logger_name="client", level=logging.INFO)

router = APIRouter(prefix="/clients", tags=["Clients"])


async def analyze_client_with_openai(client_data: ClientCreate, openai_client: AsyncOpenAI) -> dict:
    """OpenAI를 사용하여 내담자 정보 분석"""
    
    # 상담 경력 텍스트 변환
    counseling_history = "있음" if client_data.has_previous_counseling else "없음"
    
    # 프롬프트 작성
    prompt = f"""
당신은 전문 심리 상담사입니다. 아래 내담자 정보를 바탕으로 상담 계획을 수립해주세요.

## 내담자 정보
- 이름: {client_data.name}
- 나이: {client_data.age}세
- 성별: {client_data.gender}
- 상담신청배경: {client_data.consultation_background}
- 주호소문제: {client_data.main_complaint}
- 상담이전경력: {counseling_history}
- 현재 나타나고 있는 증상(본인호소): {client_data.current_symptoms}

## 요청사항
위 정보를 전문적으로 분석하여 다음 4가지 항목을 작성해주세요:

1. **상담신청 배경**: 내담자가 상담을 신청하게 된 배경을 전문적 관점에서 정리하고 분석
2. **주호소내용**: 내담자의 주요 호소 문제를 심리학적 관점에서 체계적으로 정리
3. **10회기상담목표**: 10회기 단기 상담을 기준으로 구체적이고 측정 가능한 상담 목표 설정
4. **상담전략**: 위 목표를 달성하기 위한 구체적인 상담 전략과 개입 방법 제시

각 항목은 전문적이면서도 이해하기 쉽게 작성해주세요. JSON 형식으로 응답해주세요.
응답 형식:
{{
    "consultation_background": "상담신청 배경 분석 내용",
    "main_complaint": "주호소내용 분석",
    "counseling_goals": "10회기상담목표",
    "counseling_strategy": "상담전략"
}}
"""
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 임상심리 전문가이자 전문 상담사입니다. 내담자의 정보를 분석하여 전문적인 상담 계획을 수립합니다."
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
        logger.info(f"OpenAI analysis completed for client: {client_data.name}")
        return result
        
    except Exception as e:
        logger.error(f"OpenAI analysis failed: {str(e)}")
        # 분석 실패 시에도 내담자 등록은 진행되도록 None 반환
        return {
            "consultation_background": None,
            "main_complaint": None,
            "counseling_goals": None,
            "counseling_strategy": None
        }


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    openai_client: AsyncOpenAI = Depends(get_openai_client)
):
    """내담자 등록 및 AI 분석"""
    logger.info(f"Creating client: name={client_data.name}, counselor_id={current_user.id}")
    
    # OpenAI로 분석 수행
    logger.info(f"Starting AI analysis for client: {client_data.name}")
    analysis_result = await analyze_client_with_openai(client_data, openai_client)
    
    # 내담자 생성
    new_client = Client(
        user_id=current_user.id,
        name=client_data.name,
        age=client_data.age,
        gender=client_data.gender,
        consultation_background=client_data.consultation_background,
        main_complaint=client_data.main_complaint,
        has_previous_counseling=client_data.has_previous_counseling,
        current_symptoms=client_data.current_symptoms,
        # AI 분석 결과 추가
        ai_consultation_background=analysis_result.get("consultation_background"),
        ai_main_complaint=analysis_result.get("main_complaint"),
        ai_counseling_goals=analysis_result.get("counseling_goals"),
        ai_counseling_strategy=analysis_result.get("counseling_strategy")
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    logger.info(f"Client created with AI analysis: id={new_client.id}, name={new_client.name}")
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
    
    return ClientListResponse(
        total=total,
        clients=[ClientListItem.from_orm(client) for client in clients]
    )


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
    
    return {
        "total": total,
        "records": [
            {
                "id": record.id,
                "title": record.title,
                "total_speakers": record.total_speakers,
                "duration": record.duration,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            for record in records
        ]
    }
