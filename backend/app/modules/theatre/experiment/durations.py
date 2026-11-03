"""Planned and realized room time for the experiment.

Occupancy here is the sum of the five German in-room intervals already used
by the theatre list and by catalog.py. Turnover is not included.
There is no trained occupancy model: no file on disk has both OR entry and
OR exit. predict_minutes stays unavailable until that changes.
"""

from __future__ import annotations

from random import Random

from .catalog import sample_room_minutes

LABEL = {
    "source": "synthetic",
    "target": "or_occupancy_synthetic",
    "calibration": "German 2019 specialized inpatient process distributions",
    "definition": "induction + surgical lead-in + incision-to-closure + surgical lead-out + emergence",
    "turnover": "separate, German OR cleaning mean, not part of occupancy",
}


def planned_minutes(procedure: dict) -> int:
    """Published mean occupancy. `procedure` is one entry from catalog.load_catalog."""
    return int(procedure["expected"])


def draw_minutes(procedure: dict, rng: Random) -> int:
    """One realized occupancy, same parameterization as the five-year scenario."""
    return sample_room_minutes(procedure["steps"], rng)


def predict_minutes(case: dict) -> int:
    """Hook for a future model. Refuses to invent an occupancy prediction."""
    raise RuntimeError(
        "No occupancy model is available. No downloaded dataset has both an OR-entry "
        "and an OR-exit timestamp. Use planned_minutes and draw_minutes."
    )
