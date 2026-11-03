"""The demo hospital from the Operation Theatre POC (data/demo.json, exported by tools/theatre/export_poc.py): five
surgical specialties with a theatre each, ten surgeons, 114 synthetic patients with labs, vitals, reports and
history, and their cases.

Days in the file are offsets from the POC's "today". They are replayed from the date with the same weekday nearest
to the real today, so rosters (by weekday) still match.
"""

import json
import secrets
from datetime import date, datetime, time, timedelta
from functools import cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import to_aware
from app.modules.auth import Account, create_account
from app.modules.clinical import (
    add_allergy,
    add_history,
    add_report,
    ensure_lab_tests,
    record_lab,
    record_vitals,
)
from app.modules.organization import Department
from app.modules.patients import Patient
from app.modules.staff import StaffMember

from .engine.snapshot import Case, Leave, Person, Proc, Room, Snapshot, Surgeon
from .models import PreopAssessment, Procedure, StaffLeave, SurgicalCase, Theatre, TheatreRoster

DEMO_PATH = Path(__file__).resolve().parent / "data" / "demo.json"
MRN_PREFIX = "DEMO-"
VITAL_INTS = ("heart_rate", "systolic_bp", "spo2")
PREOP = (
    "lvef",
    "nyha",
    "pa_systolic",
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


@cache
def demo() -> dict:
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))


def anchor_for(today: date) -> date:
    """The date the POC's "today" is replayed on: the nearest day to `today` with the same weekday."""
    poc_today = date.fromisoformat(demo()["today"])
    back = (today.weekday() - poc_today.weekday()) % 7
    return today - timedelta(days=back) if back <= 3 else today + timedelta(days=7 - back)


def split_allergies(text: str) -> list[tuple[str, str | None]]:
    """ "Penicillin (rash), Latex" -> [("Penicillin", "rash"), ("Latex", None)]."""
    out = []
    for item in filter(None, (part.strip() for part in text.split(","))):
        substance, _, reaction = item.partition("(")
        out.append((substance.strip(), reaction.rstrip(")").strip() or None))
    return out


def birth_date(age: int, on: date) -> date:
    """A date of birth that makes the patient `age` on `on` (and for the next eleven months)."""
    year = on.year - age
    return date(year, on.month, min(on.day, 28)) - timedelta(days=30)


def _risk_model(specialty: str) -> str:
    return "euroscore2" if specialty == "Cardiac" else "vitaldb"


def _latest_labs(rows: list) -> dict[str, float]:
    latest: dict[str, float] = {}
    for _, code, value in sorted(rows, key=lambda r: r[0]):  # stable: same-day results keep their order
        latest[code] = value
    return latest


def _sex_letter(sex: str) -> str:
    return {"Female": "F", "Male": "M"}.get(sex, "")


def demo_snapshot() -> tuple[Snapshot, dict[str, int]]:
    """The demo as a planner snapshot on the POC's own day, without a database (for tests). Ids are 1, 2, … in file
    order; returns the snapshot and POC key ("C07", "S10", "OR 2") -> id."""
    d = demo()
    today = date.fromisoformat(d["today"])
    ids: dict[str, int] = {}
    rooms = []
    for i, r in enumerate(d["rooms"], 1):
        ids[r["id"]] = i
        rooms.append(Room(i, r["id"], f"{r['id']} · {r['specialty']}", r["specialty"], r["cleaning"]))
    procs = {
        p["code"]: Proc(
            p["code"],
            p["title"],
            p["specialty"],
            (p["induction"], p["lead_in"], p["incision"], p["lead_out"], p["emergence"]),
            p["variance"],
            _risk_model(p["specialty"]),
            p["euro_weight"],
            bool(p["aorta"]),
            p["source"] or "",
        )
        for p in d["procedures"]
    }
    surgeons = {}
    for i, s in enumerate(d["surgeons"], 1):
        ids[s["key"]] = i
        surgeons[i] = Surgeon(
            i,
            s["name"],
            s["specialty"],
            s["active"],
            days={wd: (start, end) for wd, start, end in s["days"]},
            leave=[
                Leave(j, today + timedelta(a), today + timedelta(b), reason)
                for j, (a, b, reason) in enumerate(s["leave"], 1)
            ],
        )
    patients, by_key = {}, {}
    for i, p in enumerate(d["patients"], 1):
        ids[p["key"]] = i
        by_key[p["key"]] = p
        patients[i] = Person(
            i, p["name"], _sex_letter(p["sex"]), p["age"], p["allergies"] or "None known", _latest_labs(p["labs"])
        )
    cases = {}
    for i, c in enumerate(d["cases"], 1):
        ids[c["key"]] = i
        p = by_key[c["patient"]]
        cases[i] = Case(
            id=i,
            patient_id=ids[c["patient"]],
            code=c["code"],
            room_id=ids[c["room"]],
            day=None if c["day"] is None else today + timedelta(c["day"]),
            seq=c["seq"],
            urgency=c["urgency"],
            overrun=c["overrun"],
            surgeon_id=ids.get(c["surgeon"]) if c["surgeon"] else None,
            deferred=c["deferred"],
            asa=p["asa"],
            weight_kg=p["weight_kg"],
            height_cm=p["height_cm"],
            cardiac=p["cardiac"],
        )
    return Snapshot(today, rooms, procs, surgeons, patients, cases), ids


# --- Loading the demo into the database --------------------------------------------------------------------------


def _at(day: date, hour: int) -> datetime:
    return to_aware(datetime.combine(day, time(hour)))


def seed(db: Session, today: date) -> dict | None:
    """Load the demo hospital. Returns counts, or None when it is already there (nothing is changed)."""
    d = demo()
    if db.scalar(select(Patient.id).where(Patient.mrn == f"{MRN_PREFIX}{d['patients'][0]['key']}")):
        return None
    anchor = anchor_for(today)
    ensure_lab_tests(db)

    def day(offset: int | None) -> date | None:
        return None if offset is None else anchor + timedelta(days=offset)

    departments = {}
    for specialty, (code, name) in d["departments"].items():
        department = db.scalar(select(Department).where(Department.code == code))
        if department is None:
            department = Department(code=code, name=name, kind="clinical")
            db.add(department)
        departments[specialty] = department
    db.flush()

    theatres = {}
    for r in d["rooms"]:
        theatre = db.scalar(select(Theatre).where(Theatre.code == r["id"]))
        if theatre is None:
            theatre = Theatre(
                code=r["id"],
                name=f"{r['id']} · {r['specialty']}",
                department_id=departments[r["specialty"]].id,
                specialty=r["specialty"],
                cleaning_minutes=r["cleaning"],
            )
            db.add(theatre)
        theatres[r["id"]] = theatre
    for p in d["procedures"]:
        if db.get(Procedure, p["code"]) is None:
            db.add(
                Procedure(
                    code=p["code"],
                    title=p["title"],
                    specialty=p["specialty"],
                    induction=p["induction"],
                    lead_in=p["lead_in"],
                    incision=p["incision"],
                    lead_out=p["lead_out"],
                    emergence=p["emergence"],
                    variance=p["variance"],
                    risk_model=_risk_model(p["specialty"]),
                    euro_weight=p["euro_weight"],
                    aorta=bool(p["aorta"]),
                    source=p["source"] or "",
                )
            )
    db.flush()

    surgeons = {}
    for s in d["surgeons"]:
        if db.get(Account, s["username"]) is None:
            create_account(db, None, s["username"], s["name"], "doctor", secrets.token_urlsafe(18))
        member = db.scalar(select(StaffMember).where(StaffMember.username == s["username"]))
        if member is None:
            member = StaffMember(
                username=s["username"],
                department_id=departments[s["specialty"]].id,
                job_title="Consultant surgeon",
                specialty=s["specialty"],
            )
            db.add(member)
            db.flush()
            for weekday, start, end in s["days"]:
                db.add(TheatreRoster(staff_id=member.id, weekday=weekday, starts=_time(start), ends=_time(end)))
            for a, b, reason in s["leave"]:
                db.add(StaffLeave(staff_id=member.id, starts_on=day(a), ends_on=day(b), reason=reason))
        surgeons[s["key"]] = member

    patients, by_key = {}, {}
    counts = {"patients": 0, "labs": 0, "vitals": 0, "reports": 0, "cases": 0}
    for p in d["patients"]:
        patient = Patient(
            mrn=f"{MRN_PREFIX}{p['key']}",
            full_name=p["name"],
            sex=p["sex"] or None,
            date_of_birth=birth_date(p["age"], anchor),
            registered=True,
        )
        db.add(patient)
        db.flush()
        patients[p["key"]], by_key[p["key"]] = patient, p
        for offset, code, value in p["labs"]:
            record_lab(db, patient.id, code, value, _at(day(offset), 8), source="seed")
        for v in p["vitals"]:
            values = {k: (round(x) if k in VITAL_INTS else x) for k, x in v.items() if k != "day"}
            record_vitals(db, patient.id, _at(day(v["day"]), 7), source="seed", **values)
        for offset, kind, text in p["history"]:
            add_history(db, patient.id, kind, day(offset), text)
        for offset, kind, title, text in p["reports"]:
            add_report(db, patient.id, kind, title, day(offset), text, source="seed")
        for substance, reaction in split_allergies(p["allergies"]):
            add_allergy(db, patient.id, substance, reaction)
        counts["patients"] += 1
        counts["labs"] += len(p["labs"])
        counts["vitals"] += len(p["vitals"])
        counts["reports"] += len(p["reports"])

    for c in d["cases"]:
        p = by_key[c["patient"]]
        case = SurgicalCase(
            patient_id=patients[c["patient"]].id,
            procedure_code=c["code"],
            theatre_id=theatres[c["room"]].id,
            scheduled_on=day(c["day"]),
            seq=c["seq"],
            urgency=c["urgency"],
            overrun_minutes=c["overrun"],
            surgeon_id=surgeons[c["surgeon"]].id if c["surgeon"] else None,
            deferred=c["deferred"],
        )
        cardiac = p["cardiac"] or {}
        case.preop = PreopAssessment(
            asa=p["asa"],
            weight_kg=p["weight_kg"],
            height_cm=p["height_cm"],
            **{
                k: (bool(cardiac[k]) if k not in ("lvef", "nyha", "pa_systolic") else cardiac[k])
                for k in PREOP
                if k in cardiac
            },
        )
        db.add(case)
        counts["cases"] += 1
    db.flush()
    return counts


def _time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)
