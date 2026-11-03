"""Clinic schedule table."""

from datetime import date, datetime

from sqlalchemy import Date, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import now_column


class ClinicSchedule(Base):
    """The clinic's weekly hours, slot length and closed dates (a single row, id = 1).

    The AI receptionist books only inside these hours; the scribe's after-hours metric uses them too.
    """

    __tablename__ = "clinic_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # 7 entries, Monday first: {"enabled", "start": "HH:MM", "end": "HH:MM", "breaks": [{"start", "end"}]}
    days: Mapped[list] = mapped_column(JSONB)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=15)
    holidays: Mapped[list[date]] = mapped_column(ARRAY(Date), default=list)
    updated_at: Mapped[datetime] = now_column(onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(64))
