"""
내담자(Client) 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Client(Base):
    """내담자 모델"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 상담사 ID
    
    # 기본 정보
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)  # 남성, 여성, 기타
    
    # 상담 정보
    consultation_background = Column(Text, nullable=False)  # 상담신청배경
    main_complaint = Column(Text, nullable=False)  # 주호소문제
    has_previous_counseling = Column(Boolean, nullable=False)  # 상담이전경력(유무)
    current_symptoms = Column(Text, nullable=False)  # 현재 나타나고 있는 증상(본인호소)
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    counselor = relationship("User", back_populates="clients")
    voice_records = relationship("VoiceRecord", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, counselor_id={self.user_id})>"
