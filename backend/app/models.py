"""Database tables for the whole suite.

Shared: users, audit_log, clinic_schedule. Scribe: encounters. Receptionist: appointments.
JSON documents (transcripts, notes, codes, tasks) are stored as JSONB and always replaced whole, never mutated in place.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now_column(**kw) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), **kw)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('clinician', 'admin')", name="users_role_check"),)

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="clinician")
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _now_column()


class AuditLog(Base):
    """Who did what, when. Never holds clinical content: ids, counts and settings only."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("audit_log_encounter", "encounter_id"), Index("audit_log_user_ts", "username", "ts"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = _now_column()
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    encounter_id: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[dict | None] = mapped_column(JSONB)


class ClinicSchedule(Base):
    """The clinic's weekly hours, slot length and closed dates (a single row, id = 1).

    The AI receptionist books only inside these hours; the scribe's after-hours metric uses them too.
    """

    __tablename__ = "clinic_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # 7 entries, Monday first: {"enabled", "start": "HH:MM", "end": "HH:MM", "breaks": [{"start", "end"}]}
    days: Mapped[list] = mapped_column(JSONB)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=15)
    holidays: Mapped[list[date]] = mapped_column(ARRAY(Date), default=list)
    updated_at: Mapped[datetime] = _now_column(onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(64))


class Encounter(Base):
    """One recorded or sample consultation moving through the scribe pipeline. Audio is never stored."""

    __tablename__ = "encounters"
    __table_args__ = (Index("encounters_user_created", "username", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    username: Mapped[str] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = _now_column()
    source: Mapped[str] = mapped_column(String(20))  # live | recording | sample
    audio_seconds: Mapped[float | None] = mapped_column(Float)
    transcript: Mapped[dict | None] = mapped_column(JSONB)
    clinician_speaker: Mapped[int] = mapped_column(Integer, default=0)

    # Patient & visit
    patient_name: Mapped[str | None] = mapped_column(String(120))
    patient_mrn: Mapped[str | None] = mapped_column(String(60))
    patient_sex: Mapped[str | None] = mapped_column(String(30))
    patient_dob: Mapped[str | None] = mapped_column(String(20))
    visit_type: Mapped[str | None] = mapped_column(String(60))

    # Note pipeline: NULL (not started) -> drafting -> ready | failed; signed once approved_at is set
    template_id: Mapped[str | None] = mapped_column(String(64))
    note_status: Mapped[str | None] = mapped_column(String(20))
    note_error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(120))
    draft_note: Mapped[dict | None] = mapped_column(JSONB)
    draft_seconds: Mapped[float | None] = mapped_column(Float)
    drafted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_note: Mapped[dict | None] = mapped_column(JSONB)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    codes: Mapped[dict | None] = mapped_column(JSONB)
    tasks: Mapped[dict | None] = mapped_column(JSONB)

    # Edit counts at approval (kept after retention purge for metrics)
    lines_drafted: Mapped[int | None] = mapped_column(Integer)
    lines_kept: Mapped[int | None] = mapped_column(Integer)
    lines_added: Mapped[int | None] = mapped_column(Integer)
    lines_removed: Mapped[int | None] = mapped_column(Integer)
    content_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Appointment(Base):
    """A booking made by the AI voice receptionist (or the dashboard)."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(120), index=True)
    reason: Mapped[str | None] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    canceled: Mapped[bool] = mapped_column(Boolean, default=False)
    # The voice call that booked it; links the end-of-call transcript
    call_id: Mapped[str | None] = mapped_column(String(64), index=True)
    transcript: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now_column()
