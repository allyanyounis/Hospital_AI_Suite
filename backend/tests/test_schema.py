"""The normalised schema: migrations match the models, facts are stored once, and the database enforces its rules."""

from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.clock import to_aware
from app.core.database import Base, LegacySchemaError, engine, init_db, session_scope
from app.models import (
    Appointment,
    Encounter,
    EncounterCode,
    Patient,
    ScheduleBreak,
    ScheduleDay,
    StaffMember,
    VoiceCall,
    VoiceCallBooking,
)
from app.modules.appointments import booking
from app.modules.reception import parsing
from app.modules.scribe.repository import purge_expired_content
from tests.conftest import login
from tests.test_reception import NOW, book


@pytest.fixture
def frozen_clock(monkeypatch):
    for module in (booking, parsing):
        monkeypatch.setattr(module, "now_local", lambda: NOW)


def _count(model) -> int:
    with session_scope() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_migrations_match_the_models(client):
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, Base.metadata) == []


def test_start_refuses_a_database_with_the_old_schema(client):
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE clinic_schedule (id integer PRIMARY KEY)"))
    try:
        with pytest.raises(LegacySchemaError, match="old schema"):
            init_db()
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE clinic_schedule"))
    init_db()


# --- Receptionist ------------------------------------------------------------------------------------------------


def test_call_transcript_is_stored_once_and_returning_callers_are_one_patient(client, frozen_clock):
    assert book(client, "2026-11-03T10:00:00", name="Ali Khan")["success"]
    assert book(client, "2026-11-04T10:00:00", name="ali khan")["success"]  # same call, same caller
    report = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "call-1"},
            "artifact": {"messages": [{"role": "user", "message": "Two visits please."}]},
        }
    }
    assert client.post("/webhook", json=report).json() == {"status": "ok", "saved": 2}

    assert _count(VoiceCall) == 1 and _count(VoiceCallBooking) == 2 and _count(Patient) == 1
    login(client)
    assert [a["transcript"] for a in client.get("/api/appointments").json()] == ["User: Two visits please."] * 2


def _appointment(db, name: str, doctor: StaffMember, start: datetime, **kw) -> Appointment:
    return Appointment(patient=Patient(full_name=name), practitioner=doctor, start_time=start, booked_via="desk", **kw)


def test_database_rejects_a_second_active_booking_for_a_doctors_slot(client):
    start = to_aware(datetime(2026, 11, 3, 10, 0))
    with session_scope() as db:
        doctor = db.query(StaffMember).filter_by(username="drtest").one()
        other = db.query(StaffMember).filter_by(username="admin").one()
        db.add(_appointment(db, "A", doctor, start, canceled=True))
        db.add(_appointment(db, "B", doctor, start))  # a canceled one doesn't count
        db.add(_appointment(db, "C", other, start))  # another doctor, same time: fine
    with pytest.raises(IntegrityError), session_scope() as db:
        doctor = db.query(StaffMember).filter_by(username="drtest").one()
        db.add(_appointment(db, "D", doctor, start))


# --- Scribe ------------------------------------------------------------------------------------------------------


def _encounter_with_patient(client, mrn: str) -> str:
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]
    patient = {"name": "Shared Patient", "mrn": mrn, "sex": "Male", "dob": "1960-05-01", "visit_type": "Follow-up"}
    assert client.put(f"/api/encounters/{eid}/patient", json=patient).status_code == 200
    return eid


def _age(encounter_id: str) -> None:
    with session_scope() as db:
        db.get(Encounter, encounter_id).created_at = datetime(2000, 1, 1, tzinfo=UTC)


def test_patients_are_shared_by_mrn_and_erased_with_their_last_encounter(client):
    login(client)
    first, second = _encounter_with_patient(client, "MRN-9"), _encounter_with_patient(client, "MRN-9")
    assert _count(Patient) == 1

    client.post(f"/api/encounters/{first}/note", json={"template_id": "soap"})
    client.post(f"/api/encounters/{first}/codes")
    assert _count(EncounterCode) == 1

    _age(first)
    purge_expired_content(7)
    assert _count(Patient) == 1 and _count(EncounterCode) == 0  # still needed by the second encounter
    _age(second)
    purge_expired_content(7)
    assert _count(Patient) == 0


def test_patient_form_validates_and_blank_dob_is_stored_as_null(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]
    assert client.put(f"/api/encounters/{eid}/patient", json={"name": "X", "sex": "unknown"}).status_code == 422
    assert client.put(f"/api/encounters/{eid}/patient", json={"name": "X", "dob": "2026-13-40"}).status_code == 422
    assert client.put(f"/api/encounters/{eid}/patient", json={"name": "X", "dob": ""}).status_code == 200
    with session_scope() as db:
        assert db.get(Encounter, eid).patient.date_of_birth is None


# --- Schedule ----------------------------------------------------------------------------------------------------


def test_schedule_is_stored_as_rows(client):
    login(client, "admin")
    [doctor] = client.get("/api/staff?bookable=true").json()
    url = f"/api/schedules/{doctor['id']}"
    assert client.put(url, json=client.get(url).json()).status_code == 200
    assert _count(ScheduleDay) == 7 and _count(ScheduleBreak) == 7  # default lunch break kept on every day
    with pytest.raises(IntegrityError), session_scope() as db:
        day = db.query(ScheduleDay).filter_by(weekday=0).one()
        day.closes = day.opens  # an open day must close after it opens
