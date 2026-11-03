"""Pilot metrics: the burnout case in numbers. Built from timings and edit counts, never from clinical content."""

from collections import Counter
from datetime import timedelta
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..clock import now_local, now_utc, to_local
from ..config import Settings
from ..models import AuditLog, User
from ..schedule import load_schedule
from .models import Encounter
from .notes import GeneratedNote


def edit_counts(draft: GeneratedNote, final: GeneratedNote) -> dict[str, int]:
    """How much the clinician changed the draft: lines kept verbatim, added (incl. rewritten) and removed."""
    drafted = Counter((s.heading, st.text.strip()) for s in draft.sections for st in s.statements)
    signed = Counter((s.heading, st.text.strip()) for s in final.sections for st in s.statements if st.text.strip())
    kept = sum((drafted & signed).values())
    return {
        "lines_drafted": sum(drafted.values()),
        "lines_kept": kept,
        "lines_added": sum(signed.values()) - kept,
        "lines_removed": sum(drafted.values()) - kept,
    }


def compute(db: Session, settings: Settings, username: str | None, days: int = 30) -> dict:
    """Metrics for one clinician, or for everyone when username is None."""
    since = now_utc() - timedelta(days=days)
    encounters = select(Encounter).where(Encounter.created_at >= since)
    actions = (
        select(AuditLog.action, func.count())
        .where(AuditLog.ts >= since, AuditLog.action.in_(["note.reviewed", "document.generated"]))
        .group_by(AuditLog.action)
    )
    if username:
        encounters = encounters.where(Encounter.username == username)
        actions = actions.where(AuditLog.username == username)
    rows = list(db.scalars(encounters))
    action_counts = dict(db.execute(actions).all())

    approved = [r for r in rows if r.approved_at and r.drafted_at]
    draft_times = [r.draft_seconds for r in rows if r.draft_seconds]
    review_minutes = [(r.approved_at - r.drafted_at).total_seconds() / 60 for r in approved]
    drafted_lines = sum(r.lines_drafted or 0 for r in approved)
    kept_lines = sum(r.lines_kept or 0 for r in approved)
    baseline = settings.baseline_minutes_per_note

    schedule = load_schedule(db)
    today = now_local().date()
    per_day = Counter(to_local(r.approved_at).date() for r in approved)

    result = {
        "scope": "me" if username else "all",
        "days": days,
        "baseline_minutes_per_note": baseline,
        "workday": "the clinic's Scheduler hours"
        + (" (default; set them in Scheduler)" if schedule.is_default else ""),
        "encounters": len(rows),
        "notes_approved": len(approved),
        "median_draft_seconds": round(median(draft_times)) if draft_times else None,
        "median_review_minutes": round(median(review_minutes), 1) if review_minutes else None,
        "lines_kept_pct": round(100 * kept_lines / drafted_lines) if drafted_lines else None,
        "est_minutes_saved": round(sum(max(0.0, baseline - min(m, baseline)) for m in review_minutes)),
        "after_hours_approvals": sum(not schedule.is_working_time(to_local(r.approved_at)) for r in approved),
        "reviews_run": action_counts.get("note.reviewed", 0),
        "documents_generated": action_counts.get("document.generated", 0),
        "by_day": [
            {"date": (d := today - timedelta(days=i)).isoformat(), "approved": per_day.get(d, 0)}
            for i in range(13, -1, -1)
        ],
    }
    if username is None:
        names = dict(db.execute(select(User.username, User.display_name)).all())
        per_user = Counter(r.username for r in approved)
        result["by_clinician"] = [
            {"username": u, "name": names.get(u, u), "notes_approved": n} for u, n in per_user.most_common()
        ]
    return result
