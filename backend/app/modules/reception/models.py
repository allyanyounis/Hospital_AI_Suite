"""Voice receptionist tables: phone calls, and which appointments were booked during which call.

The link is owned here, not on `appointments`, so the appointments module knows nothing about voice calls.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, now_column


class VoiceCall(Base):
    """One VAPI phone call. Its transcript arrives with the end-of-call report and is stored once, here."""

    __tablename__ = "voice_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # VAPI call id
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transcript: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now_column()


class VoiceCallBooking(Base):
    """An appointment booked during a call (an appointment is booked in at most one call)."""

    __tablename__ = "voice_call_bookings"

    call_id: Mapped[str] = mapped_column(ForeignKey("voice_calls.id", ondelete="CASCADE"), primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), primary_key=True, unique=True
    )
