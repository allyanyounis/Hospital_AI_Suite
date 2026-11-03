"""Appointments API for staff: the board, front-desk booking, availability and cancelling."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.database import get_db
from app.core.events import broadcaster
from app.modules.auth import User, require
from app.modules.patients import Patient
from app.modules.scheduling import load_schedule
from app.modules.staff import StaffMember, get_bookable

from . import booking
from .extensions import details_for
from .models import Appointment
from .schemas import AppointmentOut, Availability, BookingRequest

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def _out(db: Session, appointments: list[Appointment]) -> list[AppointmentOut]:
    extra = details_for(db, [a.id for a in appointments])
    return [AppointmentOut.of(a, extra.get(a.id)) for a in appointments]


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    practitioner_id: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require("appointments.view")),
):
    query = select(Appointment).order_by(Appointment.start_time)
    if practitioner_id is not None:
        query = query.where(Appointment.practitioner_id == practitioner_id)
    if department_id is not None:
        query = query.join(Appointment.practitioner).where(StaffMember.department_id == department_id)
    return _out(db, list(db.scalars(query).unique()))


@router.get("/availability", response_model=Availability)
def availability(
    practitioner_id: int, date: date, db: Session = Depends(get_db), _: User = Depends(require("appointments.view"))
):
    get_bookable(db, practitioner_id)
    slots = booking.free_slots(db, load_schedule(db, practitioner_id), date)
    return Availability(date=date, slots=[s.strftime("%H:%M") for s in slots])


@router.post("", response_model=AppointmentOut, status_code=201)
async def book_appointment(
    req: BookingRequest, db: Session = Depends(get_db), user: User = Depends(require("appointments.book"))
):
    patient = db.get(Patient, req.patient_id)
    if patient is None:
        raise HTTPException(404, "No such patient")
    doctor = get_bookable(db, req.practitioner_id)
    start = req.start_time.replace(tzinfo=None)  # the form sends hospital-local time
    result = booking.book(
        db, doctor, load_schedule(db, doctor.id), patient, req.reason.strip(), start, booked_via="desk"
    )
    if not result.ok:
        raise HTTPException(422, result.message)
    audit(user.username, "appointment.booked", db=db, appointment_id=result.appointment.id, source="desk")
    db.commit()
    await broadcaster.publish("appointment_booked")
    return _out(db, [result.appointment])[0]


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: int, db: Session = Depends(get_db), user: User = Depends(require("appointments.manage"))
):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    if not appointment.canceled:
        appointment.canceled = True
        audit(user.username, "appointment.canceled", db=db, appointment_id=appointment_id, source="dashboard")
        db.commit()
        await broadcaster.publish("appointment_canceled")
    return _out(db, [appointment])[0]
