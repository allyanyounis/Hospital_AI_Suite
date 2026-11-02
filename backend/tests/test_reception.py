"""AI receptionist: VAPI tool-call parsing, booking rules, cancelling, transcripts, and what the public API exposes."""

from datetime import datetime

import pytest

from app.clock import to_aware
from app.reception import booking, parsing
from tests.conftest import login

# Monday 2 November 2026, 08:00 clinic time. Default schedule: Mon-Fri 09:00-17:00, lunch 13:00-14:00, 15-min slots.
NOW = datetime(2026, 11, 2, 8, 0)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    for module in (booking, parsing):
        monkeypatch.setattr(module, "now_local", lambda: NOW)


def vapi(function: str, **args) -> dict:
    """A VAPI webhook body carrying one tool call."""
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call-1"},
            "toolCalls": [{"id": "tc-1", "function": {"name": function, "arguments": args}}],
        }
    }


def book(client, when: str, name: str = "Ali Khan", **extra) -> dict:
    return client.post("/vapi", json=vapi("book_appointment", patient_name=name, start_time=when, **extra)).json()


# --- Parsing -----------------------------------------------------------------------------------------------------


def test_parses_the_shapes_voice_models_send():
    assert parsing.parse_date("2nd November") == datetime(2026, 11, 2).date()
    assert parsing.parse_date("tomorrow") == datetime(2026, 11, 3).date()
    assert parsing.parse_datetime("2026-11-03T15:30:00Z") == datetime(2026, 11, 3, 15, 30)  # 'Z' means clinic time
    assert parsing.parse_datetime("2026-11-03", "3pm") == datetime(2026, 11, 3, 15, 0)
    assert parsing.parse_datetime("tomorrow 10:30 AM") == datetime(2026, 11, 3, 10, 30)
    assert parsing.patient_name({"name": "caller", "patientFullName": "Sara Ahmed"}) == "Sara Ahmed"

    call = parsing.read_tool_call(
        {
            "message": {
                "call": {"id": "c9"},
                "toolCallList": [{"id": "t1", "function": {"name": "cancel", "arguments": '{"date": "2026-11-04"}'}}],
            }
        }
    )
    assert (call.tool_call_id, call.function_name, call.call_id, call.args) == (
        "t1",
        "cancel",
        "c9",
        {"date": "2026-11-04"},
    )


# --- Booking rules -----------------------------------------------------------------------------------------------


def test_books_a_valid_slot_and_reports_it_to_the_agent(client):
    reply = book(client, "2026-11-03T10:00:00", reason="Chest pain")
    assert reply["success"] and reply["results"][0]["toolCallId"] == "tc-1"
    assert "Appointment confirmed for Ali Khan on November 03, 2026 at 10:00 AM" in reply["results"][0]["result"]


@pytest.mark.parametrize(
    "when, expected",
    [
        ("2026-11-03T10:10:00", "not a valid slot"),  # off the 15-minute grid
        ("2026-11-03T13:15:00", "on a break"),  # lunch
        ("2026-11-03T18:00:00", "outside clinic hours"),
        ("2026-11-07T10:00:00", "closed on Saturdays"),
        ("2026-10-30T10:00:00", "in the past"),  # last Friday
        ("2026-11-20T10:00:00", "up to 10 days in advance"),
    ],
)
def test_rejects_times_the_clinic_cannot_take(client, when, expected):
    reply = book(client, when)
    assert not reply["success"] and expected in reply["result"]


def test_offers_nearest_free_slots_when_taken(client):
    assert book(client, "2026-11-03T10:00:00", name="First Patient")["success"]
    reply = book(client, "2026-11-03T10:00:00", name="Second Patient")
    assert "already booked" in reply["result"] and "9:45 AM and 10:15 AM" in reply["result"]


def test_holidays_from_the_scheduler_block_bookings(client):
    login(client)
    schedule = client.get("/api/schedule").json()
    schedule["holidays"] = ["2026-11-04"]
    assert client.put("/api/schedule", json=schedule).status_code == 200
    assert "holiday" in book(client, "2026-11-04T10:00:00")["result"]


def test_cancel_by_name_and_date(client):
    book(client, "2026-11-03T11:00:00", name="Sara Ahmed")
    reply = client.post("/cancel_appointment", json=vapi("cancel", patient_name="sara", date="2026-11-03")).json()
    assert reply["success"] and reply["canceled_count"] == 1
    again = client.post("/vapi", json=vapi("cancel_appointment", patient_name="Sara", date="2026-11-03")).json()
    assert again["status"] == "not_found"
    assert book(client, "2026-11-03T11:00:00", name="Someone Else")["success"]  # the slot is free again


# --- What is exposed ---------------------------------------------------------------------------------------------


def test_public_availability_never_lists_patients(client):
    book(client, "2026-11-03T09:00:00", name="Private Person")
    for reply in (
        client.get("/list_appointments?date=2026-11-03").json(),
        client.post("/vapi", json=vapi("check_availability", date="2026-11-03")).json(),
    ):
        assert "Private Person" not in str(reply)
        assert "9:00 AM" not in reply["available_slots"] and "9:15 AM" in reply["available_slots"]


def test_dashboard_lists_and_cancels_with_sign_in(client):
    book(client, "2026-11-03T09:30:00", name="Dashboard Patient")
    assert client.get("/api/reception/appointments").status_code == 401
    login(client)
    [appt] = client.get("/api/reception/appointments").json()
    assert appt["patient_name"] == "Dashboard Patient"
    assert datetime.fromisoformat(appt["start_time"]) == to_aware(datetime(2026, 11, 3, 9, 30))
    assert client.post(f"/api/reception/appointments/{appt['id']}/cancel").json()["canceled"] is True


def test_end_of_call_report_attaches_the_transcript(client):
    book(client, "2026-11-03T12:00:00", name="Caller Patient")  # booked during call-1
    report = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "call-1"},
            "artifact": {
                "messages": [
                    {"role": "system", "message": "secret prompt"},
                    {"role": "bot", "message": "Hello, how can I help?"},
                    {"role": "user", "message": "Book me tomorrow at noon."},
                ]
            },
        }
    }
    assert client.post("/webhook", json=report).json() == {"status": "ok", "saved": 1}
    login(client)
    [appt] = client.get("/api/reception/appointments").json()
    assert appt["transcript"] == "AI: Hello, how can I help?\nUser: Book me tomorrow at noon."


def test_vapi_secret_is_enforced_when_set(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "vapi_secret", "s3cret")
    assert client.post("/vapi", json=vapi("check_availability")).status_code == 401
    assert client.post("/vapi", json=vapi("check_availability"), headers={"x-vapi-secret": "s3cret"}).status_code == 200
