"""Play a schedule forward, and replan the cases that have not started.

Realized minutes are the shared draws on the scenario, so every policy sees
the same overrun. The recovery policy freezes cases that have started, applies
the disruption, and calls the CP-SAT planner on what is left. The planner gets
estimates for cases still running, never their realized end. The no-replan
twin is a manual rule: it keeps the original order, gives an emergency the
next free turn, and shifts later cases.
"""

from __future__ import annotations

from .contract import cancel_map, case_map, wait_map, world_minutes
from .policies import SOLVE_LIMIT, cpsat, deferred, index_rows, row_for
from .validate import executed_problems, pacu_queue_minutes, violations

BECAUSE = {
    "overrun": "the case in theatre ran long",
    "emergency": "an emergency arrived",
    "room_outage": "a theatre closed",
    "pacu": "recovery beds were reduced",
}
BLOCKED = {
    "overrun": "A case that has already started keeps its room and its start, so the old start is no longer free.",
    "emergency": "An emergency cannot start before it arrives, and it cannot be placed inside a case that is already in the room.",
    "room_outage": "A case that has not started cannot stay in a closed theatre.",
    "pacu": "Recovery holds one bed for 40 minutes. With fewer beds, a later case no longer fits.",
}
COMBINED_BLOCKED = (
    "The overrun keeps the case already in theatre where it is. "
    "The emergency then needs a free future slot, and a started case is not interrupted."
)


def events_of(scenario: dict) -> list[dict]:
    return list(scenario.get("events") or [scenario["disruption"]])


def situation(scenario: dict) -> tuple[set, int | None, tuple[int, int] | None]:
    """Closed rooms, recovery beds, and the moment the bed count changes."""
    closed: set = set()
    beds = None
    bed_change = None
    for event in events_of(scenario):
        if event["type"] == "room_outage":
            closed.add(event["room_id"])
        if event["type"] == "pacu":
            beds = event["beds"]
            bed_change = (event["at"], event["beds"])
    return closed, beds, bed_change


def _because(scenario: dict) -> str:
    events = events_of(scenario)
    if len(events) > 1:
        return "an overrun, then an emergency"
    return BECAUSE[events[0]["type"]]


def _blocked(scenario: dict) -> str:
    events = events_of(scenario)
    if len(events) > 1:
        return COMBINED_BLOCKED
    return BLOCKED[events[0]["type"]]


def execute(scenario: dict, schedule: dict) -> list[dict]:
    """Apply realized durations.

    A locked row keeps its start, which already happened. Its length is the
    realized one: the plan only carried an estimate of when it would end.
    """
    by_id = case_map(scenario)
    room_cursor = {room["id"]: scenario["open_min"] for room in scenario["rooms"]}
    surgeon_free = {surgeon["id"]: surgeon["start"] for surgeon in scenario["surgeons"]}
    actuals = []
    scheduled = [row for row in schedule["assignments"] if row["status"] == "scheduled"]
    for row in sorted(scheduled, key=lambda item: (item["start_min"], item["case_id"])):
        case = by_id[row["case_id"]]
        if row.get("locked"):
            start = row["start_min"]
            duration = world_minutes(scenario, case)
            end = start + duration
        else:
            duration = world_minutes(scenario, case)
            ready = case.get("ready_min", scenario["open_min"])
            start = max(row["start_min"], room_cursor[row["room_id"]], surgeon_free[row["surgeon_id"]], ready)
            end = start + duration
        done = dict(row, start_min=start, end_min=end, duration_min=duration)
        actuals.append(done)
        gap = scenario["cleaning"][case["specialty"]]
        room_cursor[row["room_id"]] = max(room_cursor[row["room_id"]], end + gap)
        surgeon_free[row["surgeon_id"]] = max(surgeon_free[row["surgeon_id"]], end)
    for row in schedule["assignments"]:
        if row["status"] == "deferred":
            actuals.append(dict(row))
    return actuals


def started_by(scenario: dict, schedule: dict, until: int) -> dict[str, dict]:
    """Cases whose realized start is before `until`. Their end includes the world duration."""
    probed = execute(scenario, schedule)
    started = {}
    for row in probed:
        if row["status"] != "scheduled" or row["start_min"] >= until:
            continue
        started[row["case_id"]] = dict(row, locked=True)
    return started


def _covered(intervals: list[tuple[int, int]], start: int, end: int) -> int:
    clips = []
    for left, right in intervals:
        left, right = max(left, start), min(right, end)
        if right > left:
            clips.append((left, right))
    clips.sort()
    total = 0
    cursor = start
    for left, right in clips:
        left = max(left, cursor)
        if right > left:
            total += right - left
            cursor = right
    return total


def changes_between(scenario: dict, before: list[dict], after: list[dict], because: str | None = None) -> list[dict]:
    previous = {row["case_id"]: row for row in before}
    revised = {row["case_id"]: row for row in after}
    because = because or _because(scenario)
    blocked = _blocked(scenario)
    titles = {case["id"]: case["title"] for case in scenario["cases"]}
    found = []
    for case_id in list(dict.fromkeys(list(previous) + list(revised))):
        old = previous.get(case_id)
        new = revised.get(case_id)
        if old and new and old["status"] == new["status"] == "deferred":
            continue
        if old and new and old["status"] == new["status"] == "scheduled" and old["room_id"] == new["room_id"]:
            if abs(old["start_min"] - new["start_min"]) < 15:
                continue
        if old is None and new and new["status"] == "deferred":
            continue
        if old and new and old["status"] == "scheduled" and new["status"] == "deferred":
            reason = f"Deferred after {because}."
            kind = "deferred"
        elif (
            old
            and new
            and old["status"] == "scheduled"
            and new["status"] == "scheduled"
            and old["room_id"] != new["room_id"]
        ):
            reason = f"Moved from {old['room_id']} to {new['room_id']} after {because}."
            kind = "moved"
        elif old is None or (old["status"] == "deferred" and new and new["status"] == "scheduled"):
            reason = f"Placed after {because}."
            kind = "added"
        else:
            reason = f"Start moved after {because}."
            kind = "shifted"
        found.append(
            {
                "case_id": case_id,
                "title": titles.get(case_id, case_id),
                "kind": kind,
                "reason": reason,
                "from_room": None if old is None else old["room_id"],
                "to_room": None if new is None else new["room_id"],
                "from_start": None if old is None else old["start_min"],
                "to_start": None if new is None else new["start_min"],
                "blocked": blocked,
            }
        )
    return found


def score(
    scenario: dict,
    plan: dict,
    actual: list[dict],
    changes: list[dict],
    *,
    now: int | None = None,
    closed_rooms: set | None = None,
    recovery_beds: int | None = None,
) -> dict:
    by_id = case_map(scenario)
    finishes: dict[str, int] = {}
    waiting = 0
    urgent_waiting = 0
    performed = []
    for row in actual:
        if row["status"] != "scheduled":
            continue
        performed.append(row)
        finishes[row["room_id"]] = max(finishes.get(row["room_id"], scenario["open_min"]), row["end_min"])
        case = by_id[row["case_id"]]
        wait = max(0, row["start_min"] - case.get("ready_min", scenario["open_min"]))
        waiting += wait
        if case["urgency"] in ("Urgent", "Immediate"):
            urgent_waiting += wait
    idle = 0
    for room in scenario["rooms"]:
        rows = sorted((row for row in performed if row["room_id"] == room["id"]), key=lambda row: row["start_min"])
        intervals = []
        for index, row in enumerate(rows):
            intervals.append((row["start_min"], row["end_min"]))
            if index < len(rows) - 1:
                gap = scenario["cleaning"][by_id[row["case_id"]]["specialty"]]
                intervals.append((row["end_min"], min(row["end_min"] + gap, rows[index + 1]["start_min"])))
        idle += (scenario["close_min"] - scenario["open_min"]) - _covered(
            intervals, scenario["open_min"], scenario["close_min"]
        )
    bed_change = situation(scenario)[2]
    # The morning still has the original bed count. The drop applies at the event.
    queue = pacu_queue_minutes(scenario, {"assignments": actual}, scenario["recovery_beds"], bed_change)
    problems = violations(
        scenario,
        plan,
        now=now,
        closed_rooms=closed_rooms,
        recovery_beds=recovery_beds,
        locked_ids=set(plan.get("locks") or {}),
    )
    played = executed_problems(scenario, actual)
    deferred_rows = [row for row in plan["assignments"] if row["status"] == "deferred"]
    deferred_count = len(deferred_rows)
    overtime = int(sum(max(0, end - scenario["close_min"]) for end in finishes.values()))

    # How far the published list was from the day as played.
    published = {row["case_id"]: row for row in plan["assignments"] if row["status"] == "scheduled"}
    planned_finish: dict[str, int] = {}
    for row in published.values():
        planned_finish[row["room_id"]] = max(planned_finish.get(row["room_id"], scenario["open_min"]), row["end_min"])
    finish_errors = [abs(finishes[room] - planned_finish[room]) for room in finishes if room in planned_finish]
    late_starts = [
        max(0, row["start_min"] - published[row["case_id"]]["start_min"])
        for row in performed
        if row["case_id"] in published
    ]

    # One number under the scenario's own weights, so a policy cannot look good
    # on overtime by quietly deferring more work.
    weights = scenario["weights"]
    cancels = cancel_map(weights)
    waits = wait_map(weights)
    cost = overtime * weights["overtime_per_min"] + idle * weights["idle_per_min"]
    cost += sum(cancels.get(by_id[row["case_id"]]["urgency"], 0) for row in deferred_rows)
    for row in performed:
        case = by_id[row["case_id"]]
        cost += waits[case["urgency"]] * max(0, row["start_min"] - case.get("ready_min", scenario["open_min"]))
    return {
        "overtime_min": overtime,
        "performed_min": int(sum(row["end_min"] - row["start_min"] for row in performed)),
        "deferred_min": int(sum(world_minutes(scenario, by_id[row["case_id"]]) for row in deferred_rows)),
        "finish_error_min": round(sum(finish_errors) / len(finish_errors), 1) if finish_errors else 0.0,
        "late_start_min": round(sum(late_starts) / len(late_starts), 1) if late_starts else 0.0,
        "weighted_cost": int(cost),
        "waiting_min": int(waiting),
        "urgent_waiting_min": int(urgent_waiting),
        "cancellations": deferred_count,
        "deferred_off_today": deferred_count,
        "idle_min": int(idle),
        "pacu_queue_min": int(queue),
        "changes": len(changes),
        "violations": len(problems),
        "plan_violations": len(problems),
        "executed_violations": len(played),
        "violation_detail": problems,
        "executed_detail": played,
        "solver": plan.get("solver", ""),
        "fallback": bool(plan.get("fallback")),
    }


def _manual_emergency(scenario: dict, rows: list[dict], case: dict, arrival: int, closed: set) -> list[dict]:
    """What a coordinator does by hand: the emergency takes the next free turn.

    Each open compatible room offers the end of whatever is in it at arrival
    (plus turnover), or the arrival itself if the room is between cases. The
    earliest offer wins, the home room on a tie. The cases that were due after
    it in that room slide back. Nothing is deferred and no other room changes.
    """
    gap = scenario["cleaning"][case["specialty"]]
    offers = []
    for room_id in case["compatible_rooms"]:
        if room_id in closed:
            continue
        before = [
            row
            for row in rows
            if row["status"] == "scheduled" and row["room_id"] == room_id and row["start_min"] < arrival
        ]
        turn = max([arrival] + [row["end_min"] + gap for row in before])
        offers.append((turn, room_id != case["home_room"], room_id))
    if not offers:
        return rows + [deferred(case)]
    turn, _, room_id = min(offers)
    cursor = turn + case["planned_min"] + gap
    shifted = []
    for row in sorted(rows, key=lambda item: (item["start_min"] is None, item["start_min"] or 0)):
        if row["status"] == "scheduled" and row["room_id"] == room_id and row["start_min"] >= arrival:
            start = max(row["start_min"], cursor)
            row = dict(row, start_min=start, end_min=start + row["duration_min"])
            cursor = row["end_min"] + gap
        shifted.append(row)

    surgeons = [
        surgeon
        for surgeon in scenario["surgeons"]
        if surgeon["specialty"] == case["specialty"] and room_id in surgeon["rooms"]
    ]
    finish = turn + case["planned_min"]

    def free(surgeon_id: str) -> bool:
        return not any(
            row["status"] == "scheduled"
            and row["surgeon_id"] == surgeon_id
            and row["start_min"] < finish
            and turn < row["end_min"]
            for row in shifted
        )

    # The on-call surgeon is whoever covers the room and is not in another case.
    ranked = sorted(surgeons, key=lambda surgeon: (not free(surgeon["id"]), surgeon["id"] != case["surgeon_id"]))
    return shifted + [row_for(case, room_id, turn, ranked[0]["id"], case["planned_min"])]


def no_replan(scenario: dict, initial: dict, started: dict[str, dict]) -> dict:
    """The manual rule. Keep the original order and apply every disruption by hand.

    A closed room loses the cases that have not started. Each emergency takes
    the next free turn in a compatible room, and the cases after it slide.
    No solver runs.
    """
    events = events_of(scenario)
    closed = {event["room_id"] for event in events if event["type"] == "room_outage"}
    rows = []
    for row in initial["assignments"]:
        if closed and row["status"] == "scheduled" and row["room_id"] in closed and row["case_id"] not in started:
            case = case_map(scenario)[row["case_id"]]
            rows.append(deferred(case))
            continue
        rows.append(dict(row))
    placed = {row["case_id"] for row in rows}
    for event in events:
        if event["type"] != "emergency":
            continue
        case = next(item for item in scenario["cases"] if item.get("ready_min") == event["at"] and item.get("arrives"))
        if case["id"] in placed:
            continue
        rows = _manual_emergency(scenario, rows, case, event["at"], closed)
        placed.add(case["id"])
    locks = {}
    for row in rows:
        if row["status"] == "scheduled" and row["case_id"] in started:
            locks[row["case_id"]] = {"room_id": row["room_id"], "start_min": row["start_min"]}
    return {"policy": "no_replan", "assignments": rows, "locks": locks, "solver": "shift_only"}


RUNNING_FLOOR = 15


def _reported_extra(scenario: dict, case_id: str, now: int) -> int:
    """Minutes of overrun the theatre has reported for this case by `now`."""
    return sum(
        int(event.get("extra_min") or 0)
        for event in events_of(scenario)
        if event["type"] == "overrun" and event.get("case_id") == case_id and event["at"] <= now
    )


def _locks_from(scenario: dict, started: dict[str, dict], now: int) -> dict:
    """Freeze what has started, with only what the theatre could know at `now`.

    A finished case has a known end. A case still running ends at its planned
    length plus any reported overrun, and never sooner than RUNNING_FLOOR
    minutes from now. The realized end is not given to the planner.
    """
    by_id = case_map(scenario)
    locks = {}
    for case_id, row in started.items():
        if row["end_min"] <= now:
            end = row["end_min"]
        else:
            case = by_id[case_id]
            estimate = row["start_min"] + case["planned_min"] + _reported_extra(scenario, case_id, now)
            end = max(estimate, now + RUNNING_FLOOR)
        locks[case_id] = {
            "room_id": row["room_id"],
            "start_min": row["start_min"],
            "end_min": end,
            "surgeon_id": row["surgeon_id"],
            "duration_min": end - row["start_min"],
        }
    return locks


def _cases_known(scenario: dict, event: dict, locks: dict) -> list[dict]:
    """Cases the planner may use once this event has happened.

    An overrun case that has not started yet is planned at its planned length
    plus the reported overrun, not at its realized length.
    """
    known = [item for item in events_of(scenario) if item["at"] <= event["at"]]
    include_emergency = any(item["type"] == "emergency" for item in known)
    cases = []
    for case in scenario["cases"]:
        if case.get("arrives") and not include_emergency:
            continue
        extra = _reported_extra(scenario, case["id"], event["at"])
        if extra and case["id"] not in locks:
            cases.append(dict(case, planned_min=case["planned_min"] + extra))
        else:
            cases.append(case)
    return cases


def _stamp(revised: dict, locks: dict) -> None:
    for row in revised["assignments"]:
        if row["case_id"] not in locks:
            continue
        lock = locks[row["case_id"]]
        row["locked"] = True
        row["start_min"] = lock["start_min"]
        row["end_min"] = lock["end_min"]
        row["duration_min"] = lock["duration_min"]
        row["room_id"] = lock["room_id"]
        row["surgeon_id"] = lock["surgeon_id"]
        row["status"] = "scheduled"
    revised["locks"] = locks


def recover(scenario: dict, time_limit: float = SOLVE_LIMIT, initial: dict | None = None) -> dict:
    """CP-SAT plan, then one new CP-SAT after each disruption, in time order.

    `initial` reuses a morning CP-SAT plan already solved for the same scenario.
    """
    initial = initial or cpsat(scenario, time_limit=time_limit)
    events = events_of(scenario)
    plan = initial
    closed: set = set()
    beds = scenario["recovery_beds"]
    for event in events:
        started = started_by(scenario, plan, event["at"])
        locks = _locks_from(scenario, started, event["at"])
        if event["type"] == "room_outage":
            closed.add(event["room_id"])
        if event["type"] == "pacu":
            beds = event["beds"]
        revised = cpsat(
            scenario,
            cases=_cases_known(scenario, event, locks),
            locks=locks,
            closed_rooms=set(closed),
            recovery_beds=beds,
            reference=index_rows(plan),
            now=event["at"],
            time_limit=time_limit,
        )
        _stamp(revised, locks)
        plan = revised
    last = events[-1]
    twin = no_replan(scenario, initial, started_by(scenario, initial, events[0]["at"]))
    moved = changes_between(scenario, initial["assignments"], plan["assignments"])
    actual = execute(scenario, plan)
    twin_actual = execute(scenario, twin)
    return {
        "policy": "recovery",
        "plan": revised,
        "original": initial,
        "actual": actual,
        "changes": moved,
        "metrics": score(scenario, plan, actual, moved, now=last["at"], closed_rooms=closed, recovery_beds=beds),
        "no_replan": {
            "plan": twin,
            "actual": twin_actual,
            "metrics": score(scenario, twin, twin_actual, [], closed_rooms=closed, recovery_beds=beds),
        },
    }


def react(scenario: dict, plan: dict) -> dict:
    """Apply every disruption without reordering. Every static policy is scored after this."""
    started = started_by(scenario, plan, events_of(scenario)[0]["at"])
    return no_replan(scenario, plan, started)


def run_policy(scenario: dict, name: str, time_limit: float = SOLVE_LIMIT, initial: dict | None = None) -> dict:
    """Score one policy. `initial` is a morning CP-SAT plan to reuse for cpsat and recovery."""
    from .policies import baseline, heuristic

    if name == "recovery":
        return recover(scenario, time_limit=time_limit, initial=initial)
    if len(events_of(scenario)) > 1:
        because = _because(scenario)
        if name == "baseline":
            plan = baseline(scenario)
        elif name == "heuristic":
            plan = heuristic(scenario)
        elif name == "cpsat":
            plan = initial or cpsat(scenario, time_limit=time_limit)
        else:
            raise ValueError(name)
    elif name == "baseline":
        plan = baseline(scenario)
        because = BECAUSE[scenario["disruption"]["type"]]
    elif name == "heuristic":
        plan = heuristic(scenario)
        because = "the room was planned to finish after 16:00"
    elif name == "cpsat":
        plan = initial or cpsat(scenario, time_limit=time_limit)
        because = "the constraint solver changed the packed list"
    else:
        raise ValueError(name)
    reacted = react(scenario, plan)
    if name == "baseline":
        comparison = changes_between(scenario, plan["assignments"], reacted["assignments"], because=because)
    else:
        comparison = changes_between(
            scenario,
            baseline(scenario)["assignments"],
            reacted["assignments"],
            because=because,
        )
    actual = execute(scenario, reacted)
    closed, beds, _bed_change = situation(scenario)
    return {
        "policy": name,
        "plan": reacted,
        "morning": plan,
        "actual": actual,
        "changes": comparison,
        "metrics": score(scenario, reacted, actual, comparison, closed_rooms=closed, recovery_beds=beds),
    }
