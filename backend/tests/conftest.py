"""Tests run against a separate PostgreSQL database: TEST_DATABASE_URL, or the .env DATABASE_URL with the database
renamed to hospital_ai_test. Every test starts with empty tables. No AI provider is called (a fake model is used)."""

import os

from sqlalchemy.engine import make_url

from app.config import get_settings

_url = os.environ.get("TEST_DATABASE_URL") or make_url(get_settings().database_url).set(
    database="hospital_ai_test"
).render_as_string(hide_password=False)
os.environ.update(DATABASE_URL=_url, SESSION_SECRET="test-secret", ANTHROPIC_API_KEY="", DEEPGRAM_API_KEY="")
os.environ.pop("VAPI_SECRET", None)
get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import main, security  # noqa: E402
from app.database import Base, engine, init_db  # noqa: E402
from app.scribe import router as scribe_router  # noqa: E402
from app.scribe.notes import ClinicalCodes, GeneratedDocument, GeneratedNote, NoteReview, TaskList  # noqa: E402
from app.users import save_user  # noqa: E402

PASSWORD = "correct-horse"
ORIGIN = {"origin": "http://localhost:3000"}


class FakeGenerator:
    name = "fake"
    model = "fake-model"

    async def complete(self, system, user, schema, effort=None):
        if schema is GeneratedNote:
            return GeneratedNote.model_validate(
                {
                    "sections": [
                        {
                            "heading": "Subjective",
                            "statements": [
                                {"text": "Chest pain since 07:00", "source_segment_ids": [1]},
                                {"text": "Invented line", "source_segment_ids": [999]},  # bad citation: must be dropped
                            ],
                        },
                        {"heading": "Plan", "statements": [{"text": "ECG, troponin", "source_segment_ids": [17]}]},
                    ]
                }
            )
        if schema is NoteReview:
            return NoteReview.model_validate(
                {
                    "findings": [
                        {
                            "category": "missing",
                            "severity": "low",
                            "message": "Follow-up not stated",
                            "section": "Plan",
                            "source_segment_ids": [],
                        },
                        {
                            "category": "safety",
                            "severity": "high",
                            "message": "Check allergy",
                            "section": "",
                            "source_segment_ids": [13, 999],
                        },
                    ]
                }
            )
        if schema is ClinicalCodes:
            return ClinicalCodes.model_validate(
                {
                    "codes": [
                        {
                            "code": "r07.9",
                            "description": "Chest pain, unspecified",
                            "kind": "symptom",
                            "confidence": "high",
                            "evidence": "Chest pain since 07:00",
                        },
                        {
                            "code": "NOT-A-CODE",
                            "description": "junk",
                            "kind": "primary",
                            "confidence": "low",
                            "evidence": "",
                        },
                        {
                            "code": "R07.9",
                            "description": "duplicate",
                            "kind": "secondary",
                            "confidence": "low",
                            "evidence": "",
                        },
                    ]
                }
            )
        if schema is TaskList:
            return TaskList.model_validate(
                {
                    "tasks": [
                        {
                            "title": "Order troponin",
                            "detail": "hs-troponin",
                            "category": "test",
                            "owner": "clinician",
                            "due": "today",
                            "done": True,
                        },
                    ]
                }
            )
        return GeneratedDocument(title="Visit summary", paragraphs=["You came in with chest pain."])


def _reset_database() -> None:
    init_db()
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(monkeypatch):
    _reset_database()
    security._failed_logins.clear()
    monkeypatch.setattr(scribe_router, "get_note_generator", lambda _settings: FakeGenerator())
    save_user("drtest", "Dr. Test", "clinician", PASSWORD)
    save_user("admin", "Admin", "admin", PASSWORD)
    with TestClient(main.app) as c:
        yield c


def login(client, username="drtest"):
    r = client.post("/api/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
