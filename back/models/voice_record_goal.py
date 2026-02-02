"""
회기별 AI 상담 목표 모델
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class VoiceRecordGoal(Base):
    """회기별 다음 상담 목표 테이블"""

    __tablename__ = "voice_record_goals"

    id = Column(Integer, primary_key=True, index=True)
    voice_record_id = Column(
        Integer, ForeignKey("voice_records.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    session_number = Column(Integer, nullable=True)
    next_session_goal = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    voice_record = relationship("VoiceRecord")
    client = relationship("Client")

    def __repr__(self):
        return f"<VoiceRecordGoal(id={self.id}, voice_record_id={self.voice_record_id})>"
