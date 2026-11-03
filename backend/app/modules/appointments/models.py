"""Outpatient (OPD) appointments: a patient, a doctor, a time slot. How the booking was made is recorded; the
details of each channel (e.g. the voice call) are kept by that channel's module."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, String, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column, one_of
from app.modules.patients import Patient
from app.modules.staff import StaffMember

BOOKING_CHANNELS = ("voice", "desk", "portal")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_start_time", "start_time"),
        Index("ix_appointments_patient_id", "patient_id"),
        Index("ix_appointments_practitioner_id", "practitioner_id"),
        # Database backstop for the booking rules: one active appointment per doctor per slot
        Index(
            "uq_appointments_active_slot",
            "practitioner_id",
            "start_time",
            unique=True,
            postgresql_where=text("NOT canceled"),
        ),
        CheckConstraint(one_of("booked_via", BOOKING_CHANNELS), name="booked_via"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    patient: Mapped[Patient] = relationship(lazy="joined")
    # The doctor; the appointment's department is the doctor's (staff_members.department_id), not stored twice
    practitioner_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id"))
    practitioner: Mapped[StaffMember] = relationship(lazy="joined")
    reason: Mapped[str | None] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canceled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    booked_via: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = now_column()

    @property
    def patient_name(self) -> str:
        return self.patient.full_name
