"""
음성 업로드 처리 상태 모델
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class VoiceUpload(Base):
    """음성 업로드/처리 상태 테이블"""

    __tablename__ = "voice_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    session_number = Column(Integer, nullable=True)
    s3_key = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    voice_record_id = Column(Integer, ForeignKey("voice_records.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    client = relationship("Client")
    voice_record = relationship("VoiceRecord")

    def __repr__(self):
        return f"<VoiceUpload(id={self.id}, status='{self.status}', client_id={self.client_id})>"
