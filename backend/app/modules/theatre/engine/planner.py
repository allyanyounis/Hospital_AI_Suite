"""The theatre planner (ported from the POC's server.py): the day lists, free slots, where a displaced case should go,
move tips, emergency placement by NCEPOD urgency, and every action on a case.

Everything here reads and changes a Snapshot, never the database. Times are minutes after midnight; days are dates.
Functions that change the snapshot say so; the caller decides whether to save it (service.py) or throw it away
(previews).
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import date, timedelta

from .forecast import DAY_CLOSE, DAY_OPEN, EMPTY, Z90, lognormal, simulate
from .risk import risk
from .snapshot import PHASES, Case, Person, Room, Snapshot

HORIZON = 14  # days searched for a free slot
DEST_SAFE = 25  # a moved elective should land on a day at most this likely (%) to pass 16:00
URGENCIES = ("immediate", "urgent", "expedited", "elective")  # NCEPOD classification
EMERGENCY = ("immediate", "urgent")
TARGET_MIN = {"immediate": 60, "urgent": 360}  # minutes to theatre
EXPEDITED_DAYS = 3
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def hm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# --- Lists, surgeons and free slots ------------------------------------------------------------------------------


def room_of(snap: Snapshot, specialty: str) -> Room | None:
    return next((r for r in snap.rooms if r.specialty == specialty), None)


def list_of(snap: Snapshot, room_id: int, day: date | None, without: int | None = None) -> list[Case]:
    """The cases on one room's list for `day`, in order."""
    return sorted(
        (c for c in snap.cases.values() if c.room_id == room_id and c.day == day and c.id != without),
        key=lambda c: (c.seq, c.id),
    )


def last_seq(snap: Snapshot, room_id: int, day: date) -> int:
    return max((c.seq for c in list_of(snap, room_id, day)), default=0)


def specialty_surgeons(snap: Snapshot, specialty: str) -> list[int]:
    return sorted(s.id for s in snap.surgeons.values() if s.specialty == specialty and s.active)


def surgeon_hours(snap: Snapshot, surgeon_id: int | None, day: date) -> tuple[int, int] | str:
    """The surgeon's operating hours on `day`, or the reason they cannot operate."""
    surgeon = snap.surgeons.get(surgeon_id) if surgeon_id is not None else None
    if surgeon is None or not surgeon.active:
        return "That surgeon is not active."
    weekday = day.weekday()
    hours = surgeon.days.get(weekday)
    if hours is None:
        return f"{surgeon.name} does not operate on {WEEKDAYS[weekday]}s."
    if any(leave.starts_on <= day <= leave.ends_on for leave in surgeon.leave):
        return f"{surgeon.name} is on leave."
    return hours


def next_start(snap: Snapshot, room_id: int, day: date, without: int | None = None) -> int:
    cases = list_of(snap, room_id, day, without)
    used = sum(snap.procs[c.code].minutes + c.overrun for c in cases)
    return DAY_OPEN + used + snap.room(room_id).cleaning * len(cases)


def fit(snap: Snapshot, code: str, day: date, surgeon_id: int | None = None, without: int | None = None) -> dict:
    """Place `code` at the end of its room's list on `day`: the slot, or the reason it does not fit."""
    proc = snap.procs[code]
    room = room_of(snap, proc.specialty)
    if room is None:
        return {"day": day, "room": None, "reason": f"No theatre does {proc.specialty} operations."}
    start = next_start(snap, room.id, day, without)
    end = start + proc.minutes
    ids = [surgeon_id] if surgeon_id else specialty_surgeons(snap, proc.specialty)
    reason = "No surgeon for this specialty."
    for sid in ids:
        hours = surgeon_hours(snap, sid, day)
        name = snap.surgeons[sid].name if sid in snap.surgeons else ""
        if isinstance(hours, str):
            reason = hours
        elif end > DAY_CLOSE:
            reason = f"List is full: it would end at {hm(end)}."
        elif start < hours[0] or end > hours[1]:
            reason = f"{name} operates {hm(hours[0])}–{hm(hours[1])}; this case would run {hm(start)}–{hm(end)}."
        else:
            return {"day": day, "room": room.id, "start": start, "end": end, "surgeon_id": sid, "surgeon": name}
    return {"day": day, "room": room.id, "reason": reason}


def weekdays_ahead(start: date, days: int = HORIZON, include_today: bool = True) -> Iterator[date]:
    for offset in range(0 if include_today else 1, days + 1):
        day = start + timedelta(days=offset)
        if day.weekday() < 5:
            yield day


def first_fit(snap: Snapshot, code: str, surgeon_id: int | None, after: date, without: int | None = None):
    for day in weekdays_ahead(after, include_today=False):
        if "reason" not in (slot := fit(snap, code, day, surgeon_id, without)):
            return slot
    return None


def duration_basis(source: str) -> str:
    """Name the table the planned minutes came from, so a suggestion can say so."""
    if source.startswith("German"):
        return "German 2019 specialised inpatient means (Zenodo 7147921)"
    if "Stanford" in source:
        return "Stanford 2024 CABG series: anaesthesia and skin-to-skin medians"
    if "NACOR" in source:
        return "NACOR AVR registry total case time"
    return "the published minutes for this operation"


def forecast_room(snap: Snapshot, room_id: int, day: date, extra: dict | None = None, skip: int | None = None):
    """Play one room, optionally with one more case at the end. Same draws as the board."""
    blank = {"state": "wait", "booked": DAY_OPEN, "start": DAY_OPEN, "end": DAY_OPEN}
    cases = [
        {"planned_min": snap.procs[c.code].minutes, "variance": snap.procs[c.code].variance, "overrun": c.overrun}
        | blank
        for c in list_of(snap, room_id, day, skip)
    ]
    if extra:
        cases.append({"planned_min": extra["planned_min"], "variance": extra["variance"], "overrun": 0} | blank)
    if not cases:
        return dict(EMPTY)
    return simulate(cases, snap.room(room_id).cleaning, DAY_OPEN)


def slot_options(snap: Snapshot, code: str, surgeon_id: int | None, after: date, without: int | None = None):
    """Every later weekday where the case fits a rostered surgeon, with that day's chance of passing 16:00."""
    proc = snap.procs[code]
    options = []
    for day in weekdays_ahead(after, include_today=False):
        slot = fit(snap, code, day, surgeon_id, without)
        if "reason" in slot and surgeon_id:
            slot = fit(snap, code, day, None, without)
        if "reason" in slot:
            continue
        hours = surgeon_hours(snap, slot["surgeon_id"], day)
        forecast = forecast_room(
            snap, slot["room"], day, {"planned_min": proc.minutes, "variance": proc.variance}, without
        )
        options.append(
            {
                "day": day,
                "room": slot["room"],
                "start": slot["start"],
                "end": slot["end"],
                "surgeon_id": slot["surgeon_id"],
                "surgeon": slot["surgeon"],
                "same_surgeon": slot["surgeon_id"] == surgeon_id,
                "hours": list(hours) if not isinstance(hours, str) else None,
                "minutes": proc.minutes,
                "source": duration_basis(proc.source or ""),
                "over_pct": forecast["over_pct"],
                "expected_over": forecast["expected_over"],
            }
        )
    return options


def pick_destination(options: list[dict]) -> tuple[dict, dict | None]:
    """Choose where a displaced case should go.

    Prefer the earliest day whose chance of passing 16:00 is at most DEST_SAFE; a colleague is used when the listed
    surgeon is not rostered, so a sooner safe list is not hidden. Otherwise the earliest day at or under 50%, else
    the lowest chance. `alt` is the soonest day that was not used.
    """

    def key(option: dict):
        pct, same = option["over_pct"], 0 if option.get("same_surgeon", True) else 1
        if pct <= DEST_SAFE:
            return (0, option["day"], same, pct)
        if pct <= 50:
            return (1, option["day"], same, pct)
        return (2, pct, option["day"], same)

    best = min(options, key=key)
    earlier = [option for option in options if option["day"] < best["day"]]
    return best, (min(earlier, key=lambda option: option["day"]) if earlier else None)


def destination(snap: Snapshot, code: str, surgeon_id: int | None, after: date, without: int | None = None):
    """The later slot a suggestion should name, or None when nothing in the next two weeks fits."""
    options = slot_options(snap, code, surgeon_id, after, without)
    if not options:
        return None
    best, alt = pick_destination(options)
    chosen = dict(best)
    quieter = [o for o in options if o["day"] > best["day"] and o["over_pct"] + 10 < best["over_pct"]]
    chosen["alt"] = None if alt is None else {k: alt[k] for k in ("day", "start", "over_pct", "expected_over")}
    chosen["later"] = (
        None if not quieter else {k: min(quieter, key=lambda o: o["over_pct"])[k] for k in ("day", "over_pct")}
    )
    chosen["threshold"] = DEST_SAFE
    return chosen


# --- The day list ------------------------------------------------------------------------------------------------


def case_row(snap: Snapshot, case: Case, person: Person, start: int, booked: int, day: date, now: int) -> dict:
    proc = snap.procs[case.code]
    cursor, phases = start, []
    for (key, label), minutes in zip(PHASES, proc.phases, strict=True):
        minutes += case.overrun if key == "incision" else 0
        phases.append({"key": key, "label": label, "start": cursor, "end": cursor + minutes})
        cursor += minutes
    mu, sigma = lognormal(proc.minutes, proc.variance)
    surgeon = snap.surgeons.get(case.surgeon_id) if case.surgeon_id else None
    hours = surgeon_hours(snap, case.surgeon_id, day) if case.surgeon_id else "No surgeon assigned."
    if isinstance(hours, str):
        rota = hours
    else:
        rota = None if cursor <= hours[1] else f"{surgeon.name} finishes at {hm(hours[1])}."
    score = risk(person, case, proc, cursor - start, case.urgency)
    return {
        "id": case.id,
        "seq": case.seq,
        "patient_id": case.patient_id,
        "name": person.name,
        "age": person.age,
        "sex": person.sex,
        "asa": case.asa,
        "allergies": person.allergies,
        "procedure": proc.title,
        "code": case.code,
        "urgency": case.urgency,
        "deferred": case.deferred,
        "surgeon_id": case.surgeon_id,
        "surgeon": surgeon.name if surgeon else None,
        "rota": rota,
        "booked": booked,
        "start": start,
        "end": cursor,
        "planned_min": proc.minutes,
        "variance": proc.variance,
        "latest": round(start + case.overrun + math.exp(mu + Z90 * sigma)),
        "overrun": case.overrun,
        "phases": phases,
        "state": "done" if cursor <= now else "in" if start <= now else "wait",
        "phase": next((p["label"] for p in phases if p["start"] <= now < p["end"]), None),
        "late_pct": 0,
        "risk": score["pct"],
        "risk_model": score["model"],
        "risk_high": score["pct"] >= 1.5 * score["average"],
    }


def room_view(snap: Snapshot, room: Room, day: date, now: int, level: int = 2) -> dict:
    """One room's list on `day`. Level 0: the timeline; 1: plus the forecast; 2: plus the move tip and nudge."""
    cursor = booked = DAY_OPEN
    cases = []
    for case in list_of(snap, room.id, day):
        row = case_row(snap, case, snap.patients[case.patient_id], cursor, booked, day, now)
        cases.append(row)
        cursor = row["end"] + room.cleaning
        booked += row["planned_min"] + room.cleaning
    item = {
        "id": room.id,
        "code": room.code,
        "name": room.name,
        "specialty": room.specialty,
        "cleaning": room.cleaning,
        "cases": cases,
        "finish": cases[-1]["end"] if cases else DAY_OPEN,
    }
    item["overtime"] = max(0, item["finish"] - DAY_CLOSE)
    if level >= 1:
        item["forecast"] = simulate(cases, room.cleaning, now) if cases else dict(EMPTY)
    if level >= 2:
        item["suggestion"] = suggestion(snap, item, now, day) if cases else None
        item["nudge"] = None if item["suggestion"] or not cases else suggestion(snap, item, now, day, 15, 5)
    return item


def suggestion(snap: Snapshot, room: dict, now: int, day: date, min_over: int = 50, min_drop: int = 20):
    """The single waiting elective whose move most reduces overtime, and where it should go.

    The default bar is the one for an automatic tip: the room is more likely than not to pass 16:00, and the move
    cuts that chance by 20 points. A lower bar is used only to show a weaker suggestion (a "nudge").
    """
    if room["forecast"]["over_pct"] < min_over and room["forecast"]["expected_over"] < 5:
        return None
    best = None
    for case in room["cases"]:
        if case["state"] != "wait" or case["urgency"] != "elective":
            continue
        rest = [dict(c) for c in room["cases"] if c["id"] != case["id"]]
        after = simulate(rest, room["cleaning"], now)
        if best is None or (after["expected_over"], -case["booked"]) < (
            best["after"]["expected_over"],
            -best["booked"],
        ):
            best = {
                "case": case["id"],
                "name": case["name"],
                "procedure": case["procedure"],
                "booked": case["booked"],
                "code": case["code"],
                "surgeon_id": case["surgeon_id"],
                "after": after,
            }
    if best is None:
        return None
    drop = room["forecast"]["over_pct"] - best["after"]["over_pct"]
    overtime_drop = room["forecast"]["expected_over"] - best["after"]["expected_over"]
    if drop < min_drop and overtime_drop < 5:
        return None
    slot = destination(snap, best.pop("code"), best.pop("surgeon_id"), day, best["case"])
    if slot is None:
        return None
    best.update(
        date=slot["day"],
        slot_start=slot["start"],
        slot_end=slot["end"],
        room=slot["room"],
        surgeon_id=slot["surgeon_id"],
        surgeon=slot["surgeon"],
        same_surgeon=slot["same_surgeon"],
        hours=slot["hours"],
        minutes=slot["minutes"],
        source=slot["source"],
        threshold=slot["threshold"],
        dest={"over_pct": slot["over_pct"], "expected_over": slot["expected_over"]},
        alt=slot["alt"],
        later=slot["later"],
    )
    return best


MOVE_KEYS = (
    "case",
    "name",
    "procedure",
    "date",
    "slot_start",
    "slot_end",
    "room",
    "surgeon_id",
    "surgeon",
    "same_surgeon",
    "hours",
    "minutes",
    "source",
    "threshold",
    "dest",
    "alt",
    "later",
)


def move_view(s: dict) -> dict:
    """The part of a suggestion the page needs to say where the patient should go."""
    return {key: s[key] for key in MOVE_KEYS} | {"over_pct": s["after"]["over_pct"]}


def board_now(snap: Snapshot, day: date, now: int) -> int:
    """The clock a list is played at: real time today, before the start for a future day, after the end for a past."""
    if day == snap.today:
        return now
    return DAY_OPEN - 1 if day > snap.today else DAY_CLOSE + 600


def board(snap: Snapshot, now: int, day: date | None = None, with_proposals: bool = False) -> dict:
    today = snap.today
    day = day or today
    now = board_now(snap, day, now)
    payload = {
        "today": today,
        "day": day,
        "now": now,
        "open": DAY_OPEN,
        "close": DAY_CLOSE,
        "rooms": [room_view(snap, room, day, now) for room in snap.rooms],
    }
    if with_proposals and day == today:
        payload["proposals"] = waiting_proposals(snap, now)
    return payload


def waiting_proposals(snap: Snapshot, now: int) -> list[dict]:
    """Where each waiting Immediate or Urgent case would go (worked out on a copy; nothing changes)."""
    today = snap.today
    rows = [c for c in snap.cases.values() if c.day is None and c.urgency in EMERGENCY]
    rows.sort(key=lambda c: (c.urgency == "urgent", snap.patients[c.patient_id].name))
    out = []
    for case in rows:
        before_room = room_view(snap, snap.room(case.room_id), today, now, level=1)
        before = {c["id"]: c["start"] for c in before_room["cases"]}
        trial = snap.copy()
        slot = place(trial, case.id, now)
        if "reason" in slot:
            continue
        after = room_view(trial, trial.room(slot["room"]), today, now)
        pushed = [
            {"case": c["id"], "name": c["name"], "from": before[c["id"]], "to": c["start"], "urgency": c["urgency"]}
            for c in after["cases"]
            if c["id"] in before and c["start"] > before[c["id"]]
        ]
        person, proc = snap.patients[case.patient_id], snap.procs[case.code]
        out.append(
            {
                "case": case.id,
                "name": person.name,
                "age": person.age,
                "asa": case.asa,
                "urgency": case.urgency,
                "procedure": proc.title,
                "planned_min": proc.minutes,
                "slot": {k: slot[k] for k in ("day", "room", "start", "wait", "met") if k in slot},
                "pushed": pushed[:3],
                "move": None if not after["suggestion"] else move_view(after["suggestion"]),
                "before_over": before_room["forecast"]["over_pct"],
                "after_over": after["forecast"]["over_pct"],
            }
        )
    return out


def outlook(snap: Snapshot, room_id: int, now: int, day: date) -> dict:
    room = room_view(snap, snap.room(room_id), day, board_now(snap, day, now))
    return {**room["forecast"], "finish": room["finish"], "cases": len(room["cases"]), "suggestion": room["suggestion"]}


# --- Changes (each changes the snapshot) -------------------------------------------------------------------------


def on_call(snap: Snapshot, specialty: str, day: date, preferred: int | None) -> int | None:
    """The surgeon for an emergency: the listed one if rostered, else a rostered colleague, else the listed one."""
    ids = specialty_surgeons(snap, specialty)
    rostered = [sid for sid in ids if not isinstance(surgeon_hours(snap, sid, day), str)]
    return preferred if preferred in rostered else (rostered or [preferred or (ids[0] if ids else None)])[0]


def place(snap: Snapshot, case_id: int, now: int) -> dict:
    """Put a waiting case on a list by its urgency (NCEPOD): an emergency today within its target, else the first
    list it fits. Returns the slot, or {"reason": ...}."""
    case = snap.cases[case_id]
    proc = snap.procs[case.code]
    today = snap.today
    if case.urgency in EMERGENCY:
        room = room_view(snap, snap.room(case.room_id), today, now, level=0)
        cases = room["cases"]
        waiting = [c for c in cases if c["state"] == "wait" and c["id"] != case_id]
        end = cases[-1]["end"] + room["cleaning"] if cases else DAY_OPEN
        options = [(c["seq"], max(c["start"], now)) for c in waiting]
        options.append(((cases[-1]["seq"] + 1) if cases else 1, max(end, now)))
        target = TARGET_MIN[case.urgency]
        in_time = [o for o in options if o[1] - now <= target]
        seq, start = in_time[-1] if case.urgency == "urgent" and in_time else options[0]
        for other in snap.cases.values():
            if other.room_id == case.room_id and other.day == today and other.seq >= seq:
                other.seq += 1
        case.day, case.seq, case.deferred = today, seq, False
        case.surgeon_id = on_call(snap, proc.specialty, today, case.surgeon_id)
        return {
            "day": today,
            "room": case.room_id,
            "start": start,
            "wait": start - now,
            "target": target,
            "met": start - now <= target,
        }
    slot = fit(snap, case.code, today, case.surgeon_id, case_id)
    if "reason" in slot:
        slot = first_fit(snap, case.code, case.surgeon_id, today, case_id)
    if slot is None:
        return {"reason": "No free slot in the next two weeks."}
    case.day, case.seq = slot["day"], last_seq(snap, slot["room"], slot["day"]) + 1
    case.deferred, case.surgeon_id = False, slot["surgeon_id"]
    target = EXPEDITED_DAYS if case.urgency == "expedited" else None
    days = (slot["day"] - today).days
    return {
        "day": slot["day"],
        "room": slot["room"],
        "start": slot["start"],
        "target_days": target,
        "met": target is None or days <= target,
    }


def defer(snap: Snapshot, case_id: int, day: date | None, surgeon_id: int | None = None) -> str | None:
    """Move a case to a later day (with its surgeon if rostered, else a colleague). Returns an error or None."""
    case = snap.cases[case_id]
    if not day or day <= snap.today:
        return "Pick a date after today."
    slot = fit(snap, case.code, day, surgeon_id or case.surgeon_id, case_id)
    if "reason" in slot:
        slot = fit(snap, case.code, day, None, case_id)
    if "reason" in slot:
        return slot["reason"]
    case.day, case.seq = day, last_seq(snap, case.room_id, day) + 1
    case.deferred, case.surgeon_id = True, slot["surgeon_id"]
    return None


def create_case(snap: Snapshot, req: dict) -> tuple[str | None, int | None]:
    """Add a case (and a new patient if `patient` is given instead of `patient_id`). Returns (error, case id)."""
    code, day, urgency = req.get("procedure_code"), req.get("day"), req.get("urgency") or "elective"
    proc = snap.procs.get(code or "")
    room = room_of(snap, proc.specialty) if proc else None
    if proc is None or room is None:
        return "Choose an operation.", None
    if urgency not in URGENCIES:
        return "Unknown urgency.", None
    surgeon_id = req.get("surgeon_id")
    if surgeon_id and (surgeon_id not in snap.surgeons or snap.surgeons[surgeon_id].specialty != proc.specialty):
        return "That surgeon is in another specialty.", None
    if day:
        if day < snap.today:
            return "Pick today or a later day.", None
        slot = fit(snap, code, day, surgeon_id)
        if "reason" in slot:
            return slot["reason"], None
        surgeon_id = slot["surgeon_id"]
    patient_id = req.get("patient_id")
    if patient_id:
        if patient_id not in snap.patients:
            return "No such patient.", None
    else:
        p = req.get("patient") or {}
        if not (p.get("name") or "").strip() or p.get("age") is None:
            return "Enter the patient's name and age.", None
        patient_id = snap.temp_id()
        sex = p.get("sex") or ""
        allergies = (p.get("allergies") or "").strip()
        snap.patients[patient_id] = Person(
            patient_id,
            p["name"].strip(),
            sex[:1].upper() if sex in ("Female", "Male") else "",
            int(p["age"]),
            allergies or "None known",
        )
        snap.new_patients[patient_id] = {
            "full_name": p["name"].strip(),
            "sex": sex,
            "age": int(p["age"]),
            "allergies": allergies,
        }
    snap.new_history.append((patient_id, "indication", snap.today, f"Listed for {proc.title.lower()}."))
    case_id = snap.temp_id()
    snap.cases[case_id] = Case(
        id=case_id,
        patient_id=patient_id,
        code=proc.code,
        room_id=room.id,
        day=day or None,
        seq=last_seq(snap, room.id, day) + 1 if day else 0,
        urgency=urgency,
        surgeon_id=surgeon_id,
        asa=int(req.get("asa") or 2),
        weight_kg=req.get("weight_kg"),
        height_cm=req.get("height_cm"),
        cardiac=req.get("cardiac"),
    )
    return None, case_id


def intake(snap: Snapshot, req: dict, now: int, confirm: bool = False) -> dict:
    """Place a case by urgency: a waiting one (`case_id`) or a new one. A preview reports the slot, the room's
    forecast before / with the case / with up to three suggested moves; confirm applies only the moves the user
    picked. Changes the snapshot either way: previews must be run on a copy."""
    if req.get("case_id"):
        case = snap.cases.get(req["case_id"])
        if case is None or case.day:
            return {"error": "Pick a case from the waiting list."}
        if req.get("urgency"):
            case.urgency = req["urgency"]
        case_id = case.id
    else:
        error, case_id = create_case(snap, {**req, "day": None})
        if error:
            return {"error": error}
    case = snap.cases[case_id]
    today = snap.today
    before = outlook(snap, case.room_id, now, today)
    slot = place(snap, case_id, now)
    if "reason" in slot:
        return {"error": slot["reason"]}
    if confirm:
        for move in req.get("moves") or []:
            if move["case"] not in snap.cases:
                return {"error": "A case to move is no longer on the list."}
            if error := defer(snap, move["case"], move["date"], move.get("surgeon_id")):
                return {"error": error}
        return {"case": case_id, "slot": slot}
    after = state = outlook(snap, case.room_id, now, slot["day"])
    moves = []
    while state["suggestion"] and len(moves) < 3:
        s = state["suggestion"]
        moves.append(move_view(s))
        defer(snap, s["case"], s["date"], s.get("surgeon_id"))
        state = outlook(snap, case.room_id, now, slot["day"])

    def pick(o: dict) -> dict:
        return {k: o[k] for k in ("over_pct", "expected_over", "finish")}

    return {
        "case": case_id,
        "name": snap.patients[case.patient_id].name,
        "procedure": snap.procs[case.code].title,
        "urgency": case.urgency,
        "slot": slot,
        "before": pick(before) if slot["day"] == today else None,
        "after": pick(after),
        "with_moves": pick(state),
        "moves": moves,
    }


def act(snap: Snapshot, case_id: int, op: str, now: int, **kw) -> str | None:
    """One action on a case (changes the snapshot). Returns an error message, or None when done."""
    today = snap.today
    case = snap.cases[case_id]
    placed = {}
    if case.day == today:
        placed = {c["id"]: c for c in room_view(snap, snap.room(case.room_id), today, now, level=0)["cases"]}
    started = case_id in placed and placed[case_id]["start"] <= now
    if op == "overrun":
        if case_id not in placed or placed[case_id]["state"] != "in":
            return "Only the case in theatre can run long."
        case.overrun += int(kw.get("minutes") or 15)
    elif started:
        return "This case has started. It stays where it is."
    elif op in ("earlier", "later"):
        if case.day is None:
            return "This case is not on a list."
        others = [c for c in list_of(snap, case.room_id, case.day) if c.id != case_id]
        if op == "earlier":
            other = max((c for c in others if c.seq < case.seq), key=lambda c: c.seq, default=None)
        else:
            other = min((c for c in others if c.seq > case.seq), key=lambda c: c.seq, default=None)
        if other is None or (other.id in placed and placed[other.id]["start"] <= now):
            return "Nothing to swap with."
        case.seq, other.seq = other.seq, case.seq
    elif op == "defer":
        return defer(snap, case_id, kw.get("day"), kw.get("surgeon_id"))
    elif op == "book":
        if case.day:
            return "This case is already on a list."
        slot = place(snap, case_id, now)
        if "reason" in slot:
            return slot["reason"]
    elif op == "schedule":
        day = kw.get("day")
        if case.day:
            return "This case is already on a list."
        if not day or day < today:
            return "Pick today or a later day."
        slot = fit(snap, case.code, day, kw.get("surgeon_id"), case_id)
        if "reason" in slot:
            return slot["reason"]
        case.day, case.seq = day, last_seq(snap, slot["room"], day) + 1
        case.surgeon_id, case.deferred = slot["surgeon_id"], False
    elif op == "unschedule":
        case.day, case.seq, case.deferred = None, 0, False
    elif op == "cancel":
        del snap.cases[case_id]
        snap.canceled.add(case_id)
    elif op == "surgeon":
        surgeon = snap.surgeons.get(kw.get("surgeon_id"))
        if surgeon is None or surgeon.specialty != snap.procs[case.code].specialty:
            return "Pick a surgeon from the same specialty."
        if case.day and isinstance(hours := surgeon_hours(snap, surgeon.id, case.day), str):
            return hours
        case.surgeon_id = surgeon.id
    elif op == "urgency":
        if kw.get("urgency") not in URGENCIES:
            return "Unknown urgency."
        case.urgency = kw["urgency"]
    else:
        return "Unknown action."
    return None


# --- Booking calendar, rosters and leave -------------------------------------------------------------------------


def calendar(snap: Snapshot, start: date, code: str | None = None, surgeon_id: int | None = None, days: int = 7):
    """The weekdays from `start` × every theatre: how full, free minutes, who operates, and (for an operation)
    where it would fit or why not."""
    proc = snap.procs.get(code) if code else None
    out = []
    for day in (start + timedelta(days=i) for i in range(days)):
        if day.weekday() >= 5:
            continue
        cells = []
        for room in snap.rooms:
            count = len(list_of(snap, room.id, day))
            begin = next_start(snap, room.id, day)
            staff = []
            for sid in specialty_surgeons(snap, room.specialty):
                hours = surgeon_hours(snap, sid, day)
                if not isinstance(hours, str):
                    staff.append(f"{snap.surgeons[sid].name} {hm(hours[0])}–{hm(hours[1])}")
            cell = {
                "room": room.id,
                "code": room.code,
                "cases": count,
                "free": max(0, DAY_CLOSE - begin) if staff else 0,
                "used_pct": min(100, round(100 * (begin - DAY_OPEN) / (DAY_CLOSE - DAY_OPEN))) if count else 0,
                "staff": staff,
            }
            if proc and proc.specialty == room.specialty:
                if day < snap.today:
                    cell["fit"] = {"day": day, "room": room.id, "reason": "That day has passed."}
                else:
                    cell["fit"] = fit(snap, proc.code, day, surgeon_id)
            cells.append(cell)
        out.append({"day": day, "past": day < snap.today, "rooms": cells})
    return {"today": snap.today, "start": start, "days": out}


def surgeons_view(snap: Snapshot) -> list[dict]:
    today = snap.today
    out = []
    for s in sorted(snap.surgeons.values(), key=lambda s: (s.specialty, s.name)):
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "specialty": s.specialty,
                "active": s.active,
                "days": [{"weekday": wd, "start": h[0], "end": h[1]} for wd, h in sorted(s.days.items())],
                "leave": [
                    {"id": leave.id, "starts_on": leave.starts_on, "ends_on": leave.ends_on, "reason": leave.reason}
                    for leave in sorted(s.leave, key=lambda leave: leave.starts_on)
                    if leave.ends_on >= today
                ],
                "booked": sum(1 for c in snap.cases.values() if c.surgeon_id == s.id and c.day and c.day >= today),
            }
        )
    return out


def leave_conflicts(snap: Snapshot, surgeon_id: int, starts_on: date, ends_on: date) -> list[dict]:
    """Cases the surgeon can no longer do (leave already in the snapshot), each with a colleague who can take it
    that day if there is one, and the first later slot."""
    surgeon = snap.surgeons[surgeon_id]
    rows = sorted(
        (c for c in snap.cases.values() if c.surgeon_id == surgeon_id and c.day and starts_on <= c.day <= ends_on),
        key=lambda c: (c.day, c.seq),
    )
    out = []
    for case in rows:
        cover = None
        for other in specialty_surgeons(snap, surgeon.specialty):
            if other != surgeon_id and not isinstance(surgeon_hours(snap, other, case.day), str):
                cover = {"id": other, "name": snap.surgeons[other].name}
                break
        later = destination(snap, case.code, surgeon_id, ends_on, case.id)
        out.append(
            {
                "case": case.id,
                "day": case.day,
                "name": snap.patients[case.patient_id].name,
                "procedure": snap.procs[case.code].title,
                "cover": cover,
                "later": later and {"day": later["day"], "start": later["start"], "surgeon_id": later["surgeon_id"]},
            }
        )
    return out


def case_detail(snap: Snapshot, case_id: int, now: int) -> dict:
    """One case with its timing on its list (if listed), phases and risk with the factors behind it."""
    case = snap.cases[case_id]
    proc, person = snap.procs[case.code], snap.patients[case.patient_id]
    row = None
    if case.day:
        room = room_view(snap, snap.room(case.room_id), case.day, board_now(snap, case.day, now), level=0)
        row = next(c for c in room["cases"] if c["id"] == case_id)
    surgeon = snap.surgeons.get(case.surgeon_id) if case.surgeon_id else None
    return {
        "id": case.id,
        "patient": {
            "id": person.id,
            "name": person.name,
            "age": person.age,
            "sex": person.sex,
            "allergies": person.allergies,
            "labs": person.labs,
        },
        "procedure": {
            "code": proc.code,
            "title": proc.title,
            "specialty": proc.specialty,
            "minutes": proc.minutes,
            "source": duration_basis(proc.source or ""),
            "risk_model": proc.risk_model,
        },
        "phases": [
            {"key": key, "label": label, "minutes": m} for (key, label), m in zip(PHASES, proc.phases, strict=True)
        ],
        "room": {"id": case.room_id, "code": snap.room(case.room_id).code},
        "day": case.day,
        "seq": case.seq,
        "urgency": case.urgency,
        "deferred": case.deferred,
        "overrun": case.overrun,
        "surgeon_id": case.surgeon_id,
        "surgeon": surgeon.name if surgeon else None,
        "preop": {"asa": case.asa, "weight_kg": case.weight_kg, "height_cm": case.height_cm, "cardiac": case.cardiac},
        "timing": row,
        "risk": risk(person, case, proc, proc.minutes + case.overrun, case.urgency),
        "today": snap.today,
    }
