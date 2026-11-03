"""Clinical data API (clinical.view): a patient's labs, vitals, reports, history and allergies. Read-only for now;
results arrive from the seed (and, later, the lab and ward modules)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pagination import Page
from app.modules.auth import require

from . import service
from .models import REPORT_KINDS
from .schemas import (
    ClinicalSummary,
    HistoryOut,
    LabResultOut,
    LabTestOut,
    ReportListItem,
    ReportOut,
    SeriesPoint,
    VitalSignsOut,
)

router = APIRouter(prefix="/api/clinical", tags=["clinical"], dependencies=[Depends(require("clinical.view"))])


@router.get("/lab-tests", response_model=list[LabTestOut])
def lab_tests(db: Session = Depends(get_db)):
    return [LabTestOut.of(t) for t in service.lab_tests(db)]


@router.get("/patients/{patient_id}/summary", response_model=ClinicalSummary)
def summary(patient_id: int, db: Session = Depends(get_db)):
    return service.summary(db, patient_id)


@router.get("/patients/{patient_id}/labs", response_model=Page[LabResultOut])
def labs(patient_id: int, test: str = "", cursor: str = "", limit: int = 50, db: Session = Depends(get_db)):
    return service.labs_page(db, patient_id, test or None, cursor or None, limit)


@router.get("/patients/{patient_id}/labs/series", response_model=list[SeriesPoint])
def lab_series(patient_id: int, test: str = Query(min_length=1), db: Session = Depends(get_db)):
    return service.lab_series(db, patient_id, test)


@router.get("/patients/{patient_id}/vitals", response_model=Page[VitalSignsOut])
def vitals(patient_id: int, cursor: str = "", limit: int = 50, db: Session = Depends(get_db)):
    return service.vitals_page(db, patient_id, cursor or None, limit)


@router.get("/patients/{patient_id}/reports", response_model=Page[ReportListItem])
def reports(
    patient_id: int,
    kind: str = Query("", pattern=f"^({'|'.join(REPORT_KINDS)})?$"),
    cursor: str = "",
    limit: int = 30,
    db: Session = Depends(get_db),
):
    return service.reports_page(db, patient_id, kind or None, cursor or None, limit)


@router.get("/reports/{report_id}", response_model=ReportOut)
def report(report_id: int, db: Session = Depends(get_db)):
    return ReportOut.of(service.get_report(db, report_id))


@router.get("/patients/{patient_id}/history", response_model=list[HistoryOut])
def history(patient_id: int, db: Session = Depends(get_db)):
    return service.history(db, patient_id)
