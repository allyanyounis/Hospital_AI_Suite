"""Scribe end-to-end with a fake model: sign-in, encounter, draft, review, approve, documents, metrics, retention."""

import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.database import session_scope
from app.models import AuditLog
from app.scribe.models import Encounter
from app.scribe.repository import purge_expired_content
from tests.conftest import login


def _age_encounter(encounter_id: str) -> None:
    with session_scope() as db:
        db.get(Encounter, encounter_id).created_at = datetime(2000, 1, 1, tzinfo=UTC)


def test_requires_sign_in(client):
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).status_code == 401
    assert client.get("/api/reception/appointments").status_code == 401
    assert client.get("/api/schedule").status_code == 401
    assert client.post("/api/login", json={"username": "drtest", "password": "wrong"}).status_code == 401


def test_full_flow(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]

    # Documents need an approved note
    assert client.post(f"/api/encounters/{eid}/documents", json={"type_id": "patient_summary"}).status_code == 409

    note = client.post(f"/api/encounters/{eid}/note", json={"template_id": "soap"}).json()
    assert [st["text"] for st in note["sections"][0]["statements"]] == ["Chest pain since 07:00"]

    findings = client.post(f"/api/encounters/{eid}/review", json={"note": note}).json()["findings"]
    assert findings[0]["severity"] == "high" and findings[0]["source_segment_ids"] == [13]

    note["sections"][1]["statements"].append({"text": "Cardiology review", "source_segment_ids": []})
    counts = client.post(f"/api/encounters/{eid}/approve", json={"note": note}).json()
    assert counts == {"lines_drafted": 2, "lines_kept": 2, "lines_added": 1, "lines_removed": 0}

    doc = client.post(f"/api/encounters/{eid}/documents", json={"type_id": "patient_summary"}).json()
    assert doc["title"] == "Visit summary"

    m = client.get("/api/metrics").json()
    assert m["notes_approved"] == 1 and m["lines_kept_pct"] == 100 and m["reviews_run"] == 1
    assert client.get("/api/metrics/all").status_code == 403

    with session_scope() as db:
        actions = list(db.scalars(select(AuditLog.action).where(AuditLog.encounter_id == eid).order_by(AuditLog.id)))
    assert actions == ["encounter.created", "note.drafted", "note.reviewed", "note.approved", "document.generated"]


def test_clinicians_cannot_open_each_others_encounters(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "af-review"}).json()["id"]
    client.post("/api/logout")
    login(client, "admin")
    assert client.post(f"/api/encounters/{eid}/note", json={"template_id": "soap"}).status_code == 404
    assert client.get("/api/metrics/all").status_code == 200


def test_retention_erases_content_but_keeps_metrics(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "hf-clinic"}).json()["id"]
    _age_encounter(eid)
    assert purge_expired_content(7) >= 1
    assert client.post(f"/api/encounters/{eid}/note", json={"template_id": "soap"}).status_code == 410


def test_lockout_after_repeated_failures(client):
    for _ in range(5):
        client.post("/api/login", json={"username": "lockme", "password": "nope"})
    assert client.post("/api/login", json={"username": "lockme", "password": "nope"}).status_code == 429


def test_board_pipeline_patient_and_background_draft(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]
    patient = {
        "name": "Test Patient",
        "mrn": "MRN-001",
        "sex": "Female",
        "dob": "1970-01-01",
        "visit_type": "New visit",
    }
    assert client.put(f"/api/encounters/{eid}/patient", json=patient).status_code == 200

    [row] = [e for e in client.get("/api/encounters").json() if e["id"] == eid]
    assert row["status"] == "pending" and row["patient"] == patient and row["source"] == "sample"

    assert client.post(f"/api/encounters/{eid}/note/start", json={"template_id": "soap"}).status_code == 202
    for _ in range(100):
        detail = client.get(f"/api/encounters/{eid}").json()
        if detail["status"] != "drafting":
            break
        time.sleep(0.05)
    assert detail["status"] == "ready"
    assert detail["draft_note"]["sections"][0]["statements"][0]["text"] == "Chest pain since 07:00"

    client.post(f"/api/encounters/{eid}/approve", json={"note": detail["draft_note"]})
    assert client.get(f"/api/encounters/{eid}").json()["status"] == "signed"
    assert client.post(f"/api/encounters/{eid}/note/start", json={"template_id": "soap"}).status_code == 409

    # Patient details are erased with the rest of the clinical content
    _age_encounter(eid)
    purge_expired_content(7)
    [row] = [e for e in client.get("/api/encounters").json() if e["id"] == eid]
    assert row["purged"] and row["patient"]["name"] == ""


def test_clinical_codes_and_tasks(client):
    login(client)
    eid = client.post("/api/encounters/sample", json={"sample_id": "ed-chest-pain"}).json()["id"]
    assert client.post(f"/api/encounters/{eid}/codes").status_code == 409  # needs a note first

    note = client.post(f"/api/encounters/{eid}/note", json={"template_id": "soap"}).json()
    codes = client.post(f"/api/encounters/{eid}/codes").json()
    # Malformed and duplicate codes dropped, normalised to upper case, the only code promoted to primary
    assert [(c["code"], c["kind"]) for c in codes["codes"]] == [("R07.9", "primary")]
    assert codes["source"] == "draft"

    tasks = client.post(f"/api/encounters/{eid}/tasks").json()
    assert tasks["tasks"][0]["title"] == "Order troponin" and tasks["tasks"][0]["done"] is False

    tasks["tasks"][0]["done"] = True
    tasks["tasks"].append({"title": "Book echo", "category": "test", "owner": "admin"})
    assert client.put(f"/api/encounters/{eid}/tasks", json=tasks).status_code == 200

    client.post(f"/api/encounters/{eid}/approve", json={"note": note})
    assert client.post(f"/api/encounters/{eid}/codes").json()["source"] == "signed"

    detail = client.get(f"/api/encounters/{eid}").json()
    assert [t["done"] for t in detail["tasks"]["tasks"]] == [True, False]
    assert detail["codes"]["codes"][0]["code"] == "R07.9"
