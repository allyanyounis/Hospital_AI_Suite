"""Patients: one record per person, shared by the scribe (encounters) and the receptionist (appointments)."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, Identity, Index, String, false, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, now_column, one_of

SEXES = ("Female", "Male", "Other", "Not stated")


class Patient(Base):
    """One person: the hospital's master patient record, shared by every module (registry, appointments, scribe,
    patient accounts).

    `registered` patients (front desk, admin, patient accounts) are permanent records. Provisional ones, created on
    the fly by the scribe's patient form or a phone booking, are removed by the retention purge once nothing refers
    to them.
    """

    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(one_of("sex", SEXES), name="sex"),
        CheckConstraint("btrim(full_name) <> ''", name="full_name_not_blank"),
        Index("ix_patients_full_name_lower", func.lower(text("full_name"))),
        Index("ix_patients_phone", "phone"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    mrn: Mapped[str | None] = mapped_column(String(60), unique=True)  # medical record number, when known
    full_name: Mapped[str] = mapped_column(String(120))
    sex: Mapped[str | None] = mapped_column(String(30))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(254))
    registered: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = now_column()
