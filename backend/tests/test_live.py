"""Live transcription: segment building, WebSocket auth, and the stream -> encounter flow with a fake Deepgram."""

import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect

from app.database import session_scope
from app.models import AuditLog
from app.scribe import live_router
from app.scribe.models import Encounter
from app.scribe.transcription.live import LiveTranscriptBuilder
from tests.conftest import ORIGIN, login


def w(word, speaker, start, end):
    return {"word": word.lower().strip(".,?"), "punctuated_word": word, "speaker": speaker, "start": start, "end": end}


def test_builder_groups_words_into_speaker_turns():
    b = LiveTranscriptBuilder()
    b.add_final([w("Any", 0, 0.0, 0.2), w("chest", 0, 0.2, 0.5)], speech_final=False)
    changed = b.add_final([w("pain?", 0, 0.5, 0.8)], speech_final=True)
    assert [s.text for s in changed] == ["Any chest pain?"]
    b.add_final([w("Yes,", 1, 1.2, 1.4), w("since", 1, 1.4, 1.6), w("Monday.", 1, 1.6, 2.0)], speech_final=False)
    b.close_turn()  # UtteranceEnd
    b.add_final([w("Since", 1, 3.0, 3.2), w("then.", 1, 3.2, 3.5)], speech_final=True)
    assert [(s.id, s.speaker, s.text) for s in b.segments] == [
        (0, 0, "Any chest pain?"),
        (1, 1, "Yes, since Monday."),
        (2, 1, "Since then."),
    ]
    assert b.duration == 3.5


class FakeDeepgram:
    """Accepts audio, and on CloseStream emits one final result per speaker turn, then closes."""

    def __init__(self):
        self.audio = b""
        self._closed = asyncio.Event()

    async def send(self, data):
        if isinstance(data, bytes):
            self.audio += data
        elif json.loads(data)["type"] == "CloseStream":
            self._closed.set()

    def __aiter__(self):
        return self._messages()

    async def _messages(self):
        yield json.dumps(
            {
                "type": "Results",
                "is_final": False,
                "channel": {"alternatives": [{"transcript": "Any chest", "words": [w("Any", 0, 0, 0.2)]}]},
            }
        )
        await self._closed.wait()
        for words in ([w("Any", 0, 0.0, 0.2), w("pain?", 0, 0.2, 0.6)], [w("No.", 1, 1.0, 1.3)]):
            yield json.dumps(
                {
                    "type": "Results",
                    "is_final": True,
                    "speech_final": True,
                    "channel": {"alternatives": [{"transcript": "", "words": words}]},
                }
            )


@pytest.fixture
def fake_deepgram(monkeypatch):
    fake = FakeDeepgram()

    @asynccontextmanager
    async def open_stream(_key, _model):
        yield fake

    monkeypatch.setattr(live_router, "open_deepgram_stream", open_stream)
    monkeypatch.setattr(live_router.settings, "deepgram_api_key", "test-key")
    return fake


def test_live_requires_sign_in_and_same_origin(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/encounters/live", headers=ORIGIN) as ws:
            ws.receive_json()
    login(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/encounters/live", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()


def test_live_stream_creates_encounter(client, fake_deepgram):
    login(client)
    with client.websocket_connect("/api/encounters/live", headers=ORIGIN) as ws:
        assert ws.receive_json() == {"type": "ready"}
        ws.send_bytes(b"chunk-1")
        ws.send_bytes(b"chunk-2")
        assert ws.receive_json() == {"type": "interim", "text": "Any chest", "speaker": 0}
        ws.send_text(json.dumps({"type": "stop"}))
        messages = []
        while (m := ws.receive_json())["type"] != "encounter":
            messages.append(m)

    assert fake_deepgram.audio == b"chunk-1chunk-2"
    assert [x["segment"]["text"] for x in messages if x["type"] == "segment"] == ["Any pain?", "No."]
    encounter = m["encounter"]
    assert [s["speaker"] for s in encounter["transcript"]["segments"]] == [0, 1]

    # The live encounter works with the rest of the flow
    assert client.post(f"/api/encounters/{encounter['id']}/note", json={"template_id": "soap"}).status_code == 200
    assert client.get(f"/api/encounters/{encounter['id']}").json()["source"] == "live"
    with session_scope() as db:
        detail = db.scalar(
            select(AuditLog.detail).where(
                AuditLog.encounter_id == encounter["id"], AuditLog.action == "encounter.created"
            )
        )
    assert detail["source"] == "live"


def test_live_discard_saves_nothing(client, fake_deepgram):
    login(client)
    with client.websocket_connect("/api/encounters/live", headers=ORIGIN) as ws:
        assert ws.receive_json() == {"type": "ready"}
        ws.send_bytes(b"chunk")
        ws.send_text(json.dumps({"type": "discard"}))
        with pytest.raises(WebSocketDisconnect):
            while True:
                ws.receive_json()
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(Encounter)) == 0
