"""Health check, the public settings the UI needs before sign-in, and the staff dashboard's live-events socket."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.events import broadcaster
from app.modules.auth import websocket_user
from app.modules.scribe import note_model_status

router = APIRouter(prefix="/api", tags=["system"])
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config")
async def config():
    """Public, non-secret settings the UI needs before sign-in (banner, which AI services are configured)."""
    note_model, notes_ready = await note_model_status(settings)
    return {
        "environment_banner": settings.environment_banner,
        "retention_days": settings.retention_days,
        "hospital_name": settings.hospital_name,
        "hospital_timezone": settings.hospital_timezone,
        "transcriber": settings.transcriber,
        "transcriber_ready": bool(settings.deepgram_api_key),
        "note_model": note_model,
        "notes_ready": notes_ready,
    }


@router.websocket("/events")
async def events(ws: WebSocket):
    """Pushes {"type": "appointment_booked" | "appointment_canceled" | "transcript_saved" | "schedule_updated"}."""
    if websocket_user(ws, "appointments.view") is None:
        await ws.close(code=1008)
        return
    await broadcaster.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keeps the connection open; clients don't send anything meaningful
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
