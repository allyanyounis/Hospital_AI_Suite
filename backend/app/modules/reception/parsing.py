"""Reading VAPI tool calls and REST payloads: tool-call envelopes, patient names, dates and times.

Voice models send arguments in many shapes ("2 November", "tomorrow", "3pm", ISO with a stray "Z"...), so parsing is
deliberately tolerant. All results are naive clinic-local datetimes.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from app.core.clock import now_local

_TIME_FORMATS = ["%I:%M %p", "%I:%M%p", "%I %p", "%I%p", "%H:%M:%S", "%H:%M"]
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d %B %Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d %B",
    "%B %d",
    "%d %b",
    "%b %d",  # no year: assume this year
]
_DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

DATETIME_KEYS = [
    "start_time",
    "startTime",
    "appointment_datetime",
    "appointment_time_and_date",
    "datetime",
    "dateTime",
    "date_time",
    "start",
    "appointment_time",
    "slot",
]
DATE_KEYS = ["date", "appointment_date", "day", "target_date"]
TIME_KEYS = ["time", "appointment_time", "slot", "preferred_time", "time_slot"]
NAME_KEYS = [
    "patient_name",
    "patientName",
    "patient_full_name",
    "patientFullName",
    "full_name",
    "fullName",
    "name",
    "patient",
    "caller_name",
    "callerName",
    "user_name",
    "userName",
    "customer_name",
    "customerName",
    "client_name",
    "clientName",
]
REASON_KEYS = ["reason", "notes", "details"]
# Placeholders a voice model sometimes fills in instead of a real name
GENERIC_NAMES = {
    "",
    "none",
    "null",
    "undefined",
    "unknown",
    "n/a",
    "caller",
    "user",
    "me",
    "myself",
    "patient",
    "client",
    "general consultation",
}

DEFAULT_REASON = "General Consultation"


# --- Tool-call envelope ------------------------------------------------------------------------------------------


@dataclass
class ToolCall:
    args: dict = field(default_factory=dict)
    tool_call_id: str | None = None
    function_name: str | None = None
    call_id: str | None = None  # the VAPI call, used to attach the end-of-call transcript


def read_tool_call(body: Any) -> ToolCall:
    """Unwrap a VAPI webhook (message.toolCalls / toolCallList / toolWithToolCallList), a direct toolCall(s) body,
    or a plain REST body into its arguments."""
    if not isinstance(body, dict):
        return ToolCall()

    message = body.get("message") if isinstance(body.get("message"), dict) else None
    if message is not None:
        calls = (
            message.get("toolCalls")
            or message.get("toolCallList")
            or message.get("toolWithToolCallList")
            or message.get("tools")
        )
    elif isinstance(body.get("toolCalls"), list):
        calls = body["toolCalls"]
    elif isinstance(body.get("toolCallList"), list):
        calls = body["toolCallList"]
    elif isinstance(body.get("toolCall"), dict):
        calls = [body["toolCall"]]
    else:
        calls = None

    result = ToolCall(call_id=_call_id(body))
    if isinstance(calls, list) and calls and isinstance(calls[0], dict):
        first = calls[0]
        result.tool_call_id = first.get("id") or first.get("toolCallId")
        fn = first.get("function") if isinstance(first.get("function"), dict) else first
        result.function_name = fn.get("name")
        raw = fn.get("arguments") or fn.get("parameters") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        result.args = raw if isinstance(raw, dict) else {}
    else:
        result.args = dict(body)

    # Flatten one level of nested argument wrappers
    for key in ("parameters", "arguments", "input", "body", "properties"):
        if isinstance(result.args.get(key), dict):
            result.args = {**result.args, **result.args[key]}
    return result


def _call_id(body: dict) -> str | None:
    for container in (body.get("message"), body):
        if isinstance(container, dict) and isinstance(container.get("call"), dict) and container["call"].get("id"):
            return str(container["call"]["id"])
    return None


# --- Field extraction --------------------------------------------------------------------------------------------


def first_value(args: dict, keys: list[str]) -> Any:
    return next((args[k] for k in keys if args.get(k)), None)


def patient_name(args: Any) -> str | None:
    """The patient's name across naming conventions; searches nested objects and fuzzy keys as a fallback."""
    if not isinstance(args, dict):
        return None
    for key in NAME_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip().lower() not in GENERIC_NAMES:
            return value.strip()
    for key, value in args.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip().lower() not in GENERIC_NAMES:
            if any(term in key.lower() for term in ("name", "patient", "caller", "client", "customer")):
                return value.strip()
    for value in args.values():
        if isinstance(value, dict) and (nested := patient_name(value)):
            return nested
    return None


def reason(args: dict) -> str:
    return str(first_value(args, REASON_KEYS) or DEFAULT_REASON).strip()[:255]


def requested_datetime(args: dict) -> datetime | None:
    """The appointment time asked for, from a combined datetime or separate date + time fields."""
    raw_time = first_value(args, TIME_KEYS)
    raw = first_value(args, DATETIME_KEYS) or first_value(args, DATE_KEYS)
    if parsed := parse_datetime(raw, raw_time):
        return parsed
    for value in args.values():  # last resort: any string that looks like a date
        if isinstance(value, str) and (parsed := parse_datetime(value, raw_time)):
            return parsed
    return None


def requested_date(args: dict) -> date | None:
    raw = first_value(args, DATE_KEYS) or first_value(args, ["start_time", "startTime"])
    if parsed := parse_date(raw):
        return parsed
    if moment := requested_datetime(args):
        return moment.date()
    return None


# --- Value parsing -----------------------------------------------------------------------------------------------


def _relative_day(text: str) -> str:
    """Replace 'today' / 'tomorrow' with ISO dates."""
    today = now_local().date()
    text = re.sub(r"\btoday\b", today.isoformat(), text, flags=re.IGNORECASE)
    return re.sub(r"\btomorrow\b", (today + timedelta(days=1)).isoformat(), text, flags=re.IGNORECASE)


def parse_time(value: Any) -> time | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().upper()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(value: Any) -> date | None:
    """A date from a date/datetime object or text like '2026-11-02', '2nd November', 'Nov 2', 'tomorrow'."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = _relative_day(value.strip())
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
    text = text.split("T")[0] if re.match(r"^\d{4}-\d{2}-\d{2}T", text) else text
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        return parsed if "%Y" in fmt else parsed.replace(year=now_local().year)
    head = text.split(" ")[0]
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def parse_datetime(value: Any, time_value: Any = None) -> datetime | None:
    """A naive clinic-local datetime. A date without a time uses `time_value`, else noon.

    A trailing 'Z' is ignored on purpose: voice models append it by convention while meaning clinic-local time,
    and treating it as UTC would shift the requested hour.
    """
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, parse_time(time_value) or time(12, 0))
    if not isinstance(value, str) or not value.strip():
        return None
    text = _relative_day(value.strip()).rstrip("Zz")
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            return parsed.replace(tzinfo=None)
        if len(text) > 10:  # had a time part
            return parsed
    except ValueError:
        pass
    if day := parse_date(text):
        # "2026-11-02 3pm" style: a time after the date wins over a separate time field
        rest = text.split(" ", 1)[1] if " " in text and parse_date(text.split(" ")[0]) else None
        return datetime.combine(day, parse_time(rest) or parse_time(time_value) or time(12, 0))
    return None
