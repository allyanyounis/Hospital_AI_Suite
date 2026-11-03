"""Scribe tables."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import now_column


class Encounter(Base):
    """One recorded or sample consultation moving through the scribe pipeline. Audio is never stored."""

    __tablename__ = "encounters"
    __table_args__ = (Index("encounters_user_created", "username", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    username: Mapped[str] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = now_column()
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
