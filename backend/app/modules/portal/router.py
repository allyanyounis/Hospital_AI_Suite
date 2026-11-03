"""Patient portal API. Every query is scoped to the signed-in patient's own record."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.appointments import Appointment
from app.modules.auth import User, require
from app.modules.patients import Patient

from .schemas import PortalAppointment, PortalProfile

router = APIRouter(prefix="/api/portal", tags=["patient portal"])
patient_user = require("portal.use")


def _patient_id(user: User) -> int:
    if user.patient_id is None:  # the users table forbids this for patients; guards against a misconfigured role
        raise HTTPException(403, "This account is not linked to a patient record")
    return user.patient_id


@router.get("/me", response_model=PortalProfile)
def profile(db: Session = Depends(get_db), user: User = Depends(patient_user)):
    patient = db.get(Patient, _patient_id(user))
    return PortalProfile(
        name=patient.full_name,
        mrn=patient.mrn or "",
        dob=patient.date_of_birth.isoformat() if patient.date_of_birth else "",
        sex=patient.sex or "",
    )


@router.get("/appointments", response_model=list[PortalAppointment])
def appointments(db: Session = Depends(get_db), user: User = Depends(patient_user)):
    rows = db.scalars(
        select(Appointment).where(Appointment.patient_id == _patient_id(user)).order_by(Appointment.start_time)
    )
    return [PortalAppointment.of(a) for a in rows.unique()]
