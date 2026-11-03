"""Receptionist tables."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import now_column


class Appointment(Base):
    """A booking made by the AI voice receptionist (or the dashboard)."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(120), index=True)
    reason: Mapped[str | None] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    canceled: Mapped[bool] = mapped_column(Boolean, default=False)
    # The voice call that booked it; links the end-of-call transcript
    call_id: Mapped[str | None] = mapped_column(String(64), index=True)
    transcript: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now_column()
