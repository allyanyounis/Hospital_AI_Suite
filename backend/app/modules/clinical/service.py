"""Reading and recording a patient's clinical data. Lists are newest first and paged (app/core/pagination.py)."""

from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.pagination import after_cursor, clamp, page_of
from app.modules.patients import Patient

from .models import LAB_CATALOGUE, ClinicalHistory, ClinicalReport, LabResult, LabTest, PatientAllergy, VitalSigns
from .schemas import (
    AllergyOut,
    ClinicalSummary,
    HistoryOut,
    LabLatest,
    LabResultOut,
    ReportListItem,
    SeriesPoint,
    VitalRange,
    VitalSignsOut,
)

SERIES_LIMIT = 500

# Adult reference ranges the chart flags observations against (the lab tests carry their own, in lab_tests)
VITAL_RANGES = [
    VitalRange(key="heart_rate", label="Heart rate", unit="/min", low=60, high=100),
    VitalRange(key="systolic_bp", label="Systolic BP", unit="mmHg", low=90, high=140),
    VitalRange(key="diastolic_bp", label="Diastolic BP", unit="mmHg", low=60, high=90),
    VitalRange(key="spo2", label="SpO2", unit="%", low=94, high=100),
    VitalRange(key="temperature_c", label="Temperature", unit="°C", low=36.0, high=37.5),
    VitalRange(key="resp_rate", label="Respiratory rate", unit="/min", low=12, high=20),
]


def flag(value: float, low: float, high: float) -> str:
    return "low" if value < low else "high" if value > high else "normal"


def vital_flags(v: VitalSigns) -> dict[str, str]:
    flags = {}
    for r in VITAL_RANGES:
        value = getattr(v, r.key)
        if value is not None and (f := flag(value, r.low, r.high)) != "normal":
            flags[r.key] = f
    return flags


def _vitals_out(v: VitalSigns | None) -> VitalSignsOut | None:
    return None if v is None else VitalSignsOut.of(v, vital_flags(v))


def _patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "No such patient")
    return patient


# --- Reading -----------------------------------------------------------------------------------------------------


def lab_tests(db: Session) -> list[LabTest]:
    return list(db.scalars(select(LabTest).where(LabTest.active).order_by(LabTest.category, LabTest.name)))


def latest_labs(db: Session, patient_id: int) -> list[LabLatest]:
    """Per test, the newest result and the one before it."""
    rank = (
        func.row_number()
        .over(partition_by=LabResult.test_id, order_by=(LabResult.collected_at.desc(), LabResult.id.desc()))
        .label("rank")
    )
    ranked = select(LabResult.id, rank).where(LabResult.patient_id == patient_id).subquery()
    rows = db.scalars(
        select(LabResult).join(ranked, ranked.c.id == LabResult.id).where(ranked.c.rank <= 2).order_by(ranked.c.rank)
    ).all()
    latest: dict[int, LabLatest] = {}
    for r in rows:
        t = r.test
        if t.id not in latest:
            latest[t.id] = LabLatest(
                test=t.code,
                name=t.name,
                unit=t.unit,
                category=t.category,
                ref_low=t.ref_low,
                ref_high=t.ref_high,
                value=r.value,
                flag=r.flag,
                collected_at=r.collected_at,
            )
        else:
            item = latest[t.id]
            item.previous, item.previous_at = r.value, r.collected_at
            item.trend = "up" if item.value > r.value else "down" if item.value < r.value else "same"
    order = {c: i for i, c in enumerate(("haematology", "chemistry", "coagulation"))}
    return sorted(latest.values(), key=lambda x: (order.get(x.category, 9), x.name))


def summary(db: Session, patient_id: int) -> ClinicalSummary:
    _patient(db, patient_id)
    labs = latest_labs(db, patient_id)
    two = db.scalars(
        select(VitalSigns)
        .where(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.recorded_at.desc(), VitalSigns.id.desc())
        .limit(2)
    ).all()
    counts = db.execute(
        select(ClinicalReport.kind, func.count())
        .where(ClinicalReport.patient_id == patient_id)
        .group_by(ClinicalReport.kind)
    ).all()
    return ClinicalSummary(
        patient_id=patient_id,
        labs=labs,
        out_of_range=sum(1 for lab in labs if lab.flag != "normal"),
        vitals=_vitals_out(two[0] if two else None),
        previous_vitals=_vitals_out(two[1] if len(two) > 1 else None),
        vital_ranges=VITAL_RANGES,
        allergies=[AllergyOut.of(a) for a in allergies(db, patient_id)],
        report_counts=dict(counts),
        history_count=db.scalar(select(func.count()).where(ClinicalHistory.patient_id == patient_id)) or 0,
    )


def _test_by_code(db: Session, code: str) -> LabTest:
    test = db.scalar(select(LabTest).where(LabTest.code == code.upper()))
    if test is None:
        raise HTTPException(404, "No such lab test")
    return test


def labs_page(db: Session, patient_id: int, test: str | None, cursor: str | None, limit: int) -> dict:
    _patient(db, patient_id)
    limit = clamp(limit)
    query = select(LabResult).where(LabResult.patient_id == patient_id)
    if test:
        query = query.where(LabResult.test_id == _test_by_code(db, test).id)
    if (after := after_cursor(LabResult.collected_at, LabResult.id, cursor)) is not None:
        query = query.where(after)
    rows = db.scalars(query.order_by(LabResult.collected_at.desc(), LabResult.id.desc()).limit(limit + 1)).all()
    return page_of(list(rows), limit, lambda r: r.collected_at, LabResultOut.of)


def lab_series(db: Session, patient_id: int, test: str) -> list[SeriesPoint]:
    _patient(db, patient_id)
    rows = db.execute(
        select(LabResult.collected_at, LabResult.value)
        .where(LabResult.patient_id == patient_id, LabResult.test_id == _test_by_code(db, test).id)
        .order_by(LabResult.collected_at.desc())
        .limit(SERIES_LIMIT)
    ).all()
    return [SeriesPoint(at=at, value=value) for at, value in reversed(rows)]


def vitals_page(db: Session, patient_id: int, cursor: str | None, limit: int) -> dict:
    _patient(db, patient_id)
    limit = clamp(limit)
    query = select(VitalSigns).where(VitalSigns.patient_id == patient_id)
    if (after := after_cursor(VitalSigns.recorded_at, VitalSigns.id, cursor)) is not None:
        query = query.where(after)
    rows = db.scalars(query.order_by(VitalSigns.recorded_at.desc(), VitalSigns.id.desc()).limit(limit + 1)).all()
    return page_of(list(rows), limit, lambda v: v.recorded_at, _vitals_out)


def reports_page(db: Session, patient_id: int, kind: str | None, cursor: str | None, limit: int) -> dict:
    _patient(db, patient_id)
    limit = clamp(limit)
    query = select(ClinicalReport).where(ClinicalReport.patient_id == patient_id)
    if kind:
        query = query.where(ClinicalReport.kind == kind)
    if (after := after_cursor(ClinicalReport.reported_on, ClinicalReport.id, cursor, date)) is not None:
        query = query.where(after)
    rows = db.scalars(
        query.order_by(ClinicalReport.reported_on.desc(), ClinicalReport.id.desc()).limit(limit + 1)
    ).all()
    return page_of(list(rows), limit, lambda r: r.reported_on, ReportListItem.of)


def get_report(db: Session, report_id: int) -> ClinicalReport:
    report = db.get(ClinicalReport, report_id)
    if report is None:
        raise HTTPException(404, "No such report")
    return report


def history(db: Session, patient_id: int) -> list[HistoryOut]:
    _patient(db, patient_id)
    rows = db.scalars(
        select(ClinicalHistory)
        .where(ClinicalHistory.patient_id == patient_id)
        .order_by(ClinicalHistory.noted_on.desc(), ClinicalHistory.id.desc())
    )
    return [HistoryOut.of(h) for h in rows]


def allergies(db: Session, patient_id: int) -> list[PatientAllergy]:
    return list(db.scalars(select(PatientAllergy).where(PatientAllergy.patient_id == patient_id)))


# --- For other modules -------------------------------------------------------------------------------------------


def latest_lab_values(db: Session, patient_ids: list[int]) -> dict[int, dict[str, float]]:
    """patient id -> {test code: newest value}, for risk scores."""
    if not patient_ids:
        return {}
    rank = (
        func.row_number()
        .over(
            partition_by=(LabResult.patient_id, LabResult.test_id),
            order_by=(LabResult.collected_at.desc(), LabResult.id.desc()),
        )
        .label("rank")
    )
    ranked = (
        select(LabResult.patient_id, LabResult.test_id, LabResult.value, rank)
        .where(LabResult.patient_id.in_(patient_ids))
        .subquery()
    )
    rows = db.execute(
        select(ranked.c.patient_id, LabTest.code, ranked.c.value)
        .join(LabTest, LabTest.id == ranked.c.test_id)
        .where(ranked.c.rank == 1)
    ).all()
    out: dict[int, dict[str, float]] = {}
    for patient_id, code, value in rows:
        out.setdefault(patient_id, {})[code] = value
    return out


def allergy_text(db: Session, patient_ids: list[int]) -> dict[int, str]:
    """patient id -> "Penicillin (rash), Latex"; patients without a recorded allergy are left out."""
    if not patient_ids:
        return {}
    out: dict[int, list[str]] = {}
    for a in db.scalars(
        select(PatientAllergy).where(PatientAllergy.patient_id.in_(patient_ids)).order_by(PatientAllergy.id)
    ):
        out.setdefault(a.patient_id, []).append(f"{a.substance} ({a.reaction})" if a.reaction else a.substance)
    return {pid: ", ".join(items) for pid, items in out.items()}


def ensure_lab_tests(db: Session) -> None:
    """Add any test of the starting catalogue that is missing (the migration adds them; this restores them)."""
    have = set(db.scalars(select(LabTest.code)))
    for code, name, unit, low, high, category in LAB_CATALOGUE:
        if code not in have:
            db.add(LabTest(code=code, name=name, unit=unit, ref_low=low, ref_high=high, category=category))
    db.flush()


def record_lab(
    db: Session, patient_id: int, test: LabTest | str, value: float, collected_at: datetime, *, source="manual", by=None
) -> LabResult:
    """Record a result, flagged against the test's range; `test` is a LabTest or its code."""
    test = test if isinstance(test, LabTest) else _test_by_code(db, test)
    result = LabResult(
        patient_id=patient_id,
        test=test,
        value=value,
        flag=flag(value, test.ref_low, test.ref_high),
        collected_at=collected_at,
        source=source,
        entered_by=by,
    )
    db.add(result)
    return result


def record_vitals(db: Session, patient_id: int, recorded_at: datetime, *, source="manual", by=None, **values):
    vitals = VitalSigns(patient_id=patient_id, recorded_at=recorded_at, source=source, recorded_by=by, **values)
    db.add(vitals)
    return vitals


def add_report(db: Session, patient_id: int, kind: str, title: str, reported_on: date, body: str, *, source="manual"):
    report = ClinicalReport(
        patient_id=patient_id, kind=kind, title=title, reported_on=reported_on, body=body, source=source
    )
    db.add(report)
    return report


def add_history(db: Session, patient_id: int, kind: str, noted_on: date, text: str) -> ClinicalHistory:
    entry = ClinicalHistory(patient_id=patient_id, kind=kind, noted_on=noted_on, text=text)
    db.add(entry)
    return entry


def add_allergy(db: Session, patient_id: int, substance: str, reaction: str | None = None, severity="unknown"):
    allergy = PatientAllergy(patient_id=patient_id, substance=substance, reaction=reaction, severity=severity)
    db.add(allergy)
    return allergy
