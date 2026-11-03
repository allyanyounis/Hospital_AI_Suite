"""Shared tables: staff accounts and the audit trail.

Each module keeps its own tables next to its code (schedule/models.py, scribe/models.py, reception/models.py);
app/modules.py lists the modules so every table is registered. JSON documents (transcripts, notes, codes, tasks)
are stored as JSONB and always replaced whole, never mutated in place.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now_column(**kw) -> Mapped[datetime]:
    """A timestamptz column defaulting to the database's now()."""
    return mapped_column(DateTime(timezone=True), server_default=func.now(), **kw)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('clinician', 'admin')", name="users_role_check"),)

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="clinician")
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = now_column()


class AuditLog(Base):
    """Who did what, when. Never holds clinical content: ids, counts and settings only."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("audit_log_encounter", "encounter_id"), Index("audit_log_user_ts", "username", "ts"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = now_column()
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    encounter_id: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[dict | None] = mapped_column(JSONB)
