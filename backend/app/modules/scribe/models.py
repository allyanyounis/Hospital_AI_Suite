"""Scribe tables: encounters and their code list and task checklist."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column, one_of
from app.modules.patients import Patient

ENCOUNTER_SOURCES = ("live", "recording", "sample")
NOTE_STATUSES = ("drafting", "ready", "failed")
EXTRAS_SOURCES = ("draft", "signed")
CODE_KINDS = ("primary", "secondary", "symptom", "history")
CONFIDENCES = ("high", "medium", "low")
TASK_CATEGORIES = ("test", "medication", "referral", "follow_up", "patient_advice", "admin")
TASK_OWNERS = ("clinician", "nurse", "patient", "admin")


class Encounter(Base):
    """One recorded or sample consultation moving through the scribe pipeline. Audio is never stored."""

    __tablename__ = "encounters"
    __table_args__ = (
        Index("ix_encounters_username_created_at", "username", "created_at"),
        Index("ix_encounters_patient_id", "patient_id"),
        CheckConstraint(one_of("source", ENCOUNTER_SOURCES), name="source"),
        CheckConstraint(one_of("note_status", NOTE_STATUSES), name="note_status"),
        CheckConstraint(one_of("codes_source", EXTRAS_SOURCES), name="codes_source"),
        CheckConstraint(one_of("tasks_source", EXTRAS_SOURCES), name="tasks_source"),
        CheckConstraint("approved_at IS NULL OR drafted_at IS NOT NULL", name="approved_after_drafted"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    username: Mapped[str] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = now_column()
    source: Mapped[str] = mapped_column(String(20))
    audio_seconds: Mapped[float | None] = mapped_column(Float)
    # {"segments": [{"id", "speaker", "start", "end", "text"}], "provider", "duration"}; note lines cite segment ids
    transcript: Mapped[dict | None] = mapped_column(JSONB)
    clinician_speaker: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    # Who and what kind of visit. The link is cut by the retention purge.
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"))
    patient: Mapped[Patient | None] = relationship(lazy="joined")
    visit_type: Mapped[str | None] = mapped_column(String(60))

    # Note pipeline: NULL (not started) -> drafting -> ready | failed; signed once approved_at is set
    template_id: Mapped[str | None] = mapped_column(String(64))
    note_status: Mapped[str | None] = mapped_column(String(20))
    note_error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(120))
    draft_note: Mapped[dict | None] = mapped_column(JSONB)  # {"sections": [{"heading", "statements": [...]}]}
    draft_seconds: Mapped[float | None] = mapped_column(Float)
    drafted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_note: Mapped[dict | None] = mapped_column(JSONB)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Provenance of the current code list and task list (their items live in encounter_codes / encounter_tasks)
    codes_source: Mapped[str | None] = mapped_column(String(10))
    codes_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tasks_source: Mapped[str | None] = mapped_column(String(10))
    tasks_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    codes: Mapped[list["EncounterCode"]] = relationship(
        order_by="EncounterCode.position", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list["EncounterTask"]] = relationship(
        order_by="EncounterTask.position", cascade="all, delete-orphan", passive_deletes=True
    )

    # Edit counts at approval (kept after retention purge for metrics)
    lines_drafted: Mapped[int | None] = mapped_column(Integer)
    lines_kept: Mapped[int | None] = mapped_column(Integer)
    lines_added: Mapped[int | None] = mapped_column(Integer)
    lines_removed: Mapped[int | None] = mapped_column(Integer)
    content_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EncounterCode(Base):
    """A suggested ICD-10 code, owned and edited by the clinician."""

    __tablename__ = "encounter_codes"
    __table_args__ = (
        CheckConstraint(one_of("kind", CODE_KINDS), name="kind"),
        CheckConstraint(one_of("confidence", CONFIDENCES), name="confidence"),
    )

    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[str] = mapped_column(String(10))
    evidence: Mapped[str] = mapped_column(Text, default="", server_default="")


class EncounterTask(Base):
    """One item of the encounter's care task checklist."""

    __tablename__ = "encounter_tasks"
    __table_args__ = (
        CheckConstraint(one_of("category", TASK_CATEGORIES), name="category"),
        CheckConstraint(one_of("owner", TASK_OWNERS), name="owner"),
    )

    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text, default="", server_default="")
    category: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(10))
    due: Mapped[str] = mapped_column(String(120), default="", server_default="")  # as stated in the note
    done: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
