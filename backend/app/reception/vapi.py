"""Public webhook endpoints called by the VAPI voice agent (book, cancel, check availability, end-of-call report).

These cannot use staff sign-in, so they never return other patients' details: availability answers contain free
times only. Set VAPI_SECRET (and the same secret in the VAPI dashboard) to reject calls that don't come from VAPI.

Every reply is HTTP 200 with the sentence in `results[0].result`, so the agent reads the explanation to the caller.
The URL paths match the original receptionist so the existing VAPI assistant keeps working unchanged.
"""

import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..audit import audit
from ..config import get_settings
from ..database import get_db
from ..schedule import load_schedule
from . import booking, parsing
from .events import broadcaster

log = logging.getLogger("hospital_ai.vapi")


def verify_vapi_secret(request: Request) -> None:
    secret = get_settings().vapi_secret
    if secret and not hmac.compare_digest(request.headers.get("x-vapi-secret", ""), secret):
        raise HTTPException(401, "Invalid webhook secret")


router = APIRouter(tags=["vapi webhooks"], dependencies=[Depends(verify_vapi_secret)])


def tool_reply(call: parsing.ToolCall, message: str, success: bool = False, status: str | None = None, **extra) -> dict:
    """A reply readable by both VAPI tools and plain REST clients."""
    return {
        "success": success,
        "status": status or ("success" if success else "error"),
        "message": message,
        "result": message,
        "results": [{"toolCallId": call.tool_call_id or "tool_call_result", "result": message}],
        **extra,
    }


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


# --- Actions -----------------------------------------------------------------------------------------------------


async def _schedule(call: parsing.ToolCall, db: Session) -> dict:
    name = parsing.patient_name(call.args)
    start = parsing.requested_datetime(call.args)
    if not name:
        return tool_reply(call, "Patient name is required to book an appointment.")
    if not start:
        return tool_reply(call, "A valid appointment date and time is required.")

    result = booking.book(db, load_schedule(db), name, parsing.reason(call.args), start, call.call_id)
    if not result.ok:
        return tool_reply(call, result.message)
    audit(None, "appointment.booked", db=db, appointment_id=result.appointment.id, source="voice")
    db.commit()
    await broadcaster.publish("appointment_booked")
    a = result.appointment
    return tool_reply(call, result.message, success=True, id=a.id, start_time=a.start_time.isoformat())


async def _cancel(call: parsing.ToolCall, db: Session) -> dict:
    on = parsing.requested_date(call.args)
    if not on:
        return tool_reply(call, "Please specify the date of the appointment you wish to cancel.", canceled_count=0)
    at = parsing.parse_time(parsing.first_value(call.args, ["time"]))
    result = booking.cancel(db, parsing.patient_name(call.args), on, at)
    if not result.ok:
        return tool_reply(call, result.message, status=result.status, canceled_count=0)
    audit(None, "appointment.canceled", db=db, count=result.canceled_count, source="voice")
    db.commit()
    await broadcaster.publish("appointment_canceled")
    return tool_reply(call, result.message, success=True, canceled_count=result.canceled_count)


def _availability(call: parsing.ToolCall, db: Session) -> dict:
    on = parsing.parse_date(call.args.get("date") or call.args.get("start_time"))
    schedule = load_schedule(db)
    summary, free = booking.availability_summary(db, schedule, on)
    return tool_reply(
        call,
        summary,
        success=True,
        summary=summary,
        available_slots=free,
        slot_duration_minutes=schedule.slot_minutes,
        doctor_available_hours=booking.schedule_text(schedule),
    )


# --- Routes ------------------------------------------------------------------------------------------------------


async def schedule_appointment(request: Request, db: Session = Depends(get_db)):
    return await _schedule(parsing.read_tool_call(await _body(request)), db)


async def cancel_appointment(request: Request, db: Session = Depends(get_db)):
    return await _cancel(parsing.read_tool_call(await _body(request)), db)


async def check_availability(request: Request, date: str | None = None, db: Session = Depends(get_db)):
    call = parsing.read_tool_call(await _body(request)) if request.method == "POST" else parsing.ToolCall()
    if date:
        call.args["date"] = date
    return _availability(call, db)


async def webhook(request: Request, db: Session = Depends(get_db)):
    """Server URL for the whole assistant: routes tool calls by function name and stores end-of-call transcripts."""
    body = await _body(request)
    message = body.get("message") if isinstance(body.get("message"), dict) else {}
    if message.get("type") == "end-of-call-report":
        saved = booking.attach_call_transcript(db, message)
        db.commit()
        if saved:
            await broadcaster.publish("transcript_saved")
        return {"status": "ok", "saved": saved}

    call = parsing.read_tool_call(body)
    name = (call.function_name or "").lower()
    if not call.tool_call_id and not name:
        return {"status": "ok", "message": "Hospital AI Suite is running"}
    if "schedule" in name or "book" in name:
        return await _schedule(call, db)
    if "cancel" in name:
        return await _cancel(call, db)
    if any(word in name for word in ("availab", "list", "doctor")):
        return _availability(call, db)
    log.warning("Unrecognised VAPI function %r", call.function_name)
    return tool_reply(call, "Function not recognized.")


def _register(handler, paths: list[str], methods: list[str]) -> None:
    for i, path in enumerate(paths):
        router.add_api_route(path, handler, methods=methods, include_in_schema=i == 0)


# Canonical path first; the rest are the original receptionist's URLs (incl. its typo) kept for existing assistants
_register(webhook, ["/vapi", "/webhook", "/"], ["POST"])
_register(
    schedule_appointment, ["/vapi/schedule_appointment", "/schedule_appointment", "/schedule_appointment/"], ["POST"]
)
_register(
    cancel_appointment,
    [
        "/vapi/cancel_appointment",
        "/cancel_appointment",
        "/cancel_appointment/",
        "/cancel_appointments",
        "/cancel_appointments/",
    ],
    ["POST"],
)
_register(
    check_availability,
    [
        "/vapi/check_availability",
        "/check_doctor_availability",
        "/check_doctor_availability/",
        "/check_doctor_availabilty",
        "/check_doctor_availabilty/",
        "/doctor_availability",
        "/doctor_availability/",
        "/list_appointments",
        "/list_appointments/",
    ],
    ["GET", "POST"],
)
