"""Encounter storage helpers: create, open (with access and retention checks), summarise and purge."""

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..audit import audit
from ..clock import now_utc
from ..database import session_scope
from .models import Encounter
from .transcription import Transcript

# Erased by the retention purge; timings and edit counts stay for metrics
CLINICAL_CONTENT = dict(
    transcript=None,
    draft_note=None,
    final_note=None,
    codes=None,
    tasks=None,
    patient_name=None,
    patient_mrn=None,
    patient_sex=None,
    patient_dob=None,
)


def create_encounter(db: Session, username: str, source: str, transcript: Transcript) -> Encounter:
    encounter = Encounter(
        username=username, source=source, transcript=transcript.model_dump(), audio_seconds=transcript.duration
    )
    db.add(encounter)
    db.flush()
    return encounter


def open_encounter(db: Session, encounter_id: str, username: str) -> tuple[Encounter, Transcript]:
    """Load one of the user's encounters with its transcript. Clinicians can only open their own."""
    row = db.get(Encounter, encounter_id)
    if row is None or row.username != username:
        raise HTTPException(404, "Encounter not found")
    if row.transcript is None:
        raise HTTPException(410, "This encounter's content was erased under the retention policy")
    return row, Transcript.model_validate(row.transcript)


def pipeline_status(row: Encounter) -> str:
    """pending (transcript only) -> drafting -> ready | failed -> signed."""
    if row.approved_at:
        return "signed"
    return row.note_status if row.note_status in ("drafting", "ready", "failed") else "pending"


def summary(row: Encounter) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at,
        "source": row.source,
        "audio_seconds": row.audio_seconds,
        "template_id": row.template_id,
        "clinician_speaker": row.clinician_speaker,
        "status": pipeline_status(row),
        "error": row.note_error,
        "approved_at": row.approved_at,
        "purged": row.content_purged_at is not None,
        "patient": {
            "name": row.patient_name or "",
            "mrn": row.patient_mrn or "",
            "sex": row.patient_sex or "",
            "dob": row.patient_dob or "",
            "visit_type": row.visit_type or "",
        },
    }


def purge_expired_content(retention_days: int) -> int:
    """Erase clinical content older than the retention window. Returns how many encounters were purged."""
    cutoff = now_utc() - timedelta(days=retention_days)
    with session_scope() as db:
        purged = db.execute(
            update(Encounter)
            .where(Encounter.created_at < cutoff, Encounter.content_purged_at.is_(None))
            .values(**CLINICAL_CONTENT, content_purged_at=now_utc())
        ).rowcount
        if purged:
            audit(None, "retention.purge", db=db, count=purged, retention_days=retention_days)
    return purged


def recover_interrupted_drafts() -> None:
    """A draft that was running when the server stopped will never finish; mark it failed so it can be retried."""
    with session_scope() as db:
        db.execute(
            update(Encounter)
            .where(Encounter.note_status == "drafting")
            .values(note_status="failed", note_error="Interrupted by a server restart")
        )
