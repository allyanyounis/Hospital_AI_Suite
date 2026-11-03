"""Authentication and authorization: roles, permissions per endpoint, patient portal scoping, account management,
and sessions ending when a password, role or status changes."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import main
from app.core.clock import to_aware
from app.core.database import session_scope
from app.modules.appointments import Appointment
from app.modules.auth.cli import save_user
from app.modules.auth.permissions import ROLE_PERMISSIONS
from app.modules.patients import Patient
from app.modules.staff import StaffMember
from tests.conftest import ORIGIN, PASSWORD, login


def _patient_account(client, username="ali", mrn="MRN-100") -> None:
    """Admin creates a patient account (and its patient record) through the API."""
    login(client, "admin")
    body = {
        "username": username,
        "display_name": "Ali Khan",
        "role": "patient",
        "password": PASSWORD,
        "patient": {"mrn": mrn, "dob": "1980-01-31", "sex": "Male"},
    }
    r = client.post("/api/users", json=body)
    assert r.status_code == 201, r.text
    client.post("/api/logout")


def test_me_returns_role_and_permissions(client):
    login(client)
    me = client.get("/api/me").json()
    assert me["role"] == "doctor" and me["patient_id"] is None
    assert set(me["permissions"]) == ROLE_PERMISSIONS["doctor"]


# --- Who may call what -------------------------------------------------------------------------------------------

STAFF_ONLY = [
    ("get", "/api/encounters"),
    ("get", "/api/templates"),
    ("get", "/api/metrics"),
    ("get", "/api/closures"),
    ("get", "/api/appointments"),
    ("get", "/api/patients"),
    ("get", "/api/staff"),
    ("get", "/api/departments"),
]
ADMIN_ONLY = [("get", "/api/metrics/all"), ("get", "/api/users"), ("put", "/api/closures")]


@pytest.mark.parametrize("method, path", STAFF_ONLY + ADMIN_ONLY)
def test_patients_get_403_on_staff_endpoints(client, method, path):
    _patient_account(client)
    login(client, "ali")
    kwargs = {"json": {"closures": []}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 403


@pytest.mark.parametrize("method, path", ADMIN_ONLY)
def test_doctors_get_403_on_admin_endpoints(client, method, path):
    login(client)
    kwargs = {"json": {}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 403


def test_staff_endpoints_need_sign_in(client):
    for method, path in STAFF_ONLY + ADMIN_ONLY + [("get", "/api/portal/me")]:
        kwargs = {"json": {}} if method == "put" else {}
        assert getattr(client, method)(path, **kwargs).status_code == 401, path


def test_doctors_cannot_use_the_portal(client):
    login(client)
    assert client.get("/api/portal/appointments").status_code == 403


def test_patients_cannot_open_staff_websockets(client):
    _patient_account(client)
    login(client, "ali")
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/events", headers=ORIGIN) as ws:
        ws.receive_text()


# --- Patient portal ----------------------------------------------------------------------------------------------


def test_portal_shows_only_the_patients_own_record_and_appointments(client):
    _patient_account(client)
    with session_scope() as db:
        mine = db.query(Patient).filter_by(mrn="MRN-100").one()
        doctor = db.query(StaffMember).filter_by(username="drtest").one()
        at = lambda hour: to_aware(datetime(2026, 11, 3, hour))  # noqa: E731
        db.add(Appointment(patient=mine, practitioner=doctor, reason="Check-up", start_time=at(10), booked_via="desk"))
        other = Patient(full_name="Someone Else")
        db.add(Appointment(patient=other, practitioner=doctor, start_time=at(11), booked_via="desk"))

    login(client, "ali")
    assert client.get("/api/me").json()["permissions"] == ["portal.use"]
    profile = {"name": "Ali Khan", "mrn": "MRN-100", "dob": "1980-01-31", "sex": "Male"}
    assert client.get("/api/portal/me").json() == profile
    [appointment] = client.get("/api/portal/appointments").json()
    assert appointment["reason"] == "Check-up" and "patient_name" not in appointment and "transcript" not in appointment
    assert (appointment["doctor"], appointment["department"]) == ("Dr. Test", "General Medicine")


# --- Account management ------------------------------------------------------------------------------------------


def test_admin_manages_accounts(client):
    login(client, "admin")
    body = {"username": "drnew", "display_name": "Dr. New", "role": "doctor", "password": PASSWORD}
    assert client.post("/api/users", json=body).status_code == 201
    assert client.post("/api/users", json=body).status_code == 409
    assert client.post("/api/users", json={**body, "username": "x2", "password": "short"}).status_code == 422
    assert client.post("/api/users", json={**body, "username": "p2", "role": "patient"}).status_code == 422

    promoted = client.patch("/api/users/drnew", json={"role": "admin"}).json()
    assert promoted["role"] == "admin"
    assert client.patch("/api/users/drnew", json={"role": "patient"}).status_code == 422
    assert client.patch("/api/users/admin", json={"active": False}).status_code == 422  # not yourself
    assert client.patch("/api/users/admin", json={"role": "doctor"}).status_code == 422

    names = {u["username"]: u for u in client.get("/api/users").json()}
    assert set(names) == {"admin", "drnew", "drtest"} and names["drtest"]["patient"] is None


def test_one_account_per_patient(client):
    _patient_account(client, "ali", "MRN-7")
    login(client, "admin")
    body = {"username": "ali2", "display_name": "Ali", "role": "patient", "password": PASSWORD}
    body["patient"] = {"mrn": "MRN-7"}
    assert client.post("/api/users", json=body).status_code == 409


# --- Sessions ----------------------------------------------------------------------------------------------------


def _second_device() -> TestClient:
    other = TestClient(main.app)
    login(other)
    return other


def test_password_reset_and_disable_sign_the_user_out_everywhere(client):
    other = _second_device()
    login(client, "admin")
    assert client.post("/api/users/drtest/password", json={"password": "new-password-123"}).status_code == 200
    assert other.get("/api/me").status_code == 401

    save_user("drtest", "Dr. Test", "doctor", PASSWORD)  # back to the known password
    other = _second_device()
    assert client.patch("/api/users/drtest", json={"active": False}).status_code == 200
    assert other.get("/api/me").status_code == 401
    assert other.post("/api/login", json={"username": "drtest", "password": PASSWORD}).status_code == 401


def test_changing_your_own_password_keeps_this_device_signed_in(client):
    other = _second_device()
    login(client)
    wrong = client.post("/api/me/password", json={"current_password": "nope", "new_password": "another-pass-1"})
    assert wrong.status_code == 400
    r = client.post("/api/me/password", json={"current_password": PASSWORD, "new_password": "another-pass-1"})
    assert r.status_code == 200
    assert client.get("/api/me").status_code == 200  # fresh cookie
    assert other.get("/api/me").status_code == 401  # other sessions end


def test_role_change_applies_on_the_next_request(client):
    other = _second_device()
    assert other.get("/api/users").status_code == 403
    login(client, "admin")
    client.patch("/api/users/drtest", json={"role": "admin"})
    assert other.get("/api/me").status_code == 401  # role changes end sessions; sign in again for new rights
    login(other)
    assert other.get("/api/users").status_code == 200


def test_session_check_is_quiet_when_signed_out(client):
    assert client.get("/api/session").json() == {"user": None}  # 200, not 401
    login(client)
    user = client.get("/api/session").json()["user"]
    assert user["username"] == "drtest" and set(user["permissions"]) == ROLE_PERMISSIONS["doctor"]
