"""Patient registry API: search and read (patients.view), register and edit (patients.manage)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth import User, require

from . import service
from .schemas import PatientIn, PatientRecord, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])
manage = require("patients.manage")


def _records(db: Session, patients) -> list[PatientRecord]:
    accounts = service.with_accounts(db, [p.id for p in patients])
    return [PatientRecord.of(p, p.id in accounts) for p in patients]


@router.get("", response_model=list[PatientRecord])
def search(q: str = "", db: Session = Depends(get_db), _: User = Depends(require("patients.view"))):
    return _records(db, service.search(db, q))


@router.get("/{patient_id}", response_model=PatientRecord)
def read(patient_id: int, db: Session = Depends(get_db), _: User = Depends(require("patients.view"))):
    return _records(db, [service.get_patient(db, patient_id)])[0]


@router.post("", response_model=PatientRecord, status_code=201)
def register(req: PatientIn, db: Session = Depends(get_db), user: User = Depends(manage)):
    patient = service.register(db, user.username, req)
    db.commit()
    return _records(db, [patient])[0]


@router.patch("/{patient_id}", response_model=PatientRecord)
def update(patient_id: int, req: PatientUpdate, db: Session = Depends(get_db), user: User = Depends(manage)):
    patient = service.update(db, user.username, service.get_patient(db, patient_id), req)
    db.commit()
    return _records(db, [patient])[0]
