"""
상담 예약(Appointment) 모델
"""

from sqlalchemy import Column, Integer, String, Date, Time, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Appointment(Base):
    """상담 예약 모델"""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    session_number = Column(Integer, nullable=False)  # 몇 회차
    date = Column(Date, nullable=False)  # 상담 날짜
    start_time = Column(Time, nullable=False)  # 시작 시간
    end_time = Column(Time, nullable=False)  # 종료 시간
    memo = Column(Text, nullable=True)  # 메모

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    user = relationship("User", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment(id={self.id}, client_id={self.client_id}, date={self.date})>"
