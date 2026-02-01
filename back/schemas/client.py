"""
내담자(Client) 스키마
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ClientBase(BaseModel):
    """내담자 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=100, description="내담자 이름")
    age: int = Field(..., ge=1, le=150, description="내담자 나이")
    gender: str = Field(..., description="성별 (남성, 여성, 기타)")
    total_sessions: int = Field(default=8, ge=1, le=100, description="전체 회기 수")
    consultation_background: str = Field(..., min_length=1, description="상담신청배경")
    main_complaint: str = Field(..., min_length=1, description="주호소문제")
    has_previous_counseling: bool = Field(..., description="상담이전경력 유무")
    current_symptoms: str = Field(..., min_length=1, description="현재 나타나고 있는 증상(본인호소)")


class ClientCreate(ClientBase):
    """내담자 생성 스키마"""
    pass


class ClientUpdate(BaseModel):
    """내담자 수정 스키마 (모든 필드 선택적)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = None
    total_sessions: Optional[int] = Field(None, ge=1, le=100)
    consultation_background: Optional[str] = Field(None, min_length=1)
    main_complaint: Optional[str] = Field(None, min_length=1)
    has_previous_counseling: Optional[bool] = None
    current_symptoms: Optional[str] = Field(None, min_length=1)


class ClientResponse(ClientBase):
    """내담자 응답 스키마"""
    id: int
    user_id: int
    ai_consultation_background: Optional[str] = None  # 1회기 기반 AI 분석
    ai_main_complaint: Optional[str] = None
    ai_current_symptoms: Optional[str] = None
    ai_analysis_completed: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientListItem(BaseModel):
    """내담자 목록 아이템 (간략 정보)"""
    id: int
    name: str
    age: int
    gender: str
    main_complaint: str  # 주호소문제만 표시
    created_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """내담자 목록 응답"""
    total: int
    clients: list[ClientListItem]
