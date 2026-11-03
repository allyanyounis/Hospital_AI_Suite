"""OPD scheduling: each bookable doctor's week (days and breaks) and the hospital's closed dates."""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    SmallInteger,
    String,
    Time,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column


class DoctorSchedule(Base):
    """One per doctor. Its absence means the doctor's week was never saved and the default week applies."""

    __tablename__ = "doctor_schedules"
    __table_args__ = (CheckConstraint("slot_minutes BETWEEN 5 AND 120", name="slot_minutes"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id", ondelete="CASCADE"), unique=True)
    slot_minutes: Mapped[int] = mapped_column(SmallInteger, default=15, server_default="15")
    updated_at: Mapped[datetime] = now_column(onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.username"))
    days: Mapped[list["ScheduleDay"]] = relationship(
        order_by="ScheduleDay.weekday", cascade="all, delete-orphan", passive_deletes=True
    )


class ScheduleDay(Base):
    """Hours for one weekday (0 = Monday). Hours of a disabled day are kept so the Scheduler remembers them."""

    __tablename__ = "schedule_days"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        CheckConstraint("NOT enabled OR closes > opens", name="closes_after_opens"),
    )

    schedule_id: Mapped[int] = mapped_column(ForeignKey("doctor_schedules.id", ondelete="CASCADE"), primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    opens: Mapped[time] = mapped_column(Time)
    closes: Mapped[time] = mapped_column(Time)
    breaks: Mapped[list["ScheduleBreak"]] = relationship(
        order_by="ScheduleBreak.starts", cascade="all, delete-orphan", passive_deletes=True
    )


class ScheduleBreak(Base):
    __tablename__ = "schedule_breaks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_id", "weekday"],
            ["schedule_days.schedule_id", "schedule_days.weekday"],
            ondelete="CASCADE",
            name="fk_schedule_breaks_day",
        ),
        CheckConstraint("ends > starts", name="ends_after_starts"),
    )

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    starts: Mapped[time] = mapped_column(Time, primary_key=True)
    ends: Mapped[time] = mapped_column(Time)


class HospitalClosure(Base):
    """A date the hospital's OPD is closed (public holiday), for every doctor."""

    __tablename__ = "hospital_closures"

    closed_on: Mapped[date] = mapped_column(Date, primary_key=True)
    reason: Mapped[str | None] = mapped_column(String(120))
