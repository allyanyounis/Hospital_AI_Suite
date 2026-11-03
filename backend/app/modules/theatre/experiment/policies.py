"""Three ways to build a day, all on the same cases.

Baseline packs each room in list order. That is catalog.plan_day, the same
placement the theatre list uses.

Heuristic is the live suggestion rule, scored with planned minutes: if a room
finishes after 16:00, defer the single waiting elective whose removal cuts
overtime the most. It does not re-solve the day.

CP-SAT assigns rooms, surgeons, and start times. Hard constraints match the
validator. The weights in the scenario are the objective. A case that has
already started stays where it is. When the scenario carries
duration_samples, the morning solve scores overtime and idle over every
sampled version of the day (sample average approximation) instead of over
the single planned length.
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from .catalog import DAY_CLOSE, plan_day
from .contract import cancel_map, case_map, initial_cases, wait_map
from .validate import violations

SOLVER_WORKERS = 8
SOLVE_LIMIT = 0.3


def configure(solver: cp_model.CpSolver, time_limit: float) -> None:
    """Repeatable search: the same model gives the same plan on every run.

    The limit is CP-SAT deterministic time, not wall-clock seconds, and the
    workers interleave in a fixed order. The wall-clock cap is a safety net
    far above what the deterministic limit allows.
    """
    solver.parameters.num_workers = SOLVER_WORKERS
    solver.parameters.interleave_search = True
    solver.parameters.max_deterministic_time = time_limit
    solver.parameters.max_time_in_seconds = max(30.0, 20 * time_limit)
    solver.parameters.random_seed = 20261102


def row_for(case: dict, room_id: str, start: int, surgeon_id: str, duration: int, locked: bool = False) -> dict:
    return {
        "case_id": case["id"],
        "room_id": room_id,
        "start_min": start,
        "end_min": start + duration,
        "surgeon_id": surgeon_id,
        "status": "scheduled",
        "duration_min": duration,
        "locked": locked,
    }


def deferred(case: dict, duration: int | None = None) -> dict:
    return {
        "case_id": case["id"],
        "room_id": None,
        "start_min": None,
        "end_min": None,
        "surgeon_id": None,
        "status": "deferred",
        "duration_min": case["planned_min"] if duration is None else duration,
        "locked": False,
    }


def index_rows(schedule: dict) -> dict[str, dict]:
    return {row["case_id"]: row for row in schedule["assignments"]}


def baseline(scenario: dict, cases: list[dict] | None = None) -> dict:
    """Pack each case into its home room, in list order, from 08:00."""
    chosen = initial_cases(scenario) if cases is None else [case for case in cases if not case.get("arrives")]
    packing = [{"id": case["id"], "room_id": case["home_room"], "specialty": case["specialty"]} for case in chosen]
    durations = {case["id"]: case["planned_min"] for case in chosen}
    blocks = plan_day(packing, durations, scenario["cleaning"])
    by_id = {case["id"]: case for case in chosen}
    assignments = []
    placed = set()
    for block in blocks:
        if block["type"] != "case":
            continue
        case = by_id[block["case_id"]]
        assignments.append(row_for(case, block["room_id"], block["start_min"], case["surgeon_id"], case["planned_min"]))
        placed.add(case["id"])
    for case in chosen:
        if case["id"] not in placed:
            assignments.append(deferred(case))
    return {"policy": "baseline", "assignments": assignments, "locks": {}, "fallback": False, "solver": "plan_day"}


def _room_end(rows: list[dict], cleaning: int, open_min: int) -> int:
    cursor = open_min
    for index, row in enumerate(rows):
        cursor += row["duration_min"]
        if index < len(rows) - 1:
            cursor += cleaning
    return cursor


def heuristic(scenario: dict) -> dict:
    """One elective deferral per room that is planned to finish after 16:00."""
    schedule = baseline(scenario)
    by_id = case_map(scenario)
    assignments = schedule["assignments"]
    for room in scenario["rooms"]:
        rows = [row for row in assignments if row["status"] == "scheduled" and row["room_id"] == room["id"]]
        rows.sort(key=lambda row: row["start_min"])
        if not rows or rows[-1]["end_min"] <= DAY_CLOSE:
            continue
        gap = scenario["cleaning"][room["specialty"]]
        best = None
        best_end = rows[-1]["end_min"]
        for candidate in rows:
            if by_id[candidate["case_id"]]["urgency"] != "Elective":
                continue
            kept = [row for row in rows if row["case_id"] != candidate["case_id"]]
            end = _room_end(kept, gap, scenario["open_min"])
            if end < best_end:
                best = candidate
                best_end = end
        if best is None:
            continue
        for row in assignments:
            if row["case_id"] == best["case_id"]:
                row.update(deferred(by_id[row["case_id"]]))
                row["reason"] = "defer_elective_overtime"
                break
        kept = [row for row in assignments if row["status"] == "scheduled" and row["room_id"] == room["id"]]
        kept.sort(key=lambda row: row["start_min"])
        cursor = scenario["open_min"]
        for index, row in enumerate(kept):
            row["start_min"] = cursor
            row["end_min"] = cursor + row["duration_min"]
            cursor = row["end_min"] + (gap if index < len(kept) - 1 else 0)
    schedule["policy"] = "heuristic"
    schedule["solver"] = "defer_one_elective"
    return schedule


def _recovery_blocks(locks: dict, recovery_min: int) -> list[tuple[int, int, int]]:
    """Stretches of (start, end, how many locked cases are in recovery)."""
    events = []
    for lock in locks.values():
        events.append((lock["end_min"], 1))
        events.append((lock["end_min"] + recovery_min, -1))
    events.sort(key=lambda item: (item[0], item[1]))
    segments = []
    occupancy = 0
    previous = None
    for time, delta in events:
        if previous is not None and time > previous and occupancy:
            segments.append((previous, time, occupancy))
        occupancy += delta
        previous = time
    return segments


def _eligible_surgeons(scenario: dict, case: dict) -> list[dict]:
    return [surgeon for surgeon in scenario["surgeons"] if surgeon["specialty"] == case["specialty"]]


def greedy(
    scenario: dict, cases: list[dict], locks: dict, closed_rooms: set, recovery_beds: int, now: int | None
) -> dict:
    """Place cases into the first slot the validator accepts. Used when CP-SAT finds nothing."""
    by_id = {case["id"]: case for case in cases}
    assignments = []
    for case_id, lock in locks.items():
        case = by_id[case_id]
        assignments.append(
            row_for(case, lock["room_id"], lock["start_min"], lock["surgeon_id"], lock["duration_min"], locked=True)
        )
    rank = {"Immediate": 0, "Urgent": 1, "Expedited": 2, "Elective": 3}
    waiting = sorted(
        (case for case in cases if case["id"] not in locks), key=lambda case: (rank[case["urgency"]], case["id"])
    )
    earliest = scenario["open_min"] if now is None else now
    for case in waiting:
        placed = False
        rooms = [room for room in case["compatible_rooms"] if room not in closed_rooms]
        step = 15
        for room_id in rooms:
            for surgeon in _eligible_surgeons(scenario, case):
                if room_id not in surgeon["rooms"]:
                    continue
                ready = max(earliest, case.get("ready_min", scenario["open_min"]))
                last = surgeon["end"] - case["planned_min"]
                start = ready
                while start <= last and not placed:
                    trial_row = row_for(case, room_id, start, surgeon["id"], case["planned_min"])
                    known = {row["case_id"] for row in assignments}
                    known.add(case["id"])
                    trial = {
                        "assignments": assignments
                        + [trial_row]
                        + [deferred(other) for other in waiting if other["id"] not in known],
                        "locks": locks,
                    }
                    if not violations(
                        scenario,
                        trial,
                        now=now,
                        closed_rooms=closed_rooms,
                        recovery_beds=recovery_beds,
                        locked_ids=set(locks),
                    ):
                        assignments.append(trial_row)
                        placed = True
                    start += step
                if placed:
                    break
            if placed:
                break
        if not placed:
            assignments.append(deferred(case))
    return {
        "policy": "cpsat",
        "assignments": assignments,
        "locks": locks,
        "fallback": True,
        "solver": "greedy",
    }


def cpsat(
    scenario: dict,
    cases: list[dict] | None = None,
    locks: dict | None = None,
    closed_rooms: set | None = None,
    recovery_beds: int | None = None,
    reference: dict | None = None,
    now: int | None = None,
    time_limit: float = SOLVE_LIMIT,
) -> dict:
    """Constraint solve. Falls back to the greedy packer if the model has no solution in time."""
    chosen = list(initial_cases(scenario) if cases is None else cases)
    locks = locks or {}
    closed_rooms = set(closed_rooms or ())
    beds = scenario["recovery_beds"] if recovery_beds is None else recovery_beds
    reference = reference if reference is not None else index_rows(baseline(scenario))
    weights = scenario["weights"]
    open_min = scenario["open_min"]
    close_min = scenario["close_min"]
    horizon = scenario["latest_min"]
    for lock in locks.values():
        horizon = max(horizon, lock["end_min"])

    model = cp_model.CpModel()
    present: dict[str, cp_model.IntVar] = {}
    start: dict[str, cp_model.IntVar] = {}
    end: dict[str, cp_model.IntVar] = {}
    room_lit: dict[tuple[str, str], cp_model.IntVar] = {}
    surg_lit: dict[tuple[str, str], cp_model.IntVar] = {}
    earliest = open_min if now is None else now

    for case in chosen:
        cid = case["id"]
        present[cid] = model.NewBoolVar(f"p_{cid}")
        start[cid] = model.NewIntVar(open_min, horizon, f"s_{cid}")
        end[cid] = model.NewIntVar(open_min, horizon, f"e_{cid}")
        if cid in locks:
            lock = locks[cid]
            model.Add(present[cid] == 1)
            model.Add(start[cid] == lock["start_min"])
            model.Add(end[cid] == lock["end_min"])
            for room_id in case["compatible_rooms"]:
                lit = model.NewBoolVar(f"r_{cid}_{room_id}")
                room_lit[(cid, room_id)] = lit
                model.Add(lit == int(room_id == lock["room_id"]))
            for surgeon in _eligible_surgeons(scenario, case):
                lit = model.NewBoolVar(f"g_{cid}_{surgeon['id']}")
                surg_lit[(cid, surgeon["id"])] = lit
                model.Add(lit == int(surgeon["id"] == lock["surgeon_id"]))
            continue

        rooms = [room_id for room_id in case["compatible_rooms"] if room_id not in closed_rooms]
        surgeons = [
            surgeon
            for surgeon in _eligible_surgeons(scenario, case)
            if any(room_id in surgeon["rooms"] for room_id in rooms)
        ]
        if not rooms or not surgeons:
            if case["urgency"] in ("Urgent", "Immediate"):
                model.Add(present[cid] == 1)
                model.Add(present[cid] == 0)
            else:
                model.Add(present[cid] == 0)
            continue
        if case["urgency"] in ("Urgent", "Immediate"):
            model.Add(present[cid] == 1)
        model.Add(end[cid] == start[cid] + case["planned_min"]).OnlyEnforceIf(present[cid])
        model.Add(start[cid] >= max(earliest, case.get("ready_min", open_min))).OnlyEnforceIf(present[cid])
        model.Add(end[cid] <= horizon).OnlyEnforceIf(present[cid])
        room_vars = []
        for room_id in rooms:
            lit = model.NewBoolVar(f"r_{cid}_{room_id}")
            room_lit[(cid, room_id)] = lit
            room_vars.append(lit)
        model.Add(sum(room_vars) == present[cid])
        surg_vars = []
        for surgeon in surgeons:
            lit = model.NewBoolVar(f"g_{cid}_{surgeon['id']}")
            surg_lit[(cid, surgeon["id"])] = lit
            surg_vars.append(lit)
            for room_id in rooms:
                if room_id not in surgeon["rooms"]:
                    model.AddBoolOr([room_lit[(cid, room_id)].Not(), lit.Not()])
        model.Add(sum(surg_vars) == present[cid])

    planned = {case["id"]: case["planned_min"] for case in chosen}

    def length(cid: str) -> int:
        if cid in locks:
            return locks[cid]["end_min"] - locks[cid]["start_min"]
        return planned[cid]

    # One optional interval per (case, room) and per (case, surgeon). The room
    # interval carries the turnover after the case, so NoOverlap enforces it.
    for room in scenario["rooms"]:
        gap = scenario["cleaning"][room["specialty"]]
        intervals = [
            model.NewOptionalFixedSizeIntervalVar(
                start[cid], length(cid) + gap, room_lit[(cid, room["id"])], f"ri_{cid}_{room['id']}"
            )
            for cid in (case["id"] for case in chosen)
            if (cid, room["id"]) in room_lit
        ]
        model.AddNoOverlap(intervals)

    for surgeon in scenario["surgeons"]:
        intervals = [
            model.NewOptionalFixedSizeIntervalVar(
                start[cid], length(cid), surg_lit[(cid, surgeon["id"])], f"si_{cid}_{surgeon['id']}"
            )
            for cid in (case["id"] for case in chosen)
            if (cid, surgeon["id"]) in surg_lit
        ]
        model.AddNoOverlap(intervals)

    recovery_intervals = []
    demands = []
    # Cases already running keep their recovery time. If they alone exceed the bed
    # limit, a single cumulative constraint would be unsatisfiable. Block the
    # saturated stretches instead, and let the validator ignore overage that only
    # those locked cases cause.
    for index, (left, right, occupancy) in enumerate(_recovery_blocks(locks, scenario["recovery_min"])):
        demand = min(occupancy, beds)
        length = right - left
        if length <= 0 or demand <= 0:
            continue
        block_start = model.NewIntVar(left, left, f"rb_s_{index}")
        block_end = model.NewIntVar(right, right, f"rb_e_{index}")
        recovery_intervals.append(model.NewIntervalVar(block_start, length, block_end, f"rb_{index}"))
        demands.append(demand)
    for case in chosen:
        cid = case["id"]
        if cid in locks or cid not in present:
            continue
        if not any((cid, room_id) in room_lit for room_id in case["compatible_rooms"]):
            continue
        rec_end = model.NewIntVar(open_min, horizon + scenario["recovery_min"], f"re_{cid}")
        model.Add(rec_end == end[cid] + scenario["recovery_min"]).OnlyEnforceIf(present[cid])
        recovery_intervals.append(
            model.NewOptionalIntervalVar(end[cid], scenario["recovery_min"], rec_end, present[cid], f"rec_{cid}")
        )
        demands.append(1)
    if recovery_intervals:
        model.AddCumulative(recovery_intervals, demands, beds)

    # Stochastic mode: duration_samples holds K plausible lengths per case. Room
    # overtime and idle are then averaged over the K versions of the day instead
    # of read off the single planned length. Only the morning plan uses it.
    samples = scenario.get("duration_samples") if not locks and now is None else None
    draws = len(next(iter(samples.values()))) if samples else 1
    objective = []
    sampled = []
    for room in scenario["rooms"]:
        members = [case["id"] for case in chosen if (case["id"], room["id"]) in room_lit]
        finish = model.NewIntVar(open_min, horizon, f"fin_{room['id']}")
        model.Add(finish >= open_min)
        for cid in members:
            model.Add(finish >= end[cid]).OnlyEnforceIf(room_lit[(cid, room["id"])])
        if samples:
            gap = scenario["cleaning"][room["specialty"]]
            for k in range(draws):
                load = sum((samples[cid][k] + gap) * room_lit[(cid, room["id"])] for cid in members)
                overtime = model.NewIntVar(0, 4 * horizon, f"ot_{room['id']}_{k}")
                model.Add(overtime >= open_min + load - gap - close_min)
                idle = model.NewIntVar(0, close_min - open_min, f"idle_{room['id']}_{k}")
                model.Add(idle >= close_min - open_min - load)
                sampled.append(overtime * weights["overtime_per_min"])
                sampled.append(idle * weights["idle_per_min"])
            # Keeps the planned timeline packed. Worth 1/K of a minute per minute.
            sampled.append(finish)
            continue
        overtime = model.NewIntVar(0, horizon, f"ot_{room['id']}")
        model.Add(overtime >= finish - close_min)
        idle = model.NewIntVar(0, close_min - open_min, f"idle_{room['id']}")
        model.Add(idle >= close_min - finish)
        objective.append(overtime * weights["overtime_per_min"])
        objective.append(idle * weights["idle_per_min"])

    for case in chosen:
        cid = case["id"]
        if cid in locks or cid not in present:
            continue
        if (cid, case["compatible_rooms"][0]) not in room_lit and not any(
            (cid, room_id) in room_lit for room_id in case["compatible_rooms"]
        ):
            continue
        waits = wait_map(weights)
        cancels = cancel_map(weights)
        wait_weight = waits[case["urgency"]]
        if wait_weight:
            waiting = model.NewIntVar(0, horizon, f"w_{cid}")
            ready = case.get("ready_min", open_min)
            model.Add(waiting >= start[cid] - ready).OnlyEnforceIf(present[cid])
            model.Add(waiting == 0).OnlyEnforceIf(present[cid].Not())
            objective.append(waiting * wait_weight)
        if case["urgency"] in cancels and cancels[case["urgency"]]:
            amount = int(cancels[case["urgency"]])
            penalty = model.NewIntVar(0, amount, f"can_{cid}")
            model.Add(penalty == 0).OnlyEnforceIf(present[cid])
            model.Add(penalty == amount).OnlyEnforceIf(present[cid].Not())
            objective.append(penalty)
        if case["urgency"] == "Urgent":
            late = model.NewIntVar(0, horizon, f"late_{cid}")
            target = open_min + 6 * 60
            model.Add(late >= start[cid] - target).OnlyEnforceIf(present[cid])
            model.Add(late == 0).OnlyEnforceIf(present[cid].Not())
            objective.append(late * weights["urgent_late_per_min"])
        if case["urgency"] == "Immediate":
            late = model.NewIntVar(0, horizon, f"late_{cid}")
            target = case.get("ready_min", open_min) + 60
            model.Add(late >= start[cid] - target).OnlyEnforceIf(present[cid])
            model.Add(late == 0).OnlyEnforceIf(present[cid].Not())
            objective.append(late * weights["immediate_late_per_min"])
        ref = reference.get(cid)
        if ref and ref["status"] == "scheduled" and (cid, ref["room_id"]) in room_lit:
            moved = model.NewBoolVar(f"mv_{cid}")
            model.Add(moved + room_lit[(cid, ref["room_id"])] == 1)
            objective.append(moved * weights["change"])

    if objective or sampled:
        model.Minimize(draws * sum(objective) + sum(sampled))

    solver = cp_model.CpSolver()
    configure(solver, time_limit)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        fallback = greedy(scenario, chosen, locks, closed_rooms, beds, now)
        fallback["solver"] = "greedy"
        return fallback

    assignments = []
    for case in chosen:
        cid = case["id"]
        if cid not in present or solver.Value(present[cid]) == 0:
            assignments.append(deferred(case))
            continue
        room_id = next(
            room
            for room in case["compatible_rooms"]
            if (cid, room) in room_lit and solver.Value(room_lit[(cid, room)]) == 1
        )
        surgeon_id = next(
            surgeon["id"]
            for surgeon in _eligible_surgeons(scenario, case)
            if (cid, surgeon["id"]) in surg_lit and solver.Value(surg_lit[(cid, surgeon["id"])]) == 1
        )
        start_min = solver.Value(start[cid])
        end_min = solver.Value(end[cid])
        assignments.append(
            {
                "case_id": cid,
                "room_id": room_id,
                "start_min": start_min,
                "end_min": end_min,
                "surgeon_id": surgeon_id,
                "status": "scheduled",
                "duration_min": end_min - start_min,
                "locked": cid in locks,
            }
        )
    return {
        "policy": "cpsat",
        "assignments": assignments,
        "locks": locks,
        "fallback": False,
        "solver": "cp-sat" if status == cp_model.OPTIMAL else "cp-sat-feasible",
    }
