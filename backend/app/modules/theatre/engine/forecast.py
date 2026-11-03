"""Monte Carlo forecast of one room's day: each case length is drawn from a lognormal with the operation's published
mean and variance, and the room is played DRAWS times. The seed is fixed, so the same list gives the same numbers."""

from __future__ import annotations

import math

import numpy as np

DAY_OPEN = 8 * 60
DAY_CLOSE = 16 * 60
DRAWS = 2000
Z90 = 1.2815515655446004


def lognormal(mean: float, variance: float) -> tuple[float, float]:
    sigma2 = math.log(1 + variance / mean**2)
    return math.log(mean) - sigma2 / 2, math.sqrt(sigma2)


def p90_minutes(mean: float, variance: float) -> float:
    mu, sigma = lognormal(mean, variance)
    return math.exp(mu + Z90 * sigma)


def simulate(cases: list[dict], cleaning: int, now: int) -> dict:
    """Play the room DRAWS times. Started cases keep their start; one in theatre is still running at `now`.

    Each case is a dict with planned_min, variance, overrun, state ("done", "in" or "wait"), booked, start and end.
    Waiting cases get late_pct and delay_min; the one in theatre gets remain_min, extra_min, overrun_pct and
    finish_p90 (written into the dicts).
    """
    rng = np.random.default_rng(7)
    clock = np.full(DRAWS, float(DAY_OPEN))
    for case in cases:
        mu, sigma = lognormal(case["planned_min"], case["variance"])
        length = rng.lognormal(mu, sigma, DRAWS) + case["overrun"]
        if case["state"] == "wait":
            start = np.maximum(clock, now)
            case["late_pct"] = round(100 * float((start - case["booked"] > 30).mean()))
            case["delay_min"] = round(float(np.maximum(start - case["booked"], 0).mean()))
        else:
            start = np.full(DRAWS, float(case["start"]))
            if case["state"] == "in":
                length = np.maximum(length, now - case["start"] + 1)
                finish_case = start + length
                case["remain_min"] = round(float(np.maximum(finish_case - now, 0).mean()))
                case["extra_min"] = round(float(np.maximum(finish_case - case["end"], 0).mean()))
                case["overrun_pct"] = round(100 * float((finish_case > case["end"] + 0.5).mean()))
                case["finish_p90"] = round(float(np.quantile(finish_case, 0.9)))
            else:
                length = np.full(DRAWS, float(case["end"] - case["start"]))
        clock = start + length + cleaning
    finish = clock - cleaning
    over = np.maximum(finish - DAY_CLOSE, 0)
    return {
        "over_pct": round(100 * float((over > 0).mean())),
        "expected_over": round(float(over.mean())),
        "finish_p90": round(float(np.quantile(finish, 0.9))),
    }


EMPTY = {"over_pct": 0, "expected_over": 0, "finish_p90": DAY_OPEN}
