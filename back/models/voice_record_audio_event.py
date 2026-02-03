"""
Speechmatics 비언어 이벤트 저장 모델
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime


class VoiceRecordAudioEvent(Base):
    """음성 기록 비언어 이벤트 테이블"""

    __tablename__ = "voice_record_audio_events"

    id = Column(Integer, primary_key=True, index=True)
    voice_record_id = Column(
        Integer, ForeignKey("voice_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String(50), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    channel = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<VoiceRecordAudioEvent(id={self.id}, type='{self.event_type}', "
            f"start={self.start_time}, end={self.end_time})>"
        )
