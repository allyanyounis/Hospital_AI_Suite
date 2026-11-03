"""Encounter storage helpers: create, open (with access and retention checks), patients, codes and tasks,
summarise and purge."""

from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.clock import now_utc
from app.core.database import session_scope
from app.modules.patients import delete_orphan_patients, resolve_patient

from .models import Encounter, EncounterCode, EncounterTask
from .notes import SavedCodes, SavedTasks
from .transcription import Transcript

# Erased by the retention purge (codes and tasks rows are deleted too); timings and edit counts stay for metrics
CLINICAL_CONTENT = dict(
    transcript=None,
    draft_note=None,
    final_note=None,
    patient_id=None,
    codes_source=None,
    codes_generated_at=None,
    tasks_source=None,
    tasks_generated_at=None,
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


# --- Patients ----------------------------------------------------------------------------------------------------


def assign_patient(
    db: Session, row: Encounter, name: str, mrn: str, sex: str, dob: date | None, visit_type: str
) -> None:
    """Link the encounter to the patient the form describes (see patients.resolve_patient)."""
    row.patient = resolve_patient(db, row.patient, name, mrn, sex, dob)
    row.visit_type = visit_type or None
    db.flush()
    delete_orphan_patients(db)  # e.g. the MRN-less patient this encounter pointed at before


# --- Codes and tasks ---------------------------------------------------------------------------------------------


def _generated_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(422, "generated_at must be an ISO date-time") from e


def store_codes(db: Session, row: Encounter, saved: SavedCodes) -> None:
    """Replace the encounter's code list (the old rows are deleted first so positions can be reused)."""
    row.codes.clear()
    db.flush()
    row.codes.extend(EncounterCode(position=i, **c.model_dump()) for i, c in enumerate(saved.codes))
    row.codes_source, row.codes_generated_at = saved.source, _generated_at(saved.generated_at)


def store_tasks(db: Session, row: Encounter, saved: SavedTasks) -> None:
    row.tasks.clear()
    db.flush()
    row.tasks.extend(EncounterTask(position=i, **t.model_dump()) for i, t in enumerate(saved.tasks))
    row.tasks_source, row.tasks_generated_at = saved.source, _generated_at(saved.generated_at)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")


def saved_codes(row: Encounter) -> dict | None:
    if row.codes_generated_at is None:
        return None
    codes = [{k: getattr(c, k) for k in ("code", "description", "kind", "confidence", "evidence")} for c in row.codes]
    return {"codes": codes, "source": row.codes_source, "generated_at": _iso(row.codes_generated_at)}


def saved_tasks(row: Encounter) -> dict | None:
    if row.tasks_generated_at is None:
        return None
    tasks = [{k: getattr(t, k) for k in ("title", "detail", "category", "owner", "due", "done")} for t in row.tasks]
    return {"tasks": tasks, "source": row.tasks_source, "generated_at": _iso(row.tasks_generated_at)}


# --- Listing, retention ------------------------------------------------------------------------------------------


def pipeline_status(row: Encounter) -> str:
    """pending (transcript only) -> drafting -> ready | failed -> signed."""
    if row.approved_at:
        return "signed"
    return row.note_status if row.note_status in ("drafting", "ready", "failed") else "pending"


def summary(row: Encounter) -> dict:
    patient = row.patient
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
            "name": patient.full_name if patient else "",
            "mrn": (patient.mrn if patient else None) or "",
            "sex": (patient.sex if patient else None) or "",
            "dob": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else "",
            "visit_type": row.visit_type or "",
        },
    }


def purge_expired_content(retention_days: int) -> int:
    """Erase clinical content older than the retention window. Returns how many encounters were purged."""
    cutoff = now_utc() - timedelta(days=retention_days)
    with session_scope() as db:
        expired = list(
            db.scalars(
                update(Encounter)
                .where(Encounter.created_at < cutoff, Encounter.content_purged_at.is_(None))
                .values(**CLINICAL_CONTENT, content_purged_at=now_utc())
                .returning(Encounter.id)
            )
        )
        purged = len(expired)
        if purged:
            db.execute(delete(EncounterCode).where(EncounterCode.encounter_id.in_(expired)))
            db.execute(delete(EncounterTask).where(EncounterTask.encounter_id.in_(expired)))
            delete_orphan_patients(db)
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
