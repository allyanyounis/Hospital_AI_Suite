"""Voice-call facts: who is calling, the calls themselves, which bookings they made, and their transcripts."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.appointments import Appointment
from app.modules.patients import Patient

from .models import VoiceCall, VoiceCallBooking

# --- Callers -----------------------------------------------------------------------------------------------------


def caller_number(body: dict) -> str | None:
    """The caller's phone number from a VAPI payload (message.call.customer.number), if VAPI sent one."""
    message = body.get("message") if isinstance(body.get("message"), dict) else body
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    customer = call.get("customer") if isinstance(call.get("customer"), dict) else {}
    number = customer.get("number")
    return str(number).strip() or None if number else None


def caller_patient(db: Session, name: str, phone: str | None = None) -> Patient:
    """The patient a caller is booking for.

    A known phone number identifies the patient (when the name agrees). Otherwise a returning caller is recognised
    by the same name on an earlier appointment; patients known only to the scribe are never matched by name.
    """
    if phone:
        by_phone = db.scalar(
            select(Patient).where(Patient.phone == phone, func.lower(Patient.full_name) == name.lower()).limit(1)
        )
        if by_phone:
            return by_phone
    has_booked = select(Appointment.id).where(Appointment.patient_id == Patient.id).exists()
    existing = db.scalar(
        select(Patient).where(func.lower(Patient.full_name) == name.lower(), has_booked).order_by(Patient.id).limit(1)
    )
    if existing:
        if phone and not existing.phone:
            existing.phone = phone
        return existing
    return Patient(full_name=name, phone=phone)


# --- Calls and bookings ------------------------------------------------------------------------------------------


def voice_call(db: Session, call_id: str) -> VoiceCall:
    call = db.get(VoiceCall, call_id)
    if call is None:
        call = VoiceCall(id=call_id)
        db.add(call)
        db.flush()
    return call


def link_booking(db: Session, call_id: str, appointment: Appointment) -> None:
    voice_call(db, call_id)
    db.add(VoiceCallBooking(call_id=call_id, appointment_id=appointment.id))


def transcripts_for(db: Session, appointment_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Appointment detail provider (registered with the appointments module): each booking's call transcript."""
    rows = db.execute(
        select(VoiceCallBooking.appointment_id, VoiceCall.transcript)
        .join(VoiceCall, VoiceCall.id == VoiceCallBooking.call_id)
        .where(VoiceCallBooking.appointment_id.in_(appointment_ids))
    ).all()
    found = dict(rows)
    return {i: {"transcript": found.get(i)} for i in appointment_ids}


# --- End-of-call report ------------------------------------------------------------------------------------------


def format_call_transcript(report: dict) -> str | None:
    """'AI: ...' / 'User: ...' lines from an end-of-call report (skips system prompt and tool messages)."""
    artifact = report.get("artifact") if isinstance(report.get("artifact"), dict) else {}
    messages = artifact.get("messages") or report.get("messages") or []
    lines = []
    for m in messages if isinstance(messages, list) else []:
        if not isinstance(m, dict) or m.get("role") not in ("bot", "assistant", "user"):
            continue
        text = (m.get("message") or m.get("content") or "").strip()
        if text:
            lines.append(f"{'User' if m['role'] == 'user' else 'AI'}: {text}")
    if lines:
        return "\n".join(lines)
    fallback = artifact.get("transcript") or report.get("transcript")
    return fallback.strip() if isinstance(fallback, str) and fallback.strip() else None


def _parse_iso(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def attach_call_transcript(db: Session, report: dict) -> int:
    """Save the call's transcript (once, on the call) and link the appointments booked during it.
    Returns how many appointments the transcript now belongs to."""
    call = report.get("call") if isinstance(report.get("call"), dict) else {}
    call_id = call.get("id")
    transcript = format_call_transcript(report)
    if not call_id or not transcript:
        return 0

    started = _parse_iso(report.get("startedAt") or call.get("startedAt") or call.get("createdAt"))
    ended = _parse_iso(report.get("endedAt") or call.get("endedAt"))
    row = voice_call(db, str(call_id))
    row.transcript, row.started_at, row.ended_at = transcript, started or row.started_at, ended or row.ended_at

    linked = list(db.scalars(select(VoiceCallBooking.appointment_id).where(VoiceCallBooking.call_id == row.id)))
    if not linked and started:
        # "API Request" tools don't send the call id, so match voice bookings made while the call was running
        margin = timedelta(minutes=1)
        unlinked = (
            ~select(VoiceCallBooking.appointment_id).where(VoiceCallBooking.appointment_id == Appointment.id).exists()
        )
        query = select(Appointment).where(
            Appointment.booked_via == "voice", Appointment.created_at >= started - margin, unlinked
        )
        if ended:
            query = query.where(Appointment.created_at <= ended + margin)
        for appointment in db.scalars(query).unique():
            db.add(VoiceCallBooking(call_id=row.id, appointment_id=appointment.id))
            linked.append(appointment.id)
    return len(linked)
