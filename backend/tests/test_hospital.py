"""Hospital foundation: departments, staff, roles, per-doctor booking (desk and voice), patient registry."""

from datetime import UTC, datetime

import pytest

from app.core.database import session_scope
from app.models import Encounter, Patient
from app.modules.appointments import booking
from app.modules.auth.cli import save_user
from app.modules.reception import parsing
from app.modules.scribe.repository import purge_expired_content
from app.modules.staff import save_profile
from app.modules.staff.schemas import StaffProfileIn
from tests.conftest import PASSWORD, login
from tests.test_reception import NOW, vapi

# Monday 2 November 2026, 08:00 hospital time (see test_reception)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    for module in (booking, parsing):
        monkeypatch.setattr(module, "now_local", lambda: NOW)


@pytest.fixture
def cardiology(client) -> dict:
    """A second department with a second bookable doctor, Dr. Sara Heart."""
    login(client, "admin")
    dept = client.post("/api/departments", json={"code": "card", "name": "Cardiology"}).json()
    save_user("drheart", "Dr. Sara Heart", "doctor", PASSWORD)
    profile = {"department_id": dept["id"], "job_title": "Consultant", "specialty": "Cardiology", "bookable": True}
    doctor = client.put("/api/staff/drheart", json=profile).json()
    client.post("/api/logout")
    return {"department": dept, "doctor": doctor}


def _staff(role: str, username: str) -> None:
    save_user(username, username.title(), role, PASSWORD)
    with session_scope() as db:
        save_profile(db, None, username, StaffProfileIn(department_id=1, job_title=role.title()))


# --- Organisation and staff --------------------------------------------------------------------------------------


def test_departments_and_staff_profiles(client, cardiology):
    assert cardiology["department"]["code"] == "CARD"  # codes are upper-cased
    assert cardiology["doctor"]["department"]["name"] == "Cardiology" and cardiology["doctor"]["bookable"]

    login(client, "admin")
    assert client.post("/api/departments", json={"code": "CARD", "name": "Other"}).status_code == 409
    counts = {d["code"]: d["staff_count"] for d in client.get("/api/departments").json()}
    assert counts == {"CARD": 1, "GEN": 2}
    dept_id = cardiology["department"]["id"]
    assert client.patch(f"/api/departments/{dept_id}", json={"active": False}).json()["active"] is False

    save_user("ali", "Ali", "patient", PASSWORD, mrn="P-1")
    assert client.put("/api/staff/ali", json={"department_id": dept_id}).status_code == 422  # patients aren't staff
    reg = {"department_id": dept_id, "registration_number": "PMC-1"}
    assert client.put("/api/staff/drheart", json=reg).status_code == 200
    assert client.put("/api/staff/drtest", json=reg).status_code == 409  # registration numbers are unique

    client.post("/api/logout")
    login(client)  # doctors read the directory and departments, but can't change them
    assert len(client.get("/api/staff").json()) == 3
    assert client.post("/api/departments", json={"code": "X1", "name": "X"}).status_code == 403
    assert client.put("/api/staff/drtest", json=reg).status_code == 403


def test_nurse_and_receptionist_access(client):
    _staff("nurse", "nina")
    _staff("receptionist", "rita")

    login(client, "nina")
    assert client.get("/api/patients").status_code == 200
    assert client.get("/api/appointments").status_code == 200
    assert client.post("/api/patients", json={"full_name": "X"}).status_code == 403
    assert client.get("/api/encounters").status_code == 403  # no AI scribe
    client.post("/api/logout")

    login(client, "rita")
    assert client.post("/api/patients", json={"full_name": "Walk In", "phone": "+92300"}).status_code == 201
    assert client.get("/api/encounters").status_code == 403
    assert client.get("/api/users").status_code == 403


# --- Patient registry --------------------------------------------------------------------------------------------


def test_patient_registry_search_register_update(client):
    login(client, "admin")
    body = {
        "full_name": "Fatima Noor",
        "mrn": "MRN-55",
        "sex": "Female",
        "date_of_birth": "1990-05-01",
        "phone": "0300-1",
    }
    created = client.post("/api/patients", json=body).json()
    assert created["has_account"] is False and created["date_of_birth"] == "1990-05-01"
    assert client.post("/api/patients", json={**body, "full_name": "Other"}).status_code == 409  # MRN taken
    for q in ("fatima", "MRN-55", "0300"):
        assert [p["id"] for p in client.get(f"/api/patients?q={q}").json()] == [created["id"]], q
    updated = client.patch(f"/api/patients/{created['id']}", json={"email": "f@example.org", "phone": ""}).json()
    assert (updated["email"], updated["phone"], updated["mrn"]) == ("f@example.org", "", "MRN-55")


def test_registered_patients_survive_the_retention_purge(client):
    login(client, "admin")
    registered = client.post("/api/patients", json={"full_name": "Kept"}).json()
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]
    client.put(f"/api/encounters/{eid}/patient", json={"name": "Provisional"})
    with session_scope() as db:
        db.get(Encounter, eid).created_at = datetime(2000, 1, 1, tzinfo=UTC)
    purge_expired_content(7)
    with session_scope() as db:
        assert [p.full_name for p in db.query(Patient)] == ["Kept"]
        assert db.get(Patient, registered["id"]) is not None


# --- Booking per doctor ------------------------------------------------------------------------------------------


def test_desk_booking_is_per_doctor(client, cardiology):
    login(client, "admin")
    patient = client.post("/api/patients", json={"full_name": "Desk Patient"}).json()
    [gen_doctor] = [d for d in client.get("/api/staff?bookable=true").json() if d["username"] == "drtest"]
    slots = client.get(f"/api/appointments/availability?practitioner_id={gen_doctor['id']}&date=2026-11-03").json()
    assert slots["slots"][0] == "09:00" and "13:00" not in slots["slots"]

    def desk(doctor_id: int, start: str = "2026-11-03T10:00", patient_id: int | None = None):
        body = {"patient_id": patient_id or patient["id"], "practitioner_id": doctor_id, "start_time": start}
        return client.post("/api/appointments", json={**body, "reason": "Review"})

    first = desk(gen_doctor["id"])
    assert first.status_code == 201 and first.json()["booked_via"] == "desk"
    other = client.post("/api/patients", json={"full_name": "Second"}).json()
    clash = desk(gen_doctor["id"], patient_id=other["id"])
    assert clash.status_code == 422 and "already booked" in clash.json()["detail"]
    cardiologist = cardiology["doctor"]["id"]
    assert desk(cardiologist, patient_id=other["id"]).status_code == 201  # another doctor at the same time: fine
    twice = desk(cardiologist)  # but one patient can't see two doctors at once
    assert twice.status_code == 422 and "already has an appointment" in twice.json()["detail"]
    slots = client.get(f"/api/appointments/availability?practitioner_id={gen_doctor['id']}&date=2026-11-03").json()
    assert "10:00" not in slots["slots"]

    by_dept = client.get(f"/api/appointments?department_id={cardiology['department']['id']}").json()
    assert [a["practitioner"]["department"] for a in by_dept] == ["Cardiology"]

    client.post("/api/logout")
    login(client)  # doctors can't book at the desk
    assert desk(gen_doctor["id"], "2026-11-03T11:00").status_code == 403


def test_voice_agent_asks_which_doctor_when_there_are_several(client, cardiology):
    asked = client.post("/vapi", json=vapi("book_appointment", patient_name="Ali", start_time="2026-11-03T10:00:00"))
    reply = asked.json()
    assert reply["status"] == "needs_doctor" and "Dr. Sara Heart (Cardiology)" in reply["result"]

    by_department = vapi(
        "book_appointment", patient_name="Ali", start_time="2026-11-03T10:00:00", department="cardiology"
    )
    assert "with Dr. Sara Heart" in client.post("/vapi", json=by_department).json()["result"]
    by_name = vapi("book_appointment", patient_name="Omar", start_time="2026-11-03T10:00:00", doctor="Dr Test")
    assert "with Dr. Test" in client.post("/vapi", json=by_name).json()["result"]

    availability = client.post("/vapi", json=vapi("check_availability", date="2026-11-03", doctor="heart")).json()
    assert availability["doctor"] == "Dr. Sara Heart (Cardiology)" and "10:00 AM" not in availability["available_slots"]


def test_voice_caller_is_recognised_by_phone_number(client):
    def call(name: str, number: str) -> dict:
        body = vapi("book_appointment", patient_name=name, start_time="2026-11-03T10:00:00")
        body["message"]["call"]["customer"] = {"number": number}
        return body

    login(client, "admin")
    known = client.post("/api/patients", json={"full_name": "Zara Ali", "phone": "+923001234567"}).json()
    assert client.post("/vapi", json=call("zara ali", "+923001234567")).json()["success"]
    [appointment] = client.get("/api/appointments").json()
    assert appointment["patient_id"] == known["id"]
