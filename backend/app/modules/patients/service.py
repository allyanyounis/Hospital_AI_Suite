"""The master patient index: registering, finding, updating and erasing patients. Other modules link to patients;
this module never imports them (it finds referring tables through the foreign-key metadata)."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.database import Base

from .models import Patient
from .schemas import PatientIn, PatientUpdate

SEARCH_LIMIT = 50


# --- Registry ----------------------------------------------------------------------------------------------------


def search(db: Session, q: str = "") -> list[Patient]:
    """Patients whose name, MRN or phone contains `q`; the newest first when `q` is empty."""
    query = select(Patient).order_by(Patient.created_at.desc()).limit(SEARCH_LIMIT)
    if q := q.strip():
        like = f"%{q.lower()}%"
        query = query.where(
            or_(func.lower(Patient.full_name).like(like), func.lower(Patient.mrn).like(like), Patient.phone.like(like))
        )
    return list(db.scalars(query))


def get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "No such patient")
    return patient


def with_accounts(db: Session, patient_ids: list[int]) -> set[int]:
    """Which of these patients have a portal account (read via metadata: auth depends on patients, not back)."""
    users = Base.metadata.tables.get("users")
    if users is None or not patient_ids:
        return set()
    return set(db.scalars(select(users.c.patient_id).where(users.c.patient_id.in_(patient_ids))))


def _check_mrn(db: Session, mrn: str | None, patient_id: int | None = None) -> None:
    if mrn and db.scalar(select(Patient.id).where(Patient.mrn == mrn, Patient.id != (patient_id or 0))):
        raise HTTPException(409, "Another patient already has that MRN")


def register(db: Session, actor: str | None, req: PatientIn) -> Patient:
    _check_mrn(db, req.mrn or None)
    patient = Patient(
        full_name=req.full_name,
        mrn=req.mrn or None,
        sex=req.sex or None,
        date_of_birth=req.date_of_birth,
        phone=req.phone or None,
        email=req.email or None,
        registered=True,
    )
    db.add(patient)
    db.flush()
    audit(actor, "patient.registered", db=db, patient_id=patient.id)  # ids only, never demographics
    return patient


def update(db: Session, actor: str | None, patient: Patient, req: PatientUpdate) -> Patient:
    changes = req.model_dump(exclude_unset=True)
    if "mrn" in changes:
        _check_mrn(db, changes["mrn"] or None, patient.id)
    for field, value in changes.items():
        setattr(patient, field, value if value not in ("",) else None)
    patient.registered = True
    audit(actor, "patient.updated", db=db, patient_id=patient.id, fields=sorted(changes))
    return patient


# --- Linking from other modules ----------------------------------------------------------------------------------


def resolve_patient(db: Session, current: Patient | None, name: str, mrn: str, sex: str, dob: date | None) -> Patient:
    """The patient a clinician's form describes, with its details updated.

    With an MRN the hospital-wide record is found (or created) by MRN. Without one, the caller's current MRN-less
    patient is edited in place, or a new one is created; patients are never matched by name here.
    """
    if mrn:
        patient = db.scalar(select(Patient).where(Patient.mrn == mrn)) or Patient(mrn=mrn)
    elif current is not None and current.mrn is None:
        patient = current
    else:
        patient = Patient()
    patient.full_name, patient.sex, patient.date_of_birth = name, sex or None, dob
    db.add(patient)
    return patient


def delete_orphan_patients(db: Session) -> int:
    """Remove provisional (not registered) patients that no row in any table refers to any more (e.g. after a
    retention purge). Registered patients are permanent hospital records.

    The referring tables are found from the foreign keys on Base.metadata, so new modules are covered automatically.
    """
    referrers = [
        exists().where(fk.parent == Patient.id)
        for table in Base.metadata.tables.values()
        for fk in table.foreign_keys
        if fk.column.table is Patient.__table__
    ]
    return db.execute(delete(Patient).where(Patient.registered.is_(False), *(~r for r in referrers))).rowcount
