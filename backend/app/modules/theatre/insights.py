"""Research view of the theatre: one simulated day replanned by CP-SAT, and the precomputed experiment, duration
model and five-year simulation results that ship in data/. Nothing here reads or writes the live theatre list."""

import json
from functools import cache
from pathlib import Path

from .experiment.catalog import load_catalog
from .experiment.run import one_day

DATA = Path(__file__).resolve().parent / "data"


@cache
def _json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@cache
def _catalog() -> tuple[dict, dict]:
    return load_catalog()


def run_one_day(options: dict) -> dict:
    """Same contract as the POC's experiment.run.one_day; {"error": ...} when the seed is not a whole number."""
    return one_day(options, _catalog())


def experiment_summary() -> dict:
    return {"experiment": _json("experiment_summary.json"), "duration_model": _json("duration_model.json")}


def model_audit() -> dict:
    return {"model": _json("model.json"), "simulation": _json("sim_summary.json")}
