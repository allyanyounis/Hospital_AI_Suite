"""Clinical data about a patient, shared by every module: lab results, vital signs, imaging and other reports, past
history and allergies. Rows are recorded once and read by the patient chart, the theatre list and the scribe.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column, one_of

LAB_CATEGORIES = ("haematology", "chemistry", "coagulation")
FLAGS = ("low", "normal", "high")
SOURCES = ("seed", "manual", "import")
REPORT_KINDS = (
    "ultrasound",
    "ecg",
    "xray",
    "ct",
    "mri",
    "echo",
    "angiogram",
    "mammography",
    "pathology",
    "anaesthesia_review",
    "other",
)
HISTORY_KINDS = ("indication", "condition", "surgery")
# The starting catalogue (migration 0004 inserts the same rows): code, name, unit, low, high, category
LAB_CATALOGUE = (
    ("HGB", "Haemoglobin", "g/dL", 12.0, 16.0, "haematology"),
    ("WBC", "White cells", "10^9/L", 4.0, 11.0, "haematology"),
    ("PLT", "Platelets", "10^9/L", 150, 400, "haematology"),
    ("NA", "Sodium", "mmol/L", 135, 145, "chemistry"),
    ("K", "Potassium", "mmol/L", 3.5, 5.1, "chemistry"),
    ("CREA", "Creatinine", "mg/dL", 0.6, 1.2, "chemistry"),
    ("GLU", "Glucose", "mg/dL", 70, 140, "chemistry"),
    ("ALB", "Albumin", "g/dL", 3.5, 5.0, "chemistry"),
    ("INR", "INR", "", 0.8, 1.2, "coagulation"),
)
SEVERITIES = ("mild", "moderate", "severe", "unknown")


class LabTest(Base):
    """The laboratory's test catalogue, with the reference range results are flagged against."""

    __tablename__ = "lab_tests"
    __table_args__ = (
        CheckConstraint(one_of("category", LAB_CATEGORIES), name="category"),
        CheckConstraint("ref_high > ref_low", name="range"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(30), default="", server_default="")
    ref_low: Mapped[float] = mapped_column(Float)
    ref_high: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class LabResult(Base):
    __tablename__ = "lab_results"
    __table_args__ = (
        CheckConstraint(one_of("flag", FLAGS), name="flag"),
        CheckConstraint(one_of("source", SOURCES), name="source"),
        Index("ix_lab_results_patient_test_collected", "patient_id", "test_id", "collected_at"),
        Index("ix_lab_results_patient_collected", "patient_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    test_id: Mapped[int] = mapped_column(ForeignKey("lab_tests.id"))
    test: Mapped[LabTest] = relationship(lazy="joined")
    value: Mapped[float] = mapped_column(Float)
    flag: Mapped[str] = mapped_column(String(10))  # against the test's range when the result was recorded
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    entered_by: Mapped[str | None] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = now_column()


class VitalSigns(Base):
    """One set of observations taken together. Any measurement may be missing."""

    __tablename__ = "vital_signs"
    __table_args__ = (
        CheckConstraint("heart_rate BETWEEN 20 AND 300", name="heart_rate"),
        CheckConstraint("systolic_bp BETWEEN 40 AND 300", name="systolic_bp"),
        CheckConstraint("diastolic_bp BETWEEN 20 AND 200", name="diastolic_bp"),
        CheckConstraint("spo2 BETWEEN 50 AND 100", name="spo2"),
        CheckConstraint("temperature_c BETWEEN 30 AND 45", name="temperature_c"),
        CheckConstraint("resp_rate BETWEEN 2 AND 80", name="resp_rate"),
        CheckConstraint(one_of("source", SOURCES), name="source"),
        Index("ix_vital_signs_patient_recorded", "patient_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    heart_rate: Mapped[int | None] = mapped_column(Integer)  # /min
    systolic_bp: Mapped[int | None] = mapped_column(Integer)  # mmHg
    diastolic_bp: Mapped[int | None] = mapped_column(Integer)
    spo2: Mapped[int | None] = mapped_column(Integer)  # %
    temperature_c: Mapped[float | None] = mapped_column(Float)
    resp_rate: Mapped[int | None] = mapped_column(Integer)  # /min
    source: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = now_column()


class ClinicalReport(Base):
    """An imaging, cardiology, pathology or anaesthesia report, as written text."""

    __tablename__ = "clinical_reports"
    __table_args__ = (
        CheckConstraint(one_of("kind", REPORT_KINDS), name="kind"),
        CheckConstraint(one_of("source", SOURCES), name="source"),
        Index("ix_clinical_reports_patient_reported", "patient_id", "reported_on"),
        Index("ix_clinical_reports_patient_kind", "patient_id", "kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(120))
    reported_on: Mapped[date] = mapped_column(Date)
    body: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    created_at: Mapped[datetime] = now_column()


class ClinicalHistory(Base):
    """A line of the patient's history: why they are listed, a long-term condition, or a past operation."""

    __tablename__ = "clinical_history"
    __table_args__ = (
        CheckConstraint(one_of("kind", HISTORY_KINDS), name="kind"),
        Index("ix_clinical_history_patient_noted", "patient_id", "noted_on"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    noted_on: Mapped[date] = mapped_column(Date)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = now_column()


class PatientAllergy(Base):
    __tablename__ = "patient_allergies"
    __table_args__ = (CheckConstraint(one_of("severity", SEVERITIES), name="severity"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(10), default="unknown", server_default="unknown")
    created_at: Mapped[datetime] = now_column()
