"""
음성 기록 모델
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class VoiceRecord(Base):
    """음성 처리 기록 테이블"""
    
    __tablename__ = "voice_records"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)  # 기록 제목
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 업로드한 사용자
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)  # 내담자 ID
    session_number = Column(Integer, nullable=True)  # 회기 번호 (내담자 연결 시)
    
    # 파일 정보
    s3_key = Column(String(500), nullable=True)  # S3 키 (삭제된 경우 NULL)
    original_filename = Column(String(500), nullable=True)  # 원본 파일명
    
    # 분석 결과
    total_speakers = Column(Integer, nullable=False)  # 화자 수
    full_transcript = Column(Text, nullable=False)  # 전체 대화 텍스트
    speakers_data = Column(JSON, nullable=False)  # 화자별 데이터 (JSON)
    segments_data = Column(JSON, nullable=False)  # 세그먼트 데이터 (JSON)
    dialogue = Column(Text, nullable=False)  # 시간순 대화
    
    # 메타데이터
    language_code = Column(String(10), nullable=False, default="ko")  # 언어 코드
    duration = Column(Integer, nullable=True)  # 총 길이 (초)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    user = relationship("User", back_populates="voice_records")
    client = relationship("Client", back_populates="voice_records")
    
    def __repr__(self):
        return f"<VoiceRecord(id={self.id}, title='{self.title}', user_id={self.user_id})>"
