"""Shared operating day for every scheduling policy.

Rooms and specialties are the v1 four-theatre set, plus a second general
theatre. schedule.recover_overrun can already move a case into another room
of the same specialty; the live list has only one room per specialty, so
that move had nowhere to go. OR 1B is the destination.

Durations come from durations.py. The risk model is not read.
"""

from __future__ import annotations

from random import Random

from .catalog import DAY_CLOSE, DAY_OPEN
from .durations import LABEL, draw_minutes, planned_minutes

LATEST = 19 * 60
EVENT_MIN = 10 * 60 + 30
RECOVERY_MIN = 40
RECOVERY_BEDS = 4
OVERRUN_EXTRA = 60

ROOMS = (
    {"id": "OR 1", "specialty": "General"},
    {"id": "OR 1B", "specialty": "General"},
    {"id": "OR 2", "specialty": "Trauma"},
    {"id": "OR 3", "specialty": "Gyn & Obstetrics"},
    {"id": "OR 4", "specialty": "Otolaryngology"},
)

SURGEONS = (
    {"id": "SG1", "specialty": "General", "rooms": ("OR 1", "OR 1B"), "start": DAY_OPEN, "end": LATEST},
    {"id": "SG2", "specialty": "General", "rooms": ("OR 1", "OR 1B"), "start": DAY_OPEN, "end": LATEST},
    {"id": "ST1", "specialty": "Trauma", "rooms": ("OR 2",), "start": DAY_OPEN, "end": LATEST},
    {"id": "SY1", "specialty": "Gyn & Obstetrics", "rooms": ("OR 3",), "start": DAY_OPEN, "end": LATEST},
    {"id": "SO1", "specialty": "Otolaryngology", "rooms": ("OR 4",), "start": DAY_OPEN, "end": LATEST},
)

HOME_SURGEON = {"OR 1": "SG1", "OR 1B": "SG2", "OR 2": "ST1", "OR 3": "SY1", "OR 4": "SO1"}

DISRUPTIONS = ("overrun", "emergency", "room_outage", "pacu")

# Experiment settings, not a claim about a hospital's priorities.
# Hard constraints are not in this list. Waiting for electives is left at 0
# because a minute of clock time from 08:00 would otherwise look worse than
# cancelling an afternoon case. Urgent waiting is penalised.
WEIGHTS = {
    "overtime_per_min": 8,
    "idle_per_min": 1,
    "wait_elective_per_min": 0,
    "wait_expedited_per_min": 1,
    "wait_urgent_per_min": 4,
    "wait_immediate_per_min": 8,
    "cancel_elective": 400,
    "cancel_expedited": 700,
    "change": 15,
    "urgent_late_per_min": 6,
    "immediate_late_per_min": 10,
}

WAIT_WEIGHT = {
    "Elective": WEIGHTS["wait_elective_per_min"],
    "Expedited": WEIGHTS["wait_expedited_per_min"],
    "Urgent": WEIGHTS["wait_urgent_per_min"],
    "Immediate": WEIGHTS["wait_immediate_per_min"],
}
CANCEL_WEIGHT = {"Elective": WEIGHTS["cancel_elective"], "Expedited": WEIGHTS["cancel_expedited"]}

# Three objective settings for the sensitivity run. Hard constraints do not change.
PROFILES = ("balanced", "protect_electives", "avoid_overtime")
PROFILE_NOTE = {
    "balanced": "The default experiment weights.",
    "protect_electives": "Deferring an elective costs more. A minute of overtime costs less.",
    "avoid_overtime": "A minute of overtime costs more. Deferring an elective costs less.",
}

HARD_RULES = (
    "One case in a room at a time.",
    "Turnover after a case is the German cleaning mean for that case's specialty.",
    "A case stays in a room of its own specialty.",
    "A surgeon is in one room at a time, and only in a room they cover.",
    "A case that has not started stays inside that surgeon's hours, 08:00 to 19:00.",
    "A case that has not started is not placed in a closed room or before the current time.",
    "A case that has started keeps its room and its start. It is not interrupted.",
    "Urgent and Immediate cases stay on today's list.",
    "An emergency cannot start before it arrives, and it waits for a free future slot.",
    "Recovery is one bed for a fixed 40 minutes after the case ends. A case the planner can still move must fit the beds that are free.",
)
SOFT_TERMS = (
    "Overtime after 16:00, counted per minute and summed across rooms.",
    "Idle minutes inside 08:00 to 16:00 that are neither a case nor the turnover after it.",
    "Waiting of Expedited, Urgent and Immediate cases, measured from ready time. Elective waiting has weight 0.",
    "Deferring an Elective or Expedited case off today. This is a deferral, not a permanent cancellation.",
    "Moving a case off the room it had in the previous plan.",
    "An Urgent case starting after 14:00, and an Immediate case starting more than 60 minutes after arrival.",
)
NOT_MODELLED = (
    "Anaesthesia staff and nursing staff as separate people. The surgeon roster stands in for staffing.",
    "Equipment, implants and procedure kits.",
    "Ward beds, and a full post-anaesthesia unit. The 40-minute bed is a proxy.",
    "A readiness time other than 08:00 for a booked case, or the arrival minute for an emergency.",
    "Patient preference, or a waiting-list rank beyond the four urgency words.",
)
DURATION_NOTE = (
    "Planned minutes are the sum of five published German phase means. "
    "A realized length draws each phase on its own and adds the draws. "
    "Adding the phase variances would be justified only if the phases were independent. "
    "The source publishes each phase on its own and does not say whether they move together, so that independence is an assumption. "
    "The VitalDB check compares a 90th percentile with anaesthesia duration, not with room entry to room exit. "
    "No file on disk has both of those timestamps, so there is no direct occupancy benchmark."
)


def wait_map(weights: dict) -> dict:
    return {
        "Elective": weights["wait_elective_per_min"],
        "Expedited": weights["wait_expedited_per_min"],
        "Urgent": weights["wait_urgent_per_min"],
        "Immediate": weights["wait_immediate_per_min"],
    }


def cancel_map(weights: dict) -> dict:
    return {"Elective": weights["cancel_elective"], "Expedited": weights["cancel_expedited"]}


def profile_weights(name: str) -> dict:
    weights = dict(WEIGHTS)
    if name == "balanced":
        return weights
    if name == "protect_electives":
        weights["cancel_elective"] = 1200
        weights["cancel_expedited"] = 1600
        weights["overtime_per_min"] = 4
        return weights
    if name == "avoid_overtime":
        weights["cancel_elective"] = 150
        weights["cancel_expedited"] = 280
        weights["overtime_per_min"] = 20
        return weights
    raise ValueError(name)


def compatible_rooms(specialty: str) -> list[str]:
    return [room["id"] for room in ROOMS if room["specialty"] == specialty]


def surgeons_for(room_id: str) -> list[dict]:
    return [surgeon for surgeon in SURGEONS if room_id in surgeon["rooms"]]


def world_minutes(scenario: dict, case: dict) -> int:
    """Realized occupancy, including an overrun once it is part of the case.

    A stress day replaces the draw with a fixed share of the planned length,
    so every case runs longer than its plan. The ordinary day uses the draw.
    """
    extra = 0
    for disruption in scenario.get("events") or [scenario["disruption"]]:
        if disruption.get("type") == "overrun" and disruption.get("case_id") == case["id"]:
            extra += int(disruption.get("extra_min") or 0)
    if scenario.get("duration_stress"):
        base = int(round(case["planned_min"] * float(scenario.get("duration_scale") or 1)))
    else:
        base = int(round(case["realized_min"] * float(scenario.get("duration_scale") or 1)))
    return base + extra


def _urgency(rng: Random) -> str:
    roll = rng.random()
    if roll < 0.08:
        return "Urgent"
    if roll < 0.20:
        return "Expedited"
    return "Elective"


def _take(pool: list[dict], cleaning_min: int, rng: Random) -> list[dict]:
    """Book 4 to 6 cases, a little past an 8-hour day, so policies have a choice."""
    chosen = []
    used = 0
    target = (DAY_CLOSE - DAY_OPEN) + 45
    while len(chosen) < 6:
        procedure = rng.choices(pool, weights=[item["weight"] for item in pool], k=1)[0]
        gap = cleaning_min if chosen else 0
        if len(chosen) >= 4 and used + gap + planned_minutes(procedure) > target:
            break
        chosen.append(procedure)
        used += gap + planned_minutes(procedure)
    return chosen


def _case(number: int, procedure: dict, room_id: str, rng: Random) -> dict:
    specialty = next(room["specialty"] for room in ROOMS if room["id"] == room_id)
    planned = planned_minutes(procedure)
    return {
        "id": f"C{number:02d}",
        "specialty": specialty,
        "home_room": room_id,
        "surgeon_id": HOME_SURGEON[room_id],
        "urgency": _urgency(rng),
        "ops": procedure["ops"],
        "title": procedure["title"] or procedure["ops"],
        "planned_min": planned,
        "realized_min": draw_minutes(procedure, rng),
        "compatible_rooms": compatible_rooms(specialty),
        "recovery_min": RECOVERY_MIN,
        "arrives": None,
        "ready_min": DAY_OPEN,
        "duration_source": LABEL["source"],
        "duration_target": LABEL["target"],
    }


def _emergency(pool: list[dict], rng: Random, ready: int) -> dict:
    procedure = rng.choices(pool, weights=[item["weight"] for item in pool], k=1)[0]
    planned = planned_minutes(procedure)
    return {
        "id": "E1",
        "specialty": "General",
        "home_room": "OR 1",
        "surgeon_id": "SG1",
        "urgency": "Immediate",
        "ops": procedure["ops"],
        "title": procedure["title"] or procedure["ops"],
        "planned_min": planned,
        "realized_min": draw_minutes(procedure, rng),
        "compatible_rooms": compatible_rooms("General"),
        "recovery_min": RECOVERY_MIN,
        "arrives": "emergency",
        "ready_min": ready,
        "duration_source": LABEL["source"],
        "duration_target": LABEL["target"],
    }


def build_scenario(
    seed: int,
    pools: dict,
    cleaning: dict,
    disruption: str | None = None,
    *,
    at: int | None = None,
    weights: dict | None = None,
    profile: str | None = None,
    duration_scale: float = 1.0,
    duration_stress: bool = False,
    second: str | None = None,
) -> dict:
    """One day. The same seed and the same options always rebuild the same day."""
    rng = Random(seed)
    kind = disruption or DISRUPTIONS[seed % len(DISRUPTIONS)]
    if kind not in DISRUPTIONS:
        raise ValueError(kind)
    if second not in (None, "emergency"):
        raise ValueError(second)
    if second and kind == "emergency":
        raise ValueError("the second event is already an emergency")
    cases = []
    number = 1
    for room in ROOMS:
        for procedure in _take(pools[room["specialty"]], cleaning[room["specialty"]], rng):
            cases.append(_case(number, procedure, room["id"], rng))
            number += 1
    event_at = EVENT_MIN if at is None else int(at)
    event = {"type": kind, "at": event_at}
    if kind == "overrun":
        first = next(case for case in cases if case["home_room"] == "OR 1")
        event.update(case_id=first["id"], extra_min=OVERRUN_EXTRA)
    elif kind == "room_outage":
        event.update(room_id="OR 1")
    elif kind == "pacu":
        event.update(beds=2)
    events = [event]
    if kind == "emergency":
        cases.append(_emergency(pools["General"], rng, event_at))
    if second == "emergency":
        second_at = event_at + 90
        events.append({"type": "emergency", "at": second_at})
        cases.append(_emergency(pools["General"], rng, second_at))
    chosen = profile_weights(profile) if profile else dict(weights or WEIGHTS)
    return {
        "seed": seed,
        "rooms": [dict(room) for room in ROOMS],
        "surgeons": [dict(surgeon, rooms=list(surgeon["rooms"])) for surgeon in SURGEONS],
        "cleaning": dict(cleaning),
        "cases": cases,
        "recovery_min": RECOVERY_MIN,
        "recovery_beds": RECOVERY_BEDS,
        "disruption": event,
        "events": events,
        "weights": chosen,
        "profile": profile or "balanced",
        "duration_scale": float(duration_scale),
        "duration_stress": bool(duration_stress),
        "provenance": dict(LABEL),
        "open_min": DAY_OPEN,
        "close_min": DAY_CLOSE,
        "latest_min": LATEST,
    }


def initial_cases(scenario: dict) -> list[dict]:
    """Cases known when the day starts. An emergency is not among them."""
    return [case for case in scenario["cases"] if not case.get("arrives")]


def case_map(scenario: dict) -> dict[str, dict]:
    return {case["id"]: case for case in scenario["cases"]}
