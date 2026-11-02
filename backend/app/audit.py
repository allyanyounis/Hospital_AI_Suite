"""Audit trail. Every sign-in, clinical action and booking is logged with user and time.

Never put clinical content (names, transcripts, note text) in `detail`: ids, counts and settings only.
"""

from typing import Any

from sqlalchemy.orm import Session

from .database import session_scope
from .models import AuditLog


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
