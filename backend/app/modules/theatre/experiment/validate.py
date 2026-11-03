"""Independent check of a schedule.

Does not import a planner. The v1 assert_feasible in the POC schedule.py
checks overlap, turnover, and a missing case for the old demo. This module
is the one the experiment uses. It also checks room compatibility, surgeon
hours, double-booked surgeons, recovery beds, closed rooms, and locked cases.
"""

from __future__ import annotations

from .contract import case_map


def _scheduled(schedule: dict) -> list[dict]:
    return [row for row in schedule["assignments"] if row["status"] == "scheduled"]


def violations(
    scenario: dict,
    schedule: dict,
    *,
    now: int | None = None,
    closed_rooms: set | None = None,
    recovery_beds: int | None = None,
    locked_ids: set | None = None,
) -> list[str]:
    """Return one short string per broken hard constraint. An empty list is feasible."""
    closed_rooms = closed_rooms or set()
    locked_ids = locked_ids or set()
    beds = scenario["recovery_beds"] if recovery_beds is None else recovery_beds
    by_case = case_map(scenario)
    rows = {row["case_id"]: row for row in schedule["assignments"]}
    problems = []
    locked_ids = set(locked_ids or ())
    locked_ids.update(schedule.get("locks") or {})

    for case in scenario["cases"]:
        if case.get("arrives") and case["id"] not in rows:
            if now is not None and now >= case.get("ready_min", now):
                problems.append(f"{case['id']} arrived and is missing from the schedule")
            continue
        if case["id"] not in rows:
            problems.append(f"{case['id']} is missing from the schedule")

    seen = [row["case_id"] for row in schedule["assignments"]]
    if len(seen) != len(set(seen)):
        problems.append("a case appears more than once")

    surgeons = {surgeon["id"]: surgeon for surgeon in scenario["surgeons"]}
    for row in _scheduled(schedule):
        case = by_case.get(row["case_id"])
        if case is None:
            problems.append(f"{row['case_id']} is not in the scenario")
            continue
        if row["end_min"] - row["start_min"] != row["duration_min"]:
            problems.append(f"{row['case_id']} end does not match its duration")
        if row["room_id"] not in case["compatible_rooms"]:
            problems.append(f"{row['case_id']} is in an incompatible room")
        surgeon = surgeons.get(row["surgeon_id"])
        if surgeon is None or row["room_id"] not in surgeon["rooms"]:
            problems.append(f"{row['case_id']} surgeon cannot use {row['room_id']}")
        elif row["case_id"] not in locked_ids and (
            row["start_min"] < surgeon["start"] or row["end_min"] > surgeon["end"]
        ):
            problems.append(f"{row['case_id']} is outside surgeon hours")
        if row["case_id"] not in locked_ids and row["room_id"] in closed_rooms:
            problems.append(f"{row['case_id']} is booked in a closed room")
        if now is not None and row["case_id"] not in locked_ids and row["start_min"] < now:
            problems.append(f"{row['case_id']} starts before the current time")
        ready = case.get("ready_min")
        if ready is not None and row["case_id"] not in locked_ids and row["start_min"] < ready:
            problems.append(f"{row['case_id']} starts before it is ready")
        locks = schedule.get("locks") or {}
        if row["case_id"] in locks:
            lock = locks[row["case_id"]]
            if row["room_id"] != lock["room_id"] or row["start_min"] != lock["start_min"]:
                problems.append(f"{row['case_id']} is locked and was moved")

    by_room: dict[str, list[dict]] = {}
    by_surgeon: dict[str, list[dict]] = {}
    for row in _scheduled(schedule):
        by_room.setdefault(row["room_id"], []).append(row)
        by_surgeon.setdefault(row["surgeon_id"], []).append(row)

    for room_id, room_rows in by_room.items():
        ordered = sorted(room_rows, key=lambda row: row["start_min"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier["end_min"] > later["start_min"]:
                problems.append(f"overlap in {room_id}")
                break
            gap = scenario["cleaning"][by_case[earlier["case_id"]]["specialty"]]
            if later["start_min"] < earlier["end_min"] + gap:
                problems.append(f"turnover gap missing in {room_id}")
                break

    for surgeon_id, surgeon_rows in by_surgeon.items():
        ordered = sorted(surgeon_rows, key=lambda row: row["start_min"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier["end_min"] > later["start_min"]:
                problems.append(f"surgeon {surgeon_id} is double-booked")
                break

    if _recovery_blame(scenario, schedule, beds, locked_ids):
        problems.append("recovery beds exceeded by a case the planner was free to move")

    return problems


def executed_problems(scenario: dict, actuals: list[dict]) -> list[str]:
    """Rules on the realized timeline.

    Overlap, turnover, the surgeon, the room, and a start before the case is
    ready. A realized overrun that finishes after 16:00 is overtime, so this
    check does not call it a violation. Recovery pressure is the queue metric.
    """
    by_case = {case["id"]: case for case in scenario["cases"]}
    problems = []
    rows = [row for row in actuals if row.get("status") == "scheduled"]
    by_room: dict[str, list[dict]] = {}
    by_surgeon: dict[str, list[dict]] = {}
    for row in rows:
        case = by_case.get(row["case_id"])
        if case is None:
            problems.append(f"{row['case_id']} is not in the scenario")
            continue
        if row["room_id"] not in case["compatible_rooms"]:
            problems.append(f"{row['case_id']} ran in an incompatible room")
        ready = case.get("ready_min", scenario["open_min"])
        if row["start_min"] < ready:
            problems.append(f"{row['case_id']} started before it was ready")
        by_room.setdefault(row["room_id"], []).append(row)
        by_surgeon.setdefault(row["surgeon_id"], []).append(row)
    for room_id, room_rows in by_room.items():
        ordered = sorted(room_rows, key=lambda row: row["start_min"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier["end_min"] > later["start_min"]:
                problems.append(f"executed overlap in {room_id}")
                break
            gap = scenario["cleaning"][by_case[earlier["case_id"]]["specialty"]]
            if later["start_min"] < earlier["end_min"] + gap:
                problems.append(f"executed turnover gap missing in {room_id}")
                break
    for surgeon_id, surgeon_rows in by_surgeon.items():
        ordered = sorted(surgeon_rows, key=lambda row: row["start_min"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier["end_min"] > later["start_min"]:
                problems.append(f"surgeon {surgeon_id} overlapped on the executed timeline")
                break
    return problems


def recovery_load(scenario: dict, schedule: dict) -> list[tuple[int, int]]:
    """Minute-by-minute occupancy as steps of (time, beds in use), sorted."""
    events = []
    for row in _scheduled(schedule):
        start = row["end_min"]
        end = start + scenario["recovery_min"]
        events.append((start, 1))
        events.append((end, -1))
    events.sort()
    return events


def pacu_queue_minutes(scenario: dict, schedule: dict, beds: int, bed_change: tuple[int, int] | None = None) -> int:
    """Minutes of recovery occupancy above the bed limit.

    bed_change is (time, new_bed_count) when a disruption reduces capacity.
    """
    events = []
    for row in _scheduled(schedule):
        events.append((row["end_min"], 1))
        events.append((row["end_min"] + scenario["recovery_min"], -1))
    if bed_change is not None:
        events.append((bed_change[0], 0))
    events.sort(key=lambda item: (item[0], item[1]))
    current_beds = beds
    occupancy = 0
    queue = 0
    previous = None
    for time, delta in events:
        if previous is not None and time > previous and occupancy > current_beds:
            queue += (time - previous) * (occupancy - current_beds)
        if bed_change is not None and time >= bed_change[0] and delta == 0:
            current_beds = bed_change[1]
        occupancy += delta
        previous = time
    return queue


def _recovery_blame(scenario: dict, schedule: dict, beds: int, locked_ids: set) -> bool:
    """True when a case the planner could still move is in recovery during an overage."""
    rows = _scheduled(schedule)
    times = sorted({row["end_min"] for row in rows} | {row["end_min"] + scenario["recovery_min"] for row in rows})
    for time in times:
        inside = [row for row in rows if row["end_min"] <= time < row["end_min"] + scenario["recovery_min"]]
        if len(inside) > beds and any(row["case_id"] not in locked_ids for row in inside):
            return True
    return False
