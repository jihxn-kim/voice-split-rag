"""
상담 예약 관리 API 라우터
"""

import calendar
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.appointment import Appointment
from models.client import Client
from models.user import User
from schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentListResponse,
)
from auth.dependencies import get_current_active_user
from logs.logging_util import LoggerSingleton
import logging

logger = LoggerSingleton.get_logger(logger_name="appointment", level=logging.INFO)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _to_response(appt: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appt.id,
        user_id=appt.user_id,
        client_id=appt.client_id,
        client_name=appt.client.name,
        session_number=appt.session_number,
        date=appt.date,
        start_time=appt.start_time,
        end_time=appt.end_time,
        memo=appt.memo,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
    )


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: AppointmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """새 예약 생성"""
    logger.info(f"Creating appointment: client_id={data.client_id}, date={data.date}, user_id={current_user.id}")

    client = db.query(Client).filter(
        Client.id == data.client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    appt = Appointment(
        user_id=current_user.id,
        client_id=data.client_id,
        session_number=data.session_number,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        memo=data.memo,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    logger.info(f"Appointment created: id={appt.id}")
    return _to_response(appt)


@router.get("", response_model=AppointmentListResponse)
def get_appointments(
    year: int,
    month: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """월별 예약 목록 조회"""
    logger.info(f"Fetching appointments: year={year}, month={month}, user_id={current_user.id}")

    _, last_day = calendar.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    appts = (
        db.query(Appointment)
        .filter(
            Appointment.user_id == current_user.id,
            Appointment.date >= start,
            Appointment.date <= end,
        )
        .order_by(Appointment.date, Appointment.start_time)
        .all()
    )

    return AppointmentListResponse(
        total=len(appts),
        appointments=[_to_response(a) for a in appts],
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """예약 상세 조회"""
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id,
    ).first()

    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return _to_response(appt)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """예약 수정"""
    logger.info(f"Updating appointment: id={appointment_id}, user_id={current_user.id}")

    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id,
    ).first()

    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    update_data = data.model_dump(exclude_unset=True)

    if "client_id" in update_data:
        client = db.query(Client).filter(
            Client.id == update_data["client_id"],
            Client.user_id == current_user.id,
        ).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    for field, value in update_data.items():
        setattr(appt, field, value)

    db.commit()
    db.refresh(appt)

    logger.info(f"Appointment updated: id={appt.id}")
    return _to_response(appt)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """예약 삭제"""
    logger.info(f"Deleting appointment: id={appointment_id}, user_id={current_user.id}")

    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id,
    ).first()

    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    db.delete(appt)
    db.commit()

    logger.info(f"Appointment deleted: id={appointment_id}")
