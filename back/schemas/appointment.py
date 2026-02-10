"""
상담 예약(Appointment) 스키마
"""

from pydantic import BaseModel, Field
import datetime
from typing import Optional


class AppointmentCreate(BaseModel):
    """예약 생성 스키마"""
    client_id: int = Field(..., description="내담자 ID")
    session_number: int = Field(..., ge=1, description="회차")
    date: datetime.date = Field(..., description="상담 날짜")
    start_time: datetime.time = Field(..., description="시작 시간")
    end_time: datetime.time = Field(..., description="종료 시간")
    memo: Optional[str] = Field(None, description="메모")


class AppointmentUpdate(BaseModel):
    """예약 수정 스키마 (모든 필드 선택적)"""
    client_id: Optional[int] = None
    session_number: Optional[int] = Field(None, ge=1)
    date: Optional[datetime.date] = None
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None
    memo: Optional[str] = None


class AppointmentResponse(BaseModel):
    """예약 응답 스키마"""
    id: int
    user_id: int
    client_id: int
    client_name: str
    session_number: int
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    memo: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    """예약 목록 응답"""
    total: int
    appointments: list[AppointmentResponse]
