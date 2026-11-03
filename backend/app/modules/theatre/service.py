"""Theatre lists in the database ⇄ the planner. `load` builds a Snapshot from the tables; the planner (engine/) reads
and changes it; `save` writes back only what changed. Writes take a transaction-level advisory lock, so two people
moving cases at once are applied one after the other."""

from dataclasses import dataclass
from datetime import date, time, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.clock import now_local
from app.core.pagination import clamp, decode_cursor, encode_cursor
from app.modules.clinical import add_allergy, add_history, allergy_text, latest_lab_values
from app.modules.patients import Patient
from app.modules.staff import StaffMember

from .demo import birth_date, split_allergies
from .engine.snapshot import Case, Leave, Person, Proc, Room, Snapshot, Surgeon
from .models import PreopAssessment, Procedure, StaffLeave, SurgicalCase, Theatre, TheatreRoster

WRITE_LOCK = 0x7EA7_0001  # pg_advisory_xact_lock key for theatre list changes
CARDIAC_INTS = ("lvef", "nyha", "pa_systolic")
CARDIAC_FLAGS = (
    "ccs4",
    "iddm",
    "recent_mi",
    "redo",
    "lung",
    "arteriopathy",
    "poor_mobility",
    "dialysis",
    "endocarditis",
    "critical",
)


def today() -> date:
    return now_local().date()


def minutes_now() -> int:
    now = now_local()
    return now.hour * 60 + now.minute


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _age(dob: date | None, on: date) -> int:
    if dob is None:
        return 50  # unknown: the risk model's population is middle-aged
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def _cardiac(preop: PreopAssessment | None) -> dict | None:
    if preop is None or all(getattr(preop, k) in (None, False) for k in CARDIAC_INTS + CARDIAC_FLAGS):
        return None
    return {k: getattr(preop, k) for k in CARDIAC_INTS} | {k: int(getattr(preop, k)) for k in CARDIAC_FLAGS}


@dataclass
class Loaded:
    snap: Snapshot
    rows: dict[int, SurgicalCase]
    stored: dict[int, tuple]


def load(db: Session, since: date | None = None, patient_ids: tuple[int, ...] = ()) -> Loaded:
    """Everything the planner needs: theatres, procedures, surgeons (staff whose specialty a theatre does) with
    rosters and leave, and every open case on the waiting list or listed from `since` (default today) on."""
    day0 = today()
    since = min(since or day0, day0)
    theatres = db.scalars(select(Theatre).where(Theatre.active).order_by(Theatre.code)).all()
    rooms = [Room(t.id, t.code, t.name, t.specialty, t.cleaning_minutes) for t in theatres]
    procs = {
        p.code: Proc(
            p.code,
            p.title,
            p.specialty,
            (p.induction, p.lead_in, p.incision, p.lead_out, p.emergence),
            p.variance,
            p.risk_model,
            p.euro_weight,
            p.aorta,
            p.source,
        )
        for p in db.scalars(select(Procedure))
    }
    specialties = {r.specialty for r in rooms}
    surgeons = {
        m.id: Surgeon(m.id, m.display_name, m.specialty or "", m.account.active)
        for m in db.scalars(select(StaffMember).where(StaffMember.specialty.in_(specialties)).order_by(StaffMember.id))
    }
    for r in db.scalars(select(TheatreRoster).where(TheatreRoster.staff_id.in_(surgeons))):
        surgeons[r.staff_id].days[r.weekday] = (_minutes(r.starts), _minutes(r.ends))
    for leave in db.scalars(
        select(StaffLeave).where(StaffLeave.staff_id.in_(surgeons), StaffLeave.ends_on >= since - timedelta(days=1))
    ):
        surgeons[leave.staff_id].leave.append(Leave(leave.id, leave.starts_on, leave.ends_on, leave.reason))

    rows = {
        c.id: c
        for c in db.scalars(
            select(SurgicalCase).where(
                SurgicalCase.canceled.is_(False),
                or_(SurgicalCase.scheduled_on.is_(None), SurgicalCase.scheduled_on >= since),
            )
        ).unique()
    }
    wanted = sorted({c.patient_id for c in rows.values()} | set(patient_ids))
    labs, allergies = latest_lab_values(db, wanted), allergy_text(db, wanted)
    patients = {
        p.id: Person(
            p.id,
            p.full_name,
            {"Female": "F", "Male": "M"}.get(p.sex or "", ""),
            _age(p.date_of_birth, day0),
            allergies.get(p.id, "None known"),
            labs.get(p.id, {}),
        )
        for p in db.scalars(select(Patient).where(Patient.id.in_(wanted)))
    }
    cases = {}
    for c in rows.values():
        preop = c.preop
        cases[c.id] = Case(
            id=c.id,
            patient_id=c.patient_id,
            code=c.procedure_code,
            room_id=c.theatre_id,
            day=c.scheduled_on,
            seq=c.seq,
            urgency=c.urgency,
            overrun=c.overrun_minutes,
            surgeon_id=c.surgeon_id,
            deferred=c.deferred,
            asa=preop.asa if preop else 2,
            weight_kg=preop.weight_kg if preop else None,
            height_cm=preop.height_cm if preop else None,
            cardiac=_cardiac(preop),
        )
    snap = Snapshot(day0, rooms, procs, surgeons, patients, cases)
    return Loaded(snap, rows, {c.id: c.stored() for c in cases.values()})


def lock(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK})


def save(db: Session, loaded: Loaded, actor: str) -> dict[int, int]:
    """Write the snapshot's changes. Returns temp id -> saved id for new cases. Days touched are in `touched`."""
    snap = loaded.snap
    patient_ids: dict[int, int] = {}
    for temp, p in snap.new_patients.items():
        patient = Patient(
            full_name=p["full_name"], sex=p["sex"] or None, date_of_birth=birth_date(p["age"], snap.today)
        )
        db.add(patient)
        db.flush()
        patient_ids[temp] = patient.id
        for substance, reaction in split_allergies(p["allergies"]):
            add_allergy(db, patient.id, substance, reaction)
        audit(actor, "patient.registered", db=db, patient_id=patient.id, source="theatre")
    for patient_id, kind, day, line in snap.new_history:
        add_history(db, patient_ids.get(patient_id, patient_id), kind, day, line)

    new_ids: dict[int, int] = {}
    for case in snap.cases.values():
        if case.id < 0:
            row = SurgicalCase(
                patient_id=patient_ids.get(case.patient_id, case.patient_id),
                procedure_code=case.code,
                theatre_id=case.room_id,
                scheduled_on=case.day,
                seq=case.seq,
                urgency=case.urgency,
                overrun_minutes=case.overrun,
                surgeon_id=case.surgeon_id,
                deferred=case.deferred,
                created_by=actor,
            )
            cardiac = case.cardiac or {}
            row.preop = PreopAssessment(
                asa=case.asa,
                weight_kg=case.weight_kg,
                height_cm=case.height_cm,
                **{k: cardiac[k] for k in CARDIAC_INTS if cardiac.get(k) is not None},
                **{k: bool(cardiac[k]) for k in CARDIAC_FLAGS if k in cardiac},
            )
            db.add(row)
            db.flush()
            new_ids[case.id] = row.id
            audit(
                actor,
                "theatre.case_booked",
                db=db,
                case_id=row.id,
                patient_id=row.patient_id,
                urgency=case.urgency,
                day=case.day.isoformat() if case.day else None,
            )
        elif case.stored() != loaded.stored[case.id]:
            row = loaded.rows[case.id]
            before = loaded.stored[case.id]
            row.theatre_id, row.scheduled_on, row.seq, row.urgency = case.room_id, case.day, case.seq, case.urgency
            row.overrun_minutes, row.surgeon_id, row.deferred = case.overrun, case.surgeon_id, case.deferred
            if (before[1], before[2]) != (case.day, case.seq):
                audit(
                    actor,
                    "theatre.case_moved",
                    db=db,
                    case_id=case.id,
                    day=case.day.isoformat() if case.day else None,
                    seq=case.seq,
                    deferred=case.deferred,
                )
            else:
                audit(actor, "theatre.case_updated", db=db, case_id=case.id)
    for case_id in snap.canceled:
        if case_id in loaded.rows:
            loaded.rows[case_id].canceled = True
            audit(actor, "theatre.case_canceled", db=db, case_id=case_id)
    db.flush()
    return new_ids


def touched_days(loaded: Loaded) -> list[str]:
    """Days whose lists the saved changes affect, for the live event."""
    days = set()
    for case in loaded.snap.cases.values():
        before = loaded.stored.get(case.id)
        if before is None or before != case.stored():
            days |= {d for d in (case.day, before[1] if before else None) if d}
    days |= {loaded.stored[c][1] for c in loaded.snap.canceled if c in loaded.stored and loaded.stored[c][1]}
    return sorted(d.isoformat() for d in days)


# --- Reads that need no planner ----------------------------------------------------------------------------------


def get_case_row(db: Session, case_id: int) -> SurgicalCase:
    row = db.get(SurgicalCase, case_id)
    if row is None or row.canceled:
        raise HTTPException(404, "No such case")
    return row


def _off_list_page(db: Session, where, cursor: str | None, limit: int) -> dict:
    """A page of cases off today's lists (waiting or moved later), newest change first."""
    limit = clamp(limit)
    query = select(SurgicalCase).where(SurgicalCase.canceled.is_(False), *where)
    if cursor:
        key, row_id = decode_cursor(cursor)
        query = query.where(
            or_(SurgicalCase.created_at < key, (SurgicalCase.created_at == key) & (SurgicalCase.id < row_id))
        )
    rows = db.scalars(query.order_by(SurgicalCase.created_at.desc(), SurgicalCase.id.desc()).limit(limit + 1)).all()
    items = list(rows[:limit])
    names = dict(
        db.execute(select(Patient.id, Patient.full_name).where(Patient.id.in_({r.patient_id for r in items}))).all()
    )
    procs = {
        p.code: p for p in db.scalars(select(Procedure).where(Procedure.code.in_({r.procedure_code for r in items})))
    }
    staff = {
        m.id: m.display_name
        for m in db.scalars(
            select(StaffMember).where(StaffMember.id.in_({r.surgeon_id for r in items if r.surgeon_id}))
        )
    }
    return {
        "items": [
            {
                "id": r.id,
                "patient_id": r.patient_id,
                "name": names.get(r.patient_id, ""),
                "code": r.procedure_code,
                "procedure": procs[r.procedure_code].title,
                "specialty": procs[r.procedure_code].specialty,
                "minutes": procs[r.procedure_code].minutes,
                "theatre_id": r.theatre_id,
                "day": r.scheduled_on,
                "urgency": r.urgency,
                "surgeon_id": r.surgeon_id,
                "surgeon": staff.get(r.surgeon_id),
                "listed_at": r.created_at,
            }
            for r in items
        ],
        "next_cursor": encode_cursor(items[-1].created_at, items[-1].id) if len(rows) > limit else None,
    }


def waiting_page(db: Session, urgency: str | None, cursor: str | None, limit: int) -> dict:
    where = [SurgicalCase.scheduled_on.is_(None)]
    if urgency:
        where.append(SurgicalCase.urgency == urgency)
    return _off_list_page(db, where, cursor, limit)


def deferred_page(db: Session, cursor: str | None, limit: int) -> dict:
    return _off_list_page(db, [SurgicalCase.deferred.is_(True), SurgicalCase.scheduled_on > today()], cursor, limit)


def off_list_counts(db: Session) -> dict[str, int]:
    base = select(func.count()).select_from(SurgicalCase).where(SurgicalCase.canceled.is_(False))
    waiting = db.scalar(base.where(SurgicalCase.scheduled_on.is_(None))) or 0
    urgent = (
        db.scalar(base.where(SurgicalCase.scheduled_on.is_(None), SurgicalCase.urgency.in_(("immediate", "urgent"))))
        or 0
    )
    later = db.scalar(base.where(SurgicalCase.deferred.is_(True), SurgicalCase.scheduled_on > today())) or 0
    return {"waiting": waiting, "urgent_waiting": urgent, "later": later}


def patient_cases(db: Session, patient_id: int) -> list[dict]:
    rows = (
        db.scalars(
            select(SurgicalCase)
            .where(SurgicalCase.patient_id == patient_id)
            .order_by(SurgicalCase.scheduled_on.desc().nulls_first(), SurgicalCase.id.desc())
        )
        .unique()
        .all()
    )
    procs = {p.code: p for p in db.scalars(select(Procedure))}
    theatres = {t.id: t.code for t in db.scalars(select(Theatre))}
    return [
        {
            "id": r.id,
            "procedure": procs[r.procedure_code].title,
            "code": r.procedure_code,
            "theatre": theatres.get(r.theatre_id),
            "day": r.scheduled_on,
            "urgency": r.urgency,
            "deferred": r.deferred,
            "canceled": r.canceled,
        }
        for r in rows
    ]


def theatres(db: Session) -> list[Theatre]:
    return list(db.scalars(select(Theatre).where(Theatre.active).order_by(Theatre.code)))


def procedures(db: Session) -> list[Procedure]:
    return list(db.scalars(select(Procedure).where(Procedure.active).order_by(Procedure.specialty, Procedure.title)))


# --- Rosters and leave -------------------------------------------------------------------------------------------


def surgeon(db: Session, staff_id: int) -> StaffMember:
    member = db.get(StaffMember, staff_id)
    specialties = {t.specialty for t in theatres(db)}
    if member is None or member.specialty not in specialties:
        raise HTTPException(404, "No surgeon with that id")
    return member


def replace_roster(db: Session, actor: str, staff_id: int, days: list[tuple[int, int, int]]) -> None:
    surgeon(db, staff_id)
    for row in db.scalars(select(TheatreRoster).where(TheatreRoster.staff_id == staff_id)):
        db.delete(row)
    db.flush()
    for weekday, start, end in days:
        db.add(
            TheatreRoster(
                staff_id=staff_id, weekday=weekday, starts=time(start // 60, start % 60), ends=time(end // 60, end % 60)
            )
        )
    audit(actor, "theatre.roster_saved", db=db, staff_id=staff_id, days=len(days))


def add_leave(db: Session, actor: str, staff_id: int, starts_on: date, ends_on: date, reason: str) -> StaffLeave:
    surgeon(db, staff_id)
    leave = StaffLeave(staff_id=staff_id, starts_on=starts_on, ends_on=ends_on, reason=reason or "Leave")
    db.add(leave)
    db.flush()
    audit(actor, "theatre.leave_added", db=db, staff_id=staff_id, leave_id=leave.id)
    return leave


def delete_leave(db: Session, actor: str, leave_id: int) -> None:
    leave = db.get(StaffLeave, leave_id)
    if leave is None:
        raise HTTPException(404, "No such leave")
    db.delete(leave)
    audit(actor, "theatre.leave_deleted", db=db, staff_id=leave.staff_id, leave_id=leave_id)
