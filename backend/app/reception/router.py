"""Signed-in dashboard API for the AI receptionist: appointments and live update events."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import audit
from ..database import get_db
from ..events import broadcaster
from ..security import User, current_user, websocket_user
from .models import Appointment

router = APIRouter(prefix="/api/reception", tags=["reception"])


class AppointmentOut(BaseModel):
    id: int
    patient_name: str
    reason: str | None
    start_time: datetime
    canceled: bool
    created_at: datetime
    transcript: str | None


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Appointment).order_by(Appointment.start_time))


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    if not appointment.canceled:
        appointment.canceled = True
        audit(user.username, "appointment.canceled", db=db, appointment_id=appointment_id, source="dashboard")
        db.commit()
        await broadcaster.publish("appointment_canceled")
    return appointment


@router.websocket("/events")
async def events(ws: WebSocket):
    """Pushes {"type": "appointment_booked" | "appointment_canceled" | "transcript_saved" | "schedule_updated"}."""
    if websocket_user(ws) is None:
        await ws.close(code=1008)
        return
    await broadcaster.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keeps the connection open; clients don't send anything meaningful
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
