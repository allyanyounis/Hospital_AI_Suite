"""Theatre API over the database: the seeded board equals the POC's, changes are saved and announced, previews
save nothing, and permissions hold."""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.clock import now_local
from app.core.database import session_scope
from app.core.events import broadcaster
from app.modules.auth.cli import save_user
from app.modules.theatre import SurgicalCase, seed_demo
from app.modules.theatre import service as theatre_service
from app.modules.theatre.demo import anchor_for
from tests.conftest import PASSWORD, login

GOLDEN = json.loads((Path(__file__).parent / "data" / "theatre_golden.json").read_text(encoding="utf-8"))
AT = {"at": GOLDEN["now"]}


@pytest.fixture
def demo(client, monkeypatch):
    """The demo hospital, with "today" on the replayed POC day; collects published events."""
    real_today = now_local().date()
    with session_scope() as db:
        assert seed_demo(db, real_today) is not None
        assert seed_demo(db, real_today) is None  # idempotent
    monkeypatch.setattr(theatre_service, "today", lambda: anchor_for(real_today))
    events = []

    async def publish(event, **data):
        events.append((event, data))

    monkeypatch.setattr(broadcaster, "publish", publish)
    login(client, "admin")
    return events


def _count(**where) -> int:
    with session_scope() as db:
        return db.scalar(select(func.count()).select_from(SurgicalCase).filter_by(**where))


def test_seeded_board_matches_the_poc(client, demo):
    board = client.get("/api/theatre/board", params=AT).json()
    assert [r["code"] for r in board["rooms"]] == [r["code"] for r in GOLDEN["rooms"]]
    for room, gold in zip(board["rooms"], GOLDEN["rooms"], strict=True):
        assert room["finish"] == gold["finish"]
        assert abs(room["forecast"]["over_pct"] - gold["forecast"]["over_pct"]) <= 1
        assert (room["suggestion"] is None) == (gold["suggestion"] is None)
    assert len(board["proposals"]) == len(GOLDEN["proposals"])
    assert board["waiting"] == 6 and board["urgent_waiting"] == len(GOLDEN["proposals"])


def test_moves_are_saved_audited_and_announced(client, demo):
    board = client.get("/api/theatre/board", params=AT).json()
    tip = next(r["suggestion"] for r in board["rooms"] if r["suggestion"])
    r = client.post(f"/api/theatre/cases/{tip['case']}/defer", params=AT, json={"day": tip["date"]})
    assert r.status_code == 200, r.text
    assert demo[-1][0] == "theatre_updated" and tip["date"] in demo[-1][1]["days"]
    later = client.get("/api/theatre/deferred").json()["items"]
    assert [c["id"] for c in later] == [tip["case"]]

    done = next(c for r in board["rooms"] for c in r["cases"] if c["state"] == "done")
    r = client.post(f"/api/theatre/cases/{done['id']}/later", params=AT)
    assert r.status_code == 422 and "started" in r.json()["detail"]

    r = client.post(f"/api/theatre/cases/{tip['case']}/cancel", params=AT)
    assert r.status_code == 200 and _count(id=tip["case"], canceled=True) == 1
    assert client.get(f"/api/theatre/cases/{tip['case']}").status_code == 404


def test_intake_preview_saves_nothing_and_confirm_applies_picked_moves(client, demo):
    waiting = client.get("/api/theatre/waiting", params={"urgency": "urgent"}).json()["items"]
    case_id = waiting[0]["id"]
    preview = client.post("/api/theatre/intake/preview", params=AT, json={"case_id": case_id})
    assert preview.status_code == 200, preview.text
    assert _count(scheduled_on=None) == 6  # nothing saved
    body = preview.json()
    moves = [{"case": m["case"], "date": m["date"]} for m in body["moves"][:1]]
    r = client.post("/api/theatre/intake/confirm", params=AT, json={"case_id": case_id, "moves": moves})
    assert r.status_code == 200, r.text
    assert _count(scheduled_on=None) == 5
    if moves:
        assert _count(id=moves[0]["case"], deferred=True) == 1


def test_booking_a_new_patient_and_the_calendar(client, demo):
    procedures = client.get("/api/theatre/procedures").json()
    code = next(p["code"] for p in procedures if p["title"].startswith("Laparoscopic chole"))
    today = theatre_service.today()
    week = client.get("/api/theatre/calendar", params={"start": today.isoformat(), "procedure": code}).json()
    fits = [cell["fit"] for d in week["days"] for cell in d["rooms"] if "fit" in cell and "reason" not in cell["fit"]]
    assert fits
    slot = fits[0]
    new = {
        "procedure_code": code,
        "day": slot["day"],
        "patient": {"name": "Zara Test", "age": 41, "sex": "Female", "allergies": "Latex"},
    }
    r = client.post("/api/theatre/cases", json=new)
    assert r.status_code == 201, r.text
    detail = client.get(f"/api/theatre/cases/{r.json()['case']}").json()
    assert detail["patient"]["name"] == "Zara Test" and detail["patient"]["allergies"] == "Latex"
    assert detail["day"] == slot["day"] and detail["risk"]["model"] == "VitalDB"
    chart = client.get(f"/api/clinical/patients/{detail['patient']['id']}/history").json()
    assert chart[0]["kind"] == "indication"
    past = (today - timedelta(days=7)).isoformat()
    r = client.post("/api/theatre/cases", json=new | {"day": past})
    assert r.status_code == 422


def test_roster_and_leave_conflicts(client, demo):
    surgeons = client.get("/api/theatre/surgeons").json()
    busy = max(surgeons, key=lambda s: s["booked"])
    today = theatre_service.today()
    r = client.post(
        "/api/theatre/leave",
        json={
            "staff_id": busy["id"],
            "starts_on": today.isoformat(),
            "ends_on": (today + timedelta(days=14)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["conflicts"]
    r = client.put(
        f"/api/theatre/surgeons/{busy['id']}/roster", json={"days": [{"weekday": 0, "start": 480, "end": 960}]}
    )
    assert r.status_code == 200
    me = next(s for s in client.get("/api/theatre/surgeons").json() if s["id"] == busy["id"])
    assert me["days"] == [{"weekday": 0, "start": 480, "end": 960}] and me["leave"]
    assert client.delete(f"/api/theatre/leave/{me['leave'][0]['id']}").status_code == 200


def test_permissions(client, demo):
    save_user("nurse1", "Nurse", "nurse", PASSWORD)
    login(client, "nurse1")
    assert client.get("/api/theatre/board").status_code == 200
    assert client.post("/api/theatre/cases/1/later").status_code == 403
    assert client.get("/api/theatre/insights/model-audit").status_code == 403
    login(client)  # doctor
    assert client.put("/api/theatre/surgeons/1/roster", json={"days": []}).status_code == 403
    assert client.get("/api/theatre/insights/model-audit").status_code == 200
