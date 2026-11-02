"""Clinic-local time. Booking rules work on naive clinic-local datetimes; the database stores timezone-aware ones."""

from datetime import UTC, datetime

from .config import get_settings


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    """Current clinic-local time, naive (e.g. 2026-11-02 14:30 in Asia/Karachi)."""
    return datetime.now(get_settings().tz).replace(tzinfo=None)


def to_aware(local: datetime) -> datetime:
    """Naive clinic-local -> timezone-aware, for storing."""
    return local.replace(tzinfo=get_settings().tz)


def to_local(moment: datetime) -> datetime:
    """Aware (any zone) -> naive clinic-local, for applying schedule rules."""
    return moment.astimezone(get_settings().tz).replace(tzinfo=None)
