"""Operating theatre API: the board, lists, booking, emergencies, rosters and leave, and the research insights.

Routes are plain (sync) functions: the planner's Monte Carlo runs in FastAPI's thread pool, off the event loop.
Every change commits, is audited, and is announced as `theatre_updated` (with the days it touched) on /api/events.
`at` (minutes after midnight) replays the day at another time for demos; for changes only admins may use it.
"""

from datetime import date
from functools import partial

from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.events import broadcaster
from app.core.pagination import Page
from app.modules.auth import User, require

from . import insights, service
from .engine import planner
from .schemas import (
    Action,
    ActionIn,
    CaseIn,
    ExperimentIn,
    IntakeIn,
    LeaveIn,
    ProcedureOut,
    RosterIn,
    TheatreOut,
    Urgency,
)

router = APIRouter(prefix="/api/theatre", tags=["theatre"])
view = require("theatre.view")
manage = require("theatre.manage")
roster = require("theatre.roster")
research = require("theatre.insights")
AT = Query(None, ge=0, le=24 * 60, description="Replay at this minute of the day (demo clock)")


def _now(at: int | None, user: User | None = None) -> int:
    if at is not None and (user is None or user.role == "admin"):
        return at
    return service.minutes_now()


def _publish(days: list[str]) -> None:
    from_thread.run(partial(broadcaster.publish, "theatre_updated", days=days))


def _fail(error: str | None) -> None:
    if error:
        raise HTTPException(422, error)


def _commit(db: Session, loaded: service.Loaded, user: User) -> dict[int, int]:
    new_ids = service.save(db, loaded, user.username)
    days = service.touched_days(loaded)
    db.commit()
    _publish(days)
    return new_ids


# --- Reading -----------------------------------------------------------------------------------------------------


@router.get("/board")
def board(day: date | None = None, at: int | None = AT, db: Session = Depends(get_db), _: User = Depends(view)):
    """Every theatre's list for `day` (default today): cases with phases and state, forecast, finish, move tip;
    today also the emergency proposals. Waiting and moved-later lists are paged separately (counts here)."""
    loaded = service.load(db, since=day)
    return planner.board(loaded.snap, _now(at), day, with_proposals=True) | service.off_list_counts(db)


@router.get("/waiting", response_model=Page[dict])
def waiting(
    urgency: Urgency | None = None,
    cursor: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(view),
):
    return service.waiting_page(db, urgency, cursor or None, limit)


@router.get("/deferred", response_model=Page[dict])
def deferred(cursor: str = "", limit: int = 50, db: Session = Depends(get_db), _: User = Depends(view)):
    return service.deferred_page(db, cursor or None, limit)


@router.get("/calendar")
def calendar(
    start: date | None = None,
    procedure: str | None = None,
    surgeon_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(view),
):
    """One week from `start` (default today) × every theatre; with `procedure`, where it fits or why not."""
    loaded = service.load(db, since=start)
    if procedure and procedure not in loaded.snap.procs:
        raise HTTPException(404, "No such operation")
    return planner.calendar(loaded.snap, start or loaded.snap.today, procedure, surgeon_id)


@router.get("/cases/{case_id}")
def case_detail(case_id: int, at: int | None = AT, db: Session = Depends(get_db), _: User = Depends(view)):
    row = service.get_case_row(db, case_id)
    loaded = service.load(db, since=row.scheduled_on)
    return planner.case_detail(loaded.snap, case_id, _now(at))


@router.get("/patients/{patient_id}/cases")
def patient_cases(patient_id: int, db: Session = Depends(get_db), _: User = Depends(view)):
    return service.patient_cases(db, patient_id)


@router.get("/theatres", response_model=list[TheatreOut])
def theatres(db: Session = Depends(get_db), _: User = Depends(view)):
    return [TheatreOut.of(t) for t in service.theatres(db)]


@router.get("/procedures", response_model=list[ProcedureOut])
def procedures(db: Session = Depends(get_db), _: User = Depends(view)):
    return [ProcedureOut.of(p) for p in service.procedures(db)]


@router.get("/surgeons")
def surgeons(db: Session = Depends(get_db), _: User = Depends(view)):
    return planner.surgeons_view(service.load(db).snap)


# --- Changing the lists ------------------------------------------------------------------------------------------


@router.post("/cases", status_code=201)
def book(req: CaseIn, db: Session = Depends(get_db), user: User = Depends(manage)):
    """Book a case on `day`, or put it on the waiting list."""
    service.lock(db)
    loaded = service.load(db, patient_ids=(req.patient_id,) if req.patient_id else ())
    error, temp_id = planner.create_case(loaded.snap, req.planner())
    _fail(error)
    new_ids = _commit(db, loaded, user)
    return {"case": new_ids[temp_id]}


@router.post("/cases/{case_id}/{action}")
def act(
    case_id: int,
    action: Action,
    req: ActionIn | None = None,
    at: int | None = AT,
    db: Session = Depends(get_db),
    user: User = Depends(manage),
):
    """One action on a case: move earlier/later on its list, book by urgency, schedule on a day, back to the
    waiting list, defer to a later day, cancel, record an overrun, change surgeon or urgency."""
    req = req or ActionIn()
    service.lock(db)
    row = service.get_case_row(db, case_id)
    loaded = service.load(db, since=row.scheduled_on)
    _fail(planner.act(loaded.snap, case_id, action, _now(at, user), **req.model_dump(exclude_none=True)))
    _commit(db, loaded, user)
    return {"ok": True}


@router.post("/intake/preview")
def intake_preview(req: IntakeIn, at: int | None = AT, db: Session = Depends(get_db), user: User = Depends(manage)):
    """Where an emergency would go, who is pushed back, and up to three moves that keep the room on time. Saves
    nothing."""
    loaded = service.load(db, patient_ids=(req.patient_id,) if req.patient_id else ())
    result = planner.intake(loaded.snap, req.planner(), _now(at, user))
    _fail(result.get("error"))
    return result


@router.post("/intake/confirm")
def intake_confirm(req: IntakeIn, at: int | None = AT, db: Session = Depends(get_db), user: User = Depends(manage)):
    """Place the emergency and apply only the moves the user ticked."""
    service.lock(db)
    loaded = service.load(db, patient_ids=(req.patient_id,) if req.patient_id else ())
    result = planner.intake(loaded.snap, req.planner(), _now(at, user), confirm=True)
    _fail(result.get("error"))
    new_ids = _commit(db, loaded, user)
    return {"case": new_ids.get(result["case"], result["case"]), "slot": result["slot"]}


# --- Rosters and leave -------------------------------------------------------------------------------------------


@router.put("/surgeons/{staff_id}/roster")
def save_roster(staff_id: int, req: RosterIn, db: Session = Depends(get_db), user: User = Depends(roster)):
    service.replace_roster(db, user.username, staff_id, [(d.weekday, d.start, d.end) for d in req.days])
    db.commit()
    _publish([])
    return {"ok": True}


@router.post("/leave", status_code=201)
def add_leave(req: LeaveIn, db: Session = Depends(get_db), user: User = Depends(roster)):
    """Record leave; returns the surgeon's cases in that period with a colleague who can cover or a later slot."""
    leave = service.add_leave(db, user.username, req.staff_id, req.starts_on, req.ends_on, req.reason)
    loaded = service.load(db)
    conflicts = planner.leave_conflicts(loaded.snap, req.staff_id, req.starts_on, req.ends_on)
    db.commit()
    _publish([])
    return {"id": leave.id, "conflicts": conflicts}


@router.delete("/leave/{leave_id}")
def delete_leave(leave_id: int, db: Session = Depends(get_db), user: User = Depends(roster)):
    service.delete_leave(db, user.username, leave_id)
    db.commit()
    _publish([])
    return {"ok": True}


# --- Research ----------------------------------------------------------------------------------------------------


@router.get("/insights/model-audit")
def model_audit(_: User = Depends(research)):
    return insights.model_audit()


@router.get("/insights/experiment")
def experiment(_: User = Depends(research)):
    return insights.experiment_summary()


@router.post("/insights/experiment/run")
def run_experiment(req: ExperimentIn, _: User = Depends(research)):
    """Replan one simulated day with CP-SAT (a few seconds). Never touches the real lists."""
    result = insights.run_one_day(req.model_dump())
    _fail(result.get("error"))
    return result
