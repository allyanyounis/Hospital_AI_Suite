"""OPD booking rules, shared by every booking channel (voice receptionist, front desk, later the patient portal).

Every function returns a sentence a person can read or hear. Rule failures are normal outcomes
(BookingResult.ok = False), never exceptions, so a voice call never falls back to a generic technical error.
Times are naive hospital-local datetimes; the database stores timezone-aware ones.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_local, to_aware, to_local
from app.core.config import get_settings
from app.modules.patients import Patient
from app.modules.scheduling import DAY_NAMES, DaySchedule, Schedule, parse_hhmm
from app.modules.staff import StaffMember

from .models import BOOKING_CHANNELS, Appointment


@dataclass
class BookingResult:
    ok: bool
    message: str
    appointment: Appointment | None = None
    canceled_count: int = 0
    status: str | None = None


# --- Formatting --------------------------------------------------------------------------------------------------


def fmt_time(value: datetime | time) -> str:
    """'8:30 AM' - spoken-friendly 12-hour time."""
    return value.strftime("%I:%M %p").lstrip("0")


def fmt_date(value: date | datetime) -> str:
    return value.strftime("%B %d, %Y")


def _range_text(start: str, end: str) -> str:
    return f"{fmt_time(parse_hhmm(start))} to {fmt_time(parse_hhmm(end))}"


def day_hours_text(day: DaySchedule) -> str:
    """'9:00 AM to 5:00 PM (break 1:00 PM to 2:00 PM)'."""
    breaks = [_range_text(b.start, b.end) for b in sorted(day.breaks, key=lambda b: b.start)]
    return _range_text(day.start, day.end) + (f" (break {', '.join(breaks)})" if breaks else "")


def schedule_text(schedule: Schedule) -> str:
    """The whole week, grouping days with identical hours: '9:00 AM to 5:00 PM on Monday, Tuesday; ...'."""
    groups: dict[str, list[str]] = {}
    for name, day in zip(DAY_NAMES, schedule.days, strict=False):
        if day.enabled:
            groups.setdefault(day_hours_text(day), []).append(name)
    if not groups:
        return "no working days are set"
    return "; ".join(f"{hours} on {', '.join(days)}" for hours, days in groups.items())


def doctor_label(doctor: StaffMember) -> str:
    """'Dr. Sara Khan (Cardiology)'."""
    return f"{doctor.account.display_name} ({doctor.department.name})"


# --- Availability ------------------------------------------------------------------------------------------------


def _day_bounds(on: date) -> tuple[datetime, datetime]:
    start = to_aware(datetime.combine(on, time.min))
    return start, start + timedelta(days=1)


def active_starts(db: Session, staff_id: int, on: date) -> list[datetime]:
    """Hospital-local start times of a doctor's non-canceled appointments on a date."""
    start, end = _day_bounds(on)
    rows = db.scalars(
        select(Appointment.start_time).where(
            Appointment.practitioner_id == staff_id,
            Appointment.start_time >= start,
            Appointment.start_time < end,
            Appointment.canceled.is_(False),
        )
    )
    return [to_local(t) for t in rows]


def _overlaps(slot: datetime, booked: list[datetime], step: timedelta) -> bool:
    return any(abs(b - slot) < step for b in booked)


def free_slots(db: Session, schedule: Schedule, on: date) -> list[datetime]:
    """A doctor's free, not-yet-passed slots on a date (empty if they don't work that day)."""
    if not schedule.is_open(on):
        return []
    step = timedelta(minutes=schedule.slot_minutes)
    booked = active_starts(db, schedule.staff_id, on)
    now = now_local()
    return [s for s in schedule.slot_grid(on) if s >= now and not _overlaps(s, booked, step)]


def nearest_free_text(db: Session, schedule: Schedule, requested: datetime) -> str:
    free = free_slots(db, schedule, requested.date())
    if not free:
        return f"There are no free slots left on {fmt_date(requested)}. Please choose another day."
    before = [s for s in free if s < requested][-1:]
    after = [s for s in free if s >= requested][: 2 - len(before)]
    return "The nearest available times are " + " and ".join(fmt_time(s) for s in before + after) + "."


def availability_summary(
    db: Session, doctor: StaffMember, schedule: Schedule, on: date | None
) -> tuple[str, list[str]]:
    """Spoken availability of one doctor, plus that day's free slot times."""
    window = get_settings().booking_window_days
    who = doctor_label(doctor)
    base = (
        f"Current hospital time is {now_local().strftime('%A, %B %d, %Y at %I:%M %p')}. "
        f"{who} sees patients {schedule_text(schedule)}. "
        f"Appointments are booked only in fixed {schedule.slot_minutes}-minute slots counted from opening time; "
        "in-between times cannot be booked."
    )
    if on is None:
        return f"{base} Appointments can be scheduled from today up to {window} days in advance.", []
    day_text = on.strftime("%A, %B %d, %Y")
    if not schedule.is_open(on):
        return f"{base} {who} has no OPD on {day_text}.", []
    free = [fmt_time(s) for s in free_slots(db, schedule, on)]
    if not free:
        return f"{base} There are no free slots left on {day_text}.", []
    return f"{base} Free slots on {day_text}: {', '.join(free)}.", free


# --- Booking & cancelling ----------------------------------------------------------------------------------------


def book(
    db: Session,
    doctor: StaffMember,
    schedule: Schedule,
    patient: Patient,
    reason: str,
    start: datetime,
    booked_via: str,
) -> BookingResult:
    """Validate a hospital-local start time against every rule, then save the appointment (caller commits)."""
    assert booked_via in BOOKING_CHANNELS
    when = f"{fmt_date(start)} at {fmt_time(start)}"
    who = doctor.account.display_name
    now = now_local()
    window = get_settings().booking_window_days

    if start < now - timedelta(minutes=15):
        return BookingResult(
            False,
            "I'm sorry, but you cannot book an appointment in the past. "
            f"Please choose a time from today up to {window} days ahead.",
        )
    last_day = now.date() + timedelta(days=window)
    if start.date() > last_day:
        return BookingResult(
            False,
            f"I'm sorry, but appointments can only be booked up to {window} days in advance. "
            f"The latest date you can book is {fmt_date(last_day)}.",
        )
    if start.date() in schedule.holidays:
        return BookingResult(False, f"I'm sorry, but the hospital's OPD is closed for a holiday on {fmt_date(start)}.")
    day = schedule.day(start.date())
    if day is None:
        return BookingResult(
            False,
            f"I'm sorry, but {who}'s OPD is closed on {DAY_NAMES[start.weekday()]}s. Please choose a working day.",
        )

    grid = schedule.slot_grid(start.date())
    opening = datetime.combine(start.date(), parse_hhmm(day.start))
    if not grid or start < opening or start > grid[-1]:
        last = f" The last appointment slot is at {fmt_time(grid[-1])}." if grid else ""
        return BookingResult(
            False,
            f"I'm sorry, but {fmt_time(start)} is outside {who}'s OPD hours. {who} is "
            f"available from {day_hours_text(day)}.{last} Please choose a different time.",
        )
    if brk := schedule.break_at(start):
        return BookingResult(
            False,
            f"I'm sorry, {who} is on a break from {_range_text(brk.start, brk.end)}, "
            f"so {fmt_time(start)} cannot be booked. {nearest_free_text(db, schedule, start)}",
        )
    if start not in grid:
        return BookingResult(
            False,
            f"I'm sorry, appointments are booked in fixed {schedule.slot_minutes}-minute "
            f"slots, so {fmt_time(start)} is not a valid slot. "
            f"{nearest_free_text(db, schedule, start)}",
        )

    if patient.id is not None and db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient.id,
            Appointment.start_time == to_aware(start),
            Appointment.canceled.is_(False),
        )
    ):
        return BookingResult(
            False,
            f"It looks like {patient.full_name} already has an appointment on {when}. Please choose a different time.",
        )
    if _overlaps(start, active_starts(db, doctor.id, start.date()), timedelta(minutes=schedule.slot_minutes)):
        return BookingResult(
            False,
            f"I'm sorry, but {who}'s {fmt_time(start)} slot on {fmt_date(start)} is already "
            f"booked. {nearest_free_text(db, schedule, start)}",
        )

    appointment = Appointment(
        patient=patient, practitioner=doctor, reason=reason, start_time=to_aware(start), booked_via=booked_via
    )
    db.add(appointment)
    db.flush()
    return BookingResult(
        True, f"Appointment confirmed for {patient.full_name} on {when} with {who} for {reason}.", appointment
    )


def cancel(db: Session, patient: str | None, on: date, at: time | None = None) -> BookingResult:
    """Cancel active appointments on a date, narrowed by patient name and (if given) a time within 15 minutes."""
    start, end = _day_bounds(on)
    query = select(Appointment).where(
        Appointment.start_time >= start, Appointment.start_time < end, Appointment.canceled.is_(False)
    )
    if patient:
        query = query.join(Appointment.patient).where(Patient.full_name.ilike(f"%{patient}%"))
    matches = list(db.scalars(query).unique())
    if at is not None:
        exact = datetime.combine(on, at)
        near = [a for a in matches if abs(to_local(a.start_time) - exact) <= timedelta(minutes=15)]
        matches = near or matches

    if not matches:
        who = f" for {patient}" if patient else ""
        return BookingResult(False, f"No active appointment was found on {fmt_date(on)}{who}.", status="not_found")
    for appointment in matches:
        appointment.canceled = True
    return BookingResult(
        True, f"Your appointment on {fmt_date(on)} has been successfully canceled.", canceled_count=len(matches)
    )
