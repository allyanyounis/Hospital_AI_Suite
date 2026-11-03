"""Scribe API: capture -> draft -> safety check -> sign -> codes, tasks and letters, plus pilot metrics."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import audit
from ..clock import now_utc
from ..config import get_settings
from ..database import get_db, session_scope
from ..security import User, admin_user, current_user
from . import metrics
from .models import Encounter
from .notes import (
    DOCUMENT_TYPES,
    TEMPLATES,
    DocumentType,
    GeneratedDocument,
    GeneratedNote,
    NoteGenerationError,
    NoteGenerator,
    NoteReview,
    NoteTemplate,
    SavedCodes,
    SavedTasks,
    draft_note,
    get_note_generator,
    review_note,
    suggest_codes,
    suggest_tasks,
    write_document,
)
from .repository import create_encounter, open_encounter, purge_expired_content, summary
from .samples import get_sample, list_samples
from .transcription import Transcript, TranscriptionError, get_transcriber

router = APIRouter(prefix="/api", tags=["scribe"])
settings = get_settings()
log = logging.getLogger("hospital_ai.scribe")

MAX_AUDIO_BYTES = 50 * 1024 * 1024


class EncounterOut(BaseModel):
    id: str
    transcript: Transcript


class SampleRequest(BaseModel):
    sample_id: str


class NoteRequest(BaseModel):
    template_id: str
    clinician_speaker: int = 0


class NoteBody(BaseModel):
    note: GeneratedNote


class DocumentRequest(BaseModel):
    type_id: str


class PatientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mrn: str = Field(default="", max_length=60)
    sex: str = Field(default="", max_length=30)
    dob: str = Field(default="", max_length=20)
    visit_type: str = Field(default="", max_length=60)


def _generator() -> NoteGenerator:
    try:
        return get_note_generator(settings)
    except NoteGenerationError as e:
        raise HTTPException(503, str(e)) from e


def _template(template_id: str) -> NoteTemplate:
    template = TEMPLATES.get(template_id)
    if template is None:
        raise HTTPException(404, "Unknown template")
    return template


def save_new_encounter(db: Session, user: User, source: str, transcript: Transcript, **detail) -> EncounterOut:
    """Store a fresh transcript as an encounter (shared by sample, upload and live capture)."""
    purge_expired_content(settings.retention_days)
    encounter = create_encounter(db, user.username, source, transcript)
    audit(user.username, "encounter.created", encounter.id, db=db, source=source, **detail)
    db.commit()
    return EncounterOut(id=encounter.id, transcript=transcript)


# --- Reference data ----------------------------------------------------------------------------------------------


@router.get("/templates", response_model=list[NoteTemplate])
def templates(_: User = Depends(current_user)):
    return list(TEMPLATES.values())


@router.get("/document-types", response_model=list[DocumentType])
def document_types(_: User = Depends(current_user)):
    return list(DOCUMENT_TYPES.values())


@router.get("/samples")
def samples(_: User = Depends(current_user)):
    return list_samples()


# --- Capture -----------------------------------------------------------------------------------------------------


@router.post("/encounters/sample", response_model=EncounterOut)
def start_from_sample(req: SampleRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    transcript = get_sample(req.sample_id)
    if transcript is None:
        raise HTTPException(404, "Sample not found")
    return save_new_encounter(db, user, "sample", transcript, sample_id=req.sample_id)


@router.post("/encounters/recording", response_model=EncounterOut)
async def start_from_recording(audio: UploadFile, db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty recording")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Recording is too large (50 MB max)")
    # Audio stays in memory for this request only; it is never written to disk or the database
    try:
        mimetype = (audio.content_type or "audio/webm").split(";")[0]  # "audio/webm;codecs=opus" -> "audio/webm"
        transcript = await get_transcriber(settings).transcribe(data, mimetype)
    except TranscriptionError as e:
        audit(user.username, "transcription.failed")
        raise HTTPException(502, str(e)) from e
    if not transcript.segments:
        raise HTTPException(422, "No speech was detected in the recording")
    return save_new_encounter(
        db, user, "recording", transcript, transcriber=transcript.provider, audio_seconds=transcript.duration
    )


# --- Encounters --------------------------------------------------------------------------------------------------


@router.get("/encounters")
def encounters(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(
        select(Encounter).where(Encounter.username == user.username).order_by(Encounter.created_at.desc()).limit(500)
    )
    return [summary(r) for r in rows]


@router.get("/encounters/{encounter_id}")
def encounter_detail(encounter_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, transcript = open_encounter(db, encounter_id, user.username)
    return {
        **summary(row),
        "transcript": transcript.model_dump(),
        "draft_note": row.draft_note,
        "final_note": row.final_note,
        "codes": row.codes,
        "tasks": row.tasks,
    }


@router.put("/encounters/{encounter_id}/patient")
def set_patient(encounter_id: str, req: PatientIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    row.patient_name, row.patient_mrn, row.patient_sex = req.name.strip(), req.mrn.strip(), req.sex.strip()
    row.patient_dob, row.visit_type = req.dob.strip(), req.visit_type.strip()
    audit(user.username, "patient.updated", encounter_id, db=db)  # ids only, never the details themselves
    db.commit()
    return {"ok": True}


# --- Drafting ----------------------------------------------------------------------------------------------------


def _store_draft(row: Encounter, note: GeneratedNote, model: str, seconds: float) -> None:
    row.model, row.draft_note, row.draft_seconds = model, note.model_dump(), seconds
    row.drafted_at, row.note_status, row.note_error = now_utc(), "ready", None


@router.post("/encounters/{encounter_id}/note", response_model=GeneratedNote)
async def draft(encounter_id: str, req: NoteRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Draft the note and wait for it (the Board uses /note/start to draft in the background instead)."""
    row, transcript = open_encounter(db, encounter_id, user.username)
    template = _template(req.template_id)
    if row.approved_at:
        raise HTTPException(409, "This note is already signed")
    generator = _generator()
    started = time.perf_counter()
    try:
        note = await draft_note(generator, transcript, template, req.clinician_speaker)
    except NoteGenerationError as e:
        audit(user.username, "note.draft_failed", encounter_id, model=generator.model)
        raise HTTPException(502, str(e)) from e
    seconds = round(time.perf_counter() - started, 1)
    row.template_id, row.clinician_speaker = template.id, req.clinician_speaker
    _store_draft(row, note, generator.model, seconds)
    audit(
        user.username, "note.drafted", encounter_id, db=db, template=template.id, model=generator.model, seconds=seconds
    )
    db.commit()
    return note


_background_tasks: set[asyncio.Task] = set()


async def _draft_in_background(
    encounter_id: str, username: str, transcript: Transcript, template: NoteTemplate, clinician_speaker: int
) -> None:
    started, model = time.perf_counter(), None
    try:
        generator = get_note_generator(settings)
        model = generator.model
        note = await draft_note(generator, transcript, template, clinician_speaker)
    except Exception as e:  # any failure must land on the Board as "failed", never stay stuck in "drafting"
        log.warning("Background draft failed for %s: %s", encounter_id, e)
        message = str(e) if isinstance(e, NoteGenerationError) else "Note drafting failed"
        with session_scope() as db:
            row = db.get(Encounter, encounter_id)
            row.note_status, row.note_error = "failed", message[:300]
            audit(username, "note.draft_failed", encounter_id, db=db, model=model)
        return
    seconds = round(time.perf_counter() - started, 1)
    with session_scope() as db:
        _store_draft(db.get(Encounter, encounter_id), note, model, seconds)
        audit(username, "note.drafted", encounter_id, db=db, template=template.id, model=model, seconds=seconds)


@router.post("/encounters/{encounter_id}/note/start", status_code=202)
async def start_draft(
    encounter_id: str, req: NoteRequest, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    row, transcript = open_encounter(db, encounter_id, user.username)
    template = _template(req.template_id)
    if row.approved_at:
        raise HTTPException(409, "This note is already signed")
    if row.note_status == "drafting":
        return {"status": "drafting"}
    _generator()  # fail fast with 503 if no model is configured
    row.template_id, row.clinician_speaker = template.id, req.clinician_speaker
    row.note_status, row.note_error = "drafting", None
    db.commit()
    task = asyncio.create_task(
        _draft_in_background(encounter_id, user.username, transcript, template, req.clinician_speaker)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "drafting"}


# --- Safety check, sign-off, letters -----------------------------------------------------------------------------


@router.post("/encounters/{encounter_id}/review", response_model=NoteReview)
async def review(encounter_id: str, req: NoteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, transcript = open_encounter(db, encounter_id, user.username)
    generator = _generator()
    try:
        result = await review_note(generator, transcript, req.note, row.clinician_speaker, settings.review_effort)
    except NoteGenerationError as e:
        raise HTTPException(502, str(e)) from e
    severities = [f.severity for f in result.findings]
    audit(
        user.username,
        "note.reviewed",
        encounter_id,
        findings=len(severities),
        high=severities.count("high"),
        model=generator.model,
    )
    return result


@router.post("/encounters/{encounter_id}/approve")
def approve(encounter_id: str, req: NoteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    if row.draft_note is None:
        raise HTTPException(409, "Draft a note before approving")
    counts = metrics.edit_counts(GeneratedNote.model_validate(row.draft_note), req.note)
    reapproval = row.approved_at is not None
    row.final_note, row.approved_at = req.note.model_dump(), now_utc()
    for key, value in counts.items():
        setattr(row, key, value)
    audit(user.username, "note.approved", encounter_id, db=db, reapproval=reapproval, **counts)
    db.commit()
    return counts


@router.post("/encounters/{encounter_id}/documents", response_model=GeneratedDocument)
async def document(
    encounter_id: str, req: DocumentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    row, _ = open_encounter(db, encounter_id, user.username)
    doc_type = DOCUMENT_TYPES.get(req.type_id)
    if doc_type is None:
        raise HTTPException(404, "Unknown document type")
    if row.final_note is None:
        raise HTTPException(409, "Approve the note first; documents are written from the approved note")
    generator = _generator()
    try:
        doc = await write_document(generator, doc_type, GeneratedNote.model_validate(row.final_note))
    except NoteGenerationError as e:
        raise HTTPException(502, str(e)) from e
    audit(user.username, "document.generated", encounter_id, type=doc_type.id, model=generator.model)
    return doc


# --- Clinical codes & task list: suggested from the signed note (or the draft), then owned by the clinician ---------


def _note_for_extras(row: Encounter) -> tuple[GeneratedNote, str]:
    if row.final_note:
        return GeneratedNote.model_validate(row.final_note), "signed"
    if row.draft_note:
        return GeneratedNote.model_validate(row.draft_note), "draft"
    raise HTTPException(409, "Generate the note first")


@router.post("/encounters/{encounter_id}/codes", response_model=SavedCodes)
async def generate_codes(encounter_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    note, source = _note_for_extras(row)
    generator = _generator()
    try:
        codes = await suggest_codes(generator, note)
    except NoteGenerationError as e:
        raise HTTPException(502, str(e)) from e
    saved = SavedCodes(codes=codes, source=source, generated_at=now_utc().isoformat(timespec="seconds"))
    row.codes = saved.model_dump()
    audit(user.username, "codes.generated", encounter_id, db=db, count=len(codes), source=source, model=generator.model)
    db.commit()
    return saved


@router.put("/encounters/{encounter_id}/codes", response_model=SavedCodes)
def save_codes(encounter_id: str, req: SavedCodes, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    row.codes = req.model_dump()
    audit(user.username, "codes.edited", encounter_id, db=db, count=len(req.codes))
    db.commit()
    return req


@router.post("/encounters/{encounter_id}/tasks", response_model=SavedTasks)
async def generate_tasks(encounter_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    note, source = _note_for_extras(row)
    generator = _generator()
    try:
        tasks = await suggest_tasks(generator, note)
    except NoteGenerationError as e:
        raise HTTPException(502, str(e)) from e
    saved = SavedTasks(tasks=tasks, source=source, generated_at=now_utc().isoformat(timespec="seconds"))
    row.tasks = saved.model_dump()
    audit(user.username, "tasks.generated", encounter_id, db=db, count=len(tasks), source=source, model=generator.model)
    db.commit()
    return saved


@router.put("/encounters/{encounter_id}/tasks", response_model=SavedTasks)
def save_tasks(encounter_id: str, req: SavedTasks, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row, _ = open_encounter(db, encounter_id, user.username)
    row.tasks = req.model_dump()
    audit(user.username, "tasks.edited", encounter_id, db=db, count=len(req.tasks), done=sum(t.done for t in req.tasks))
    db.commit()
    return req


# --- Pilot metrics -----------------------------------------------------------------------------------------------


@router.get("/metrics")
def my_metrics(days: int = 30, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return metrics.compute(db, settings, user.username, days)


@router.get("/metrics/all")
def all_metrics(days: int = 30, db: Session = Depends(get_db), user: User = Depends(admin_user)):
    audit(user.username, "metrics.viewed_all")
    return metrics.compute(db, settings, None, days)
