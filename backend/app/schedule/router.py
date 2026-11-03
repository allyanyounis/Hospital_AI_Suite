from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..audit import audit
from ..database import get_db
from ..events import broadcaster
from ..security import User, current_user
from . import ClinicSchedule, ClinicScheduleIn, load_schedule, save_schedule

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("", response_model=ClinicSchedule)
def get_schedule(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return load_schedule(db)


@router.put("", response_model=ClinicSchedule)
async def update_schedule(req: ClinicScheduleIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    save_schedule(db, req, user.username)
    audit(
        user.username,
        "schedule.updated",
        db=db,
        working_days=sum(d.enabled for d in req.days),
        slot_minutes=req.slot_minutes,
        holidays=len(req.holidays),
    )
    db.commit()
    await broadcaster.publish("schedule_updated")
    return load_schedule(db)
