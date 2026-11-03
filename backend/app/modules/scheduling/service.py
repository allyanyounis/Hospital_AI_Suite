"""Loading and saving doctors' weeks and the hospital's closed dates."""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import DoctorSchedule, HospitalClosure, ScheduleBreak, ScheduleDay
from .schemas import BreakPeriod, Closure, DaySchedule, Schedule, ScheduleIn, default_schedule, parse_hhmm


def _hhmm(value) -> str:
    return value.strftime("%H:%M")


def closed_dates(db: Session) -> list[date]:
    return list(db.scalars(select(HospitalClosure.closed_on).order_by(HospitalClosure.closed_on)))


def load_schedule(db: Session, staff_id: int) -> Schedule:
    """A doctor's saved week (or the default week), with the hospital's closed dates applied."""
    holidays = closed_dates(db)
    row = db.scalar(select(DoctorSchedule).where(DoctorSchedule.staff_id == staff_id))
    if row is None:
        return default_schedule(staff_id, holidays)
    days = {d.weekday: d for d in row.days}
    return Schedule(
        staff_id=staff_id,
        days=[
            DaySchedule(
                enabled=d.enabled,
                start=_hhmm(d.opens),
                end=_hhmm(d.closes),
                breaks=[BreakPeriod(start=_hhmm(b.starts), end=_hhmm(b.ends)) for b in d.breaks],
            )
            if (d := days.get(i))
            else DaySchedule()
            for i in range(7)
        ],
        slot_minutes=row.slot_minutes,
        holidays=holidays,
        updated_at=row.updated_at,
    )


def save_schedule(db: Session, staff_id: int, schedule: ScheduleIn, username: str | None) -> None:
    """Replace a doctor's whole week; the request is already validated (ScheduleIn)."""
    row = db.scalar(select(DoctorSchedule).where(DoctorSchedule.staff_id == staff_id))
    if row is None:
        row = DoctorSchedule(staff_id=staff_id)
        db.add(row)
    row.slot_minutes, row.updated_by = schedule.slot_minutes, username
    row.days.clear()
    db.flush()  # old days and breaks are deleted before the new ones reuse their keys
    for weekday, day in enumerate(schedule.days):
        # A disabled day's breaks are not validated; keep only ones the table can hold
        breaks = day.breaks
        if not day.enabled:
            breaks = [b for b in {b.start: b for b in day.breaks}.values() if b.end > b.start]
        row.days.append(
            ScheduleDay(
                weekday=weekday,
                enabled=day.enabled,
                opens=parse_hhmm(day.start),
                closes=parse_hhmm(day.end),
                breaks=[ScheduleBreak(starts=parse_hhmm(b.start), ends=parse_hhmm(b.end)) for b in breaks],
            )
        )


def list_closures(db: Session) -> list[Closure]:
    rows = db.scalars(select(HospitalClosure).order_by(HospitalClosure.closed_on))
    return [Closure(date=r.closed_on, reason=r.reason or "") for r in rows]


def save_closures(db: Session, closures: list[Closure]) -> None:
    db.execute(delete(HospitalClosure))
    db.add_all(HospitalClosure(closed_on=c.date, reason=c.reason.strip() or None) for c in closures)
