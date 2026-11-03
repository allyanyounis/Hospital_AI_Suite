"""Live transcription WebSocket: relays browser audio to Deepgram and streams the transcript back.

Protocol
  browser -> server: binary audio chunks; text {"type": "stop"} to finish and save, {"type": "discard"} to drop.
  server -> browser: {"type": "ready"}, {"type": "interim", "text", "speaker"}, {"type": "segment", "segment"},
                     then {"type": "encounter", "encounter"} after stop, or {"type": "empty"} / {"type": "error"}.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.audit import audit
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.auth import websocket_user

from .router import save_new_encounter
from .transcription import Transcript
from .transcription.live import LiveTranscriptBuilder, open_deepgram_stream, send_control

router = APIRouter(tags=["scribe"])
settings = get_settings()
log = logging.getLogger("hospital_ai.live")

FLUSH_TIMEOUT_SECONDS = 15
KEEPALIVE_SECONDS = 5  # Deepgram closes a stream after ~10s without audio; pausing the recorder sends none


async def _close_quietly(ws: WebSocket) -> None:
    try:
        await ws.close()
    except RuntimeError:
        pass  # already closed by the browser


@router.websocket("/api/encounters/live")
async def live_encounter(ws: WebSocket):
    user = websocket_user(ws, "scribe.use")
    if user is None:
        await ws.close(code=1008)
        return
    await ws.accept()
    if settings.transcriber != "deepgram" or not settings.deepgram_api_key:
        await ws.send_json({"type": "error", "message": "Live transcription needs Deepgram (DEEPGRAM_API_KEY)"})
        await ws.close()
        return

    builder = LiveTranscriptBuilder()

    async def to_client(payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except (WebSocketDisconnect, RuntimeError):
            pass  # browser went away; we still finish cleanly

    command = "dropped"
    try:
        async with open_deepgram_stream(settings.deepgram_api_key, settings.deepgram_model) as dg:

            async def browser_to_deepgram() -> str:
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        return "disconnect"
                    if msg.get("bytes"):
                        await dg.send(msg["bytes"])
                    elif msg.get("text"):
                        try:
                            kind = json.loads(msg["text"]).get("type")
                        except (ValueError, AttributeError):
                            continue
                        if kind in ("stop", "discard"):
                            await send_control(dg, "CloseStream")
                            return kind

            async def deepgram_to_browser() -> None:
                async for raw in dg:
                    if isinstance(raw, bytes):
                        continue
                    data = json.loads(raw)
                    if data.get("type") == "UtteranceEnd":
                        builder.close_turn()
                    if data.get("type") != "Results":
                        continue
                    alt = (data.get("channel", {}).get("alternatives") or [{}])[0]
                    words = alt.get("words") or []
                    if data.get("is_final"):
                        for seg in builder.add_final(words, bool(data.get("speech_final"))):
                            await to_client({"type": "segment", "segment": seg.model_dump()})
                        await to_client({"type": "interim", "text": "", "speaker": None})
                    elif alt.get("transcript"):
                        speaker = words[0].get("speaker") if words else None
                        await to_client({"type": "interim", "text": alt["transcript"], "speaker": speaker})

            async def keepalive() -> None:
                while True:
                    await asyncio.sleep(KEEPALIVE_SECONDS)
                    await send_control(dg, "KeepAlive")

            await to_client({"type": "ready"})
            client_task = asyncio.create_task(browser_to_deepgram())
            dg_task = asyncio.create_task(deepgram_to_browser())
            ka_task = asyncio.create_task(keepalive())
            try:
                await asyncio.wait({client_task, dg_task}, return_when=asyncio.FIRST_COMPLETED)
                # If Deepgram ended first (error/timeout), the browser falls back to uploading the recording
                command = client_task.result() if client_task.done() else "dropped"
                if command == "stop":
                    try:  # let Deepgram flush its final results after CloseStream
                        await asyncio.wait_for(dg_task, timeout=FLUSH_TIMEOUT_SECONDS)
                    except TimeoutError:
                        log.warning("Deepgram did not finish flushing; saving what we have")
            finally:
                for task in (client_task, dg_task, ka_task):
                    task.cancel()
    except Exception as e:  # connecting to Deepgram failed or the stream dropped
        log.warning("Live transcription failed: %s", e)
        command = "dropped"

    if command != "stop":
        # Discarded or disconnected: nothing is saved. Dropped: tell the browser so it uploads instead.
        if command == "dropped":
            audit(user.username, "transcription.failed", mode="live")
            await to_client({"type": "error", "message": "Live transcription is unavailable right now"})
        await _close_quietly(ws)
        return
    if not builder.segments:
        await to_client({"type": "empty"})
        await _close_quietly(ws)
        return

    transcript = Transcript(segments=builder.segments, provider="deepgram (live)", duration=builder.duration)
    with SessionLocal() as db:
        encounter = save_new_encounter(
            db, user, "live", transcript, transcriber=transcript.provider, audio_seconds=transcript.duration
        )
    await to_client({"type": "encounter", "encounter": encounter.model_dump()})
    await _close_quietly(ws)
