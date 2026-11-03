"""OPD schedules per doctor and the hospital's closed dates."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.database import get_db
from app.core.events import broadcaster
from app.modules.auth import User, require
from app.modules.staff import get_bookable

from .schemas import Closure, ClosuresIn, ScheduleIn, ScheduleOut
from .service import list_closures, load_schedule, save_closures, save_schedule

router = APIRouter(prefix="/api", tags=["scheduling"])


@router.get("/schedules/{staff_id}", response_model=ScheduleOut)
def get_schedule(staff_id: int, db: Session = Depends(get_db), _: User = Depends(require("schedule.view"))):
    get_bookable(db, staff_id)
    return load_schedule(db, staff_id)


@router.put("/schedules/{staff_id}", response_model=ScheduleOut)
async def update_schedule(
    staff_id: int, req: ScheduleIn, db: Session = Depends(get_db), user: User = Depends(require("schedule.edit"))
):
    get_bookable(db, staff_id)
    save_schedule(db, staff_id, req, user.username)
    audit(
        user.username,
        "schedule.updated",
        db=db,
        staff_id=staff_id,
        working_days=sum(d.enabled for d in req.days),
        slot_minutes=req.slot_minutes,
    )
    db.commit()
    await broadcaster.publish("schedule_updated")
    return load_schedule(db, staff_id)


@router.get("/closures", response_model=list[Closure])
def get_closures(db: Session = Depends(get_db), _: User = Depends(require("schedule.view"))):
    return list_closures(db)


@router.put("/closures", response_model=list[Closure])
async def update_closures(
    req: ClosuresIn, db: Session = Depends(get_db), user: User = Depends(require("schedule.edit"))
):
    save_closures(db, req.closures)
    audit(user.username, "closures.updated", db=db, count=len(req.closures))
    db.commit()
    await broadcaster.publish("schedule_updated")
    return list_closures(db)
