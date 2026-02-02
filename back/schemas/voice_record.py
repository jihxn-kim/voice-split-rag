"""
음성 기록 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class VoiceRecordBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class VoiceRecordCreate(BaseModel):
    """음성 기록 생성 (내부용)"""
    title: str
    s3_key: Optional[str] = None
    original_filename: Optional[str] = None
    total_speakers: int
    full_transcript: str
    speakers_data: List[dict]
    segments_data: List[dict]
    dialogue: str
    language_code: str = "ko"
    duration: Optional[int] = None


class VoiceRecordUpdate(BaseModel):
    """음성 기록 수정 (제목만)"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    speaker_renames: Optional[Dict[str, str]] = None


class VoiceRecordResponse(BaseModel):
    """음성 기록 응답 (전체)"""
    id: int
    title: str
    user_id: int
    client_id: Optional[int] = None
    session_number: Optional[int] = None
    s3_key: Optional[str]
    original_filename: Optional[str]
    total_speakers: int
    full_transcript: str
    speakers_data: List[dict]
    segments_data: List[dict]
    dialogue: str
    language_code: str
    duration: Optional[int]
    next_session_goal: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VoiceRecordListItem(BaseModel):
    """음성 기록 목록 아이템 (간략)"""
    id: int
    title: str
    client_id: Optional[int] = None
    session_number: Optional[int] = None
    total_speakers: int
    language_code: str
    duration: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VoiceRecordListResponse(BaseModel):
    """음성 기록 목록 응답"""
    total: int
    records: List[VoiceRecordListItem]
