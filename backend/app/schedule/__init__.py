"""Clinic schedule shared by the AI receptionist (bookings) and the AI scribe (after-hours metric)."""

from sqlalchemy.orm import Session

from ..models import ClinicSchedule as ScheduleRow
from .schemas import DAY_NAMES, BreakPeriod, ClinicSchedule, ClinicScheduleIn, DaySchedule, default_schedule

__all__ = [
    "DAY_NAMES",
    "BreakPeriod",
    "ClinicSchedule",
    "ClinicScheduleIn",
    "DaySchedule",
    "default_schedule",
    "load_schedule",
    "save_schedule",
]


def load_schedule(db: Session) -> ClinicSchedule:
    row = db.get(ScheduleRow, 1)
    if row is None:
        return default_schedule()
    return ClinicSchedule(
        days=row.days, slot_minutes=row.slot_minutes, holidays=row.holidays, updated_at=row.updated_at
    )


def save_schedule(db: Session, schedule: ClinicScheduleIn, username: str) -> None:
    row = db.get(ScheduleRow, 1) or ScheduleRow(id=1)
    row.days = [d.model_dump() for d in schedule.days]
    row.slot_minutes = schedule.slot_minutes
    row.holidays = schedule.holidays
    row.updated_by = username
    db.add(row)
