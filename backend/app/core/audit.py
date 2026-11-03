"""Audit trail. Every sign-in, clinical action and booking is logged with user and time.

Never put clinical content (names, transcripts, note text) in `detail`: ids, counts and settings only.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base, now_column, session_scope


class AuditLog(Base):
    """Who did what, when. Never holds clinical content: ids, counts and settings only.

    `username` is deliberately not a foreign key: failed sign-ins record the name that was tried, which may not exist.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_encounter_id", "encounter_id"),
        Index("ix_audit_log_username_ts", "username", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ts: Mapped[datetime] = now_column()
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"))
    detail: Mapped[dict | None] = mapped_column(JSONB)


def audit(
    username: str | None,
    action: str,
    encounter_id: str | None = None,
    *,
    db: Session | None = None,
    **detail: Any,
) -> None:
    """Record an action. Pass `db` to join the caller's transaction; otherwise it commits on its own."""
    entry = AuditLog(username=username, action=action, encounter_id=encounter_id, detail=detail or None)
    if db is not None:
        db.add(entry)
        return
    with session_scope() as session:
        session.add(entry)
