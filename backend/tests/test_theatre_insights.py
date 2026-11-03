"""Theatre insights: the ported CP-SAT experiment reproduces the POC's seeded day, and the precomputed research
results load. Expected numbers were captured by running the POC's experiment.run.one_day on the same seed."""

import pytest

from app.modules.theatre.insights import experiment_summary, model_audit, run_one_day

DAY_KEYS = {
    "seed",
    "disruption",
    "provenance",
    "weights",
    "rooms",
    "recovery_beds",
    "original",
    "revised",
    "changes",
    "recovery",
    "no_replan",
    "solver",
    "fallback",
    "events",
    "profile",
    "duration_stress",
    "note",
}
METRICS = {
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
}


@pytest.fixture(scope="module")
def day():
    return run_one_day({"seed": 20261101})


def test_one_day_has_the_poc_shape(day):
    assert set(day) == DAY_KEYS
    assert set(day["recovery"]) == METRICS and set(day["no_replan"]) == METRICS
    assert {"case_id", "room_id", "start_min", "end_min", "status", "surgeon_id"} <= set(day["original"][0])
    assert [room["id"] for room in day["rooms"]] == ["OR 1", "OR 1B", "OR 2", "OR 3", "OR 4"]


def test_one_day_matches_the_poc_for_the_default_seed(day):
    assert day["seed"] == 20261101
    assert day["events"] == [{"type": "emergency", "at": 630}]
    assert day["solver"] == "cp-sat" and day["fallback"] is False and day["profile"] == "balanced"
    assert (len(day["original"]), len(day["revised"]), len(day["changes"])) == (21, 22, 6)
    assert day["recovery"]["overtime_min"] == 88 and day["recovery"]["weighted_cost"] == 3795
    assert day["no_replan"]["overtime_min"] == 226 and day["no_replan"]["weighted_cost"] == 4503
    assert day["recovery"]["violations"] == 0


def test_bad_seed_is_an_error():
    assert run_one_day({"seed": "tomorrow"}) == {"error": "The seed needs to be a whole number."}


def test_experiment_summary_and_model_audit_load():
    summary = experiment_summary()
    assert set(summary) == {"experiment", "duration_model"}
    assert {"metrics", "paired", "example", "definitions"} <= set(summary["experiment"])
    audit = model_audit()
    assert set(audit) == {"model", "simulation"}
    assert audit["model"] and audit["simulation"]
