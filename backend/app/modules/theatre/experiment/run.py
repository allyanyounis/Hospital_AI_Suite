"""One seeded day of the scheduling experiment: build the day, play the rolling CP-SAT recovery policy against it,
and return the morning plan, the revised plan and both days' metrics. The POC's 100-seed batch runner, CLI and
ML duration track are not ported; their precomputed results ship as data/experiment_summary.json."""

from __future__ import annotations

from .catalog import load_catalog
from .contract import DISRUPTIONS, PROFILES, build_scenario
from .recover import run_policy

METRICS = (
    "overtime_min",
    "waiting_min",
    "urgent_waiting_min",
    "cancellations",
    "deferred_min",
    "performed_min",
    "idle_min",
    "pacu_queue_min",
    "changes",
    "violations",
    "executed_violations",
    "weighted_cost",
)
DEFAULT_SEED = 20261101
WHEN = {"early": 9 * 60, "midday": 10 * 60 + 30, "late": 14 * 60}


def _public_assignment(scenario: dict, row: dict) -> dict:
    case = next(item for item in scenario["cases"] if item["id"] == row["case_id"])
    return {
        "case_id": row["case_id"],
        "title": case["title"],
        "specialty": case["specialty"],
        "urgency": case["urgency"],
        "planned_min": case["planned_min"],
        "room_id": row["room_id"],
        "start_min": row["start_min"],
        "end_min": row["end_min"],
        "status": row["status"],
        "surgeon_id": row["surgeon_id"],
    }


def _example(scenario: dict, result: dict) -> dict:
    return {
        "seed": scenario["seed"],
        "disruption": scenario["disruption"],
        "provenance": scenario["provenance"],
        "weights": scenario["weights"],
        "rooms": scenario["rooms"],
        "recovery_beds": scenario["recovery_beds"],
        "original": [_public_assignment(scenario, row) for row in result["original"]["assignments"]],
        "revised": [_public_assignment(scenario, row) for row in result["plan"]["assignments"]],
        "changes": result["changes"],
        "recovery": {key: result["metrics"][key] for key in METRICS},
        "no_replan": {key: result["no_replan"]["metrics"][key] for key in METRICS},
        "solver": result["plan"].get("solver", ""),
        "fallback": bool(result["metrics"]["fallback"]),
        "events": [
            {"type": event["type"], "at": event["at"]} for event in scenario.get("events") or [scenario["disruption"]]
        ],
    }


def one_day(options: dict, catalog: tuple[dict, dict] | None = None) -> dict:
    """One seeded day for the Experiment screen. It does not touch the theatre list."""
    pools, cleaning = catalog or load_catalog()
    try:
        seed = int(options.get("seed") or DEFAULT_SEED)
    except (TypeError, ValueError):
        return {"error": "The seed needs to be a whole number."}
    kind = options.get("disruption") or None
    second = "emergency" if options.get("second") else None
    if second:
        kind = kind or DISRUPTIONS[seed % len(DISRUPTIONS)]
        if kind == "emergency":
            kind = "overrun"
    at = WHEN.get(options.get("when") or "midday", WHEN["midday"])
    profile = options.get("profile") if options.get("profile") in PROFILES else "balanced"
    stress = bool(options.get("stress"))
    scenario = build_scenario(
        seed,
        pools,
        cleaning,
        kind,
        at=at,
        profile=profile,
        second=second,
        duration_stress=stress,
        duration_scale=1.25 if stress else 1.0,
    )
    result = run_policy(scenario, "recovery")
    example = _example(scenario, result)
    example["profile"] = scenario["profile"]
    example["duration_stress"] = stress
    example["note"] = "A simulated day. Accepting the replan here does not change the theatre list."
    return example
