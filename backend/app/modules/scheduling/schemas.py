"""A doctor's weekly OPD schedule and the rules derived from it (slot grid, breaks, working time), plus the
hospital's closed dates.

Times are "HH:MM" strings in the hospital's timezone; zero-padded, so they compare correctly as strings.
"""

from datetime import date, datetime, time, timedelta

from pydantic import BaseModel, Field, model_validator

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def parse_hhmm(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


class BreakPeriod(BaseModel):
    start: str = Field(pattern=HHMM)
    end: str = Field(pattern=HHMM)


class DaySchedule(BaseModel):
    enabled: bool = False
    start: str = Field("09:00", pattern=HHMM)
    end: str = Field("17:00", pattern=HHMM)
    breaks: list[BreakPeriod] = Field(default_factory=list)

    def periods(self) -> list[tuple[str, str]]:
        """Working periods: the day split around its breaks, e.g. [("09:00", "13:00"), ("14:00", "17:00")]."""
        edges = [self.start]
        for b in sorted(self.breaks, key=lambda b: b.start):
            edges += [b.start, b.end]
        edges.append(self.end)
        return list(zip(edges[::2], edges[1::2], strict=False))


class ScheduleIn(BaseModel):
    """A doctor's week as the Scheduler sends it."""

    days: list[DaySchedule] = Field(min_length=7, max_length=7)  # Monday first
    slot_minutes: int = Field(15, ge=5, le=120)

    @model_validator(mode="after")
    def _check(self) -> "ScheduleIn":
        for name, day in zip(DAY_NAMES, self.days, strict=False):
            if not day.enabled:
                continue
            if day.end <= day.start:
                raise ValueError(f"{name}: finish time must be after start time")
            previous_end = day.start
            for b in sorted(day.breaks, key=lambda b: b.start):
                if b.end <= b.start:
                    raise ValueError(f"{name}: a break must end after it starts")
                if b.start < previous_end or b.end > day.end:
                    raise ValueError(f"{name}: breaks must be inside working hours and must not overlap")
                previous_end = b.end
        return self


class ScheduleOut(ScheduleIn):
    staff_id: int | None = None
    is_default: bool = False
    updated_at: datetime | None = None


class Schedule(ScheduleOut):
    """A doctor's saved week with the hospital's closed dates, and the rules every module uses."""

    holidays: list[date] = Field(default_factory=list)

    def day(self, on: date) -> DaySchedule | None:
        """That weekday's hours, or None if it is a day off."""
        d = self.days[on.weekday()]
        return d if d.enabled else None

    def is_open(self, on: date) -> bool:
        return on not in self.holidays and self.day(on) is not None

    def slot_grid(self, on: date) -> list[datetime]:
        """Bookable slot start times (naive, clinic-local): every slot length from opening, restarting after each
        break, keeping only slots that finish in time. 9-17 with 30 min -> 9:00, 9:30 ... 16:30."""
        day = self.day(on)
        if day is None:
            return []
        step = timedelta(minutes=self.slot_minutes)
        slots = []
        for start, end in day.periods():
            current = datetime.combine(on, parse_hhmm(start))
            closing = datetime.combine(on, parse_hhmm(end))
            while current + step <= closing:
                slots.append(current)
                current += step
        return slots

    def break_at(self, moment: datetime) -> BreakPeriod | None:
        """The break a slot starting at this (clinic-local) time would run into, if any."""
        day = self.day(moment.date())
        if day is None:
            return None
        slot_end = (moment + timedelta(minutes=self.slot_minutes)).time()
        for b in day.breaks:
            if moment.time() < parse_hhmm(b.end) and slot_end > parse_hhmm(b.start):
                return b
        return None

    def is_working_time(self, moment: datetime) -> bool:
        """Inside the day's opening hours (a break still counts as the working day, not after hours)."""
        day = self.day(moment.date())
        return day is not None and day.start <= moment.strftime("%H:%M") < day.end


def default_schedule(staff_id: int | None = None, holidays: list[date] | None = None) -> Schedule:
    """Used until a doctor's week is saved: Monday to Friday, 09:00-17:00 with a 13:00-14:00 lunch break."""
    lunch = [BreakPeriod(start="13:00", end="14:00")]
    return Schedule(
        staff_id=staff_id,
        days=[DaySchedule(enabled=i < 5, start="09:00", end="17:00", breaks=lunch) for i in range(7)],
        slot_minutes=15,
        holidays=holidays or [],
        is_default=True,
    )


class Closure(BaseModel):
    """A date the whole hospital's OPD is closed."""

    date: date
    reason: str = Field(default="", max_length=120)


class ClosuresIn(BaseModel):
    closures: list[Closure]

    @model_validator(mode="after")
    def _unique(self) -> "ClosuresIn":
        self.closures = sorted({c.date: c for c in self.closures}.values(), key=lambda c: c.date)
        return self
