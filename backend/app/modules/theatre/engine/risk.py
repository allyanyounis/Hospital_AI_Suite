"""Risk of a bad outcome for one case.

Non-cardiac operations: a logistic model trained on 6,386 VitalDB cases (ICU stay or death in hospital; coefficients
in data/model.json). Cardiac operations: EuroSCORE II predicted in-hospital mortality (Nashef et al., Eur J
Cardiothorac Surg 2012). Missing labs fall back to the training median.
"""

from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path

from .snapshot import Case, Person, Proc

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "model.json"
EMERGENCY = ("immediate", "urgent")
LAB_FOR_FEATURE = {"preop_hb": "HGB", "preop_plt": "PLT", "preop_alb": "ALB", "preop_cr": "CREA"}
EURO_URGENCY = {
    "elective": ("elective", 0),
    "expedited": ("urgent", 0.3174673),
    "urgent": ("emergency", 0.7039121),
    "immediate": ("emergency", 0.7039121),
}
EUROSCORE_AVERAGE = 3.9  # mortality in the EuroSCORE II development cohort


@cache
def model() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def risk(person: Person, case: Case, proc: Proc, anaesthesia_min: int, urgency: str) -> dict:
    if proc.risk_model == "euroscore2":
        return euroscore(person, case, proc, urgency)
    m = model()
    values = {
        "age": person.age,
        "asa": case.asa,
        "emop": 1 if urgency in EMERGENCY else 0,
        "anesthesia_h": anaesthesia_min / 60,
    }
    values.update({name: person.labs.get(code) for name, code in LAB_FOR_FEATURE.items()})
    score = m["intercept"]
    factors = []
    for feature in m["features"]:
        value = values[feature["name"]]
        if value is None:
            value = feature["median"]
        push = feature["coef"] * (value - feature["mean"]) / feature["sd"]
        score += push
        digits = 1 if feature["unit"] == "h" else 2
        factors.append(
            {"label": feature["label"], "value": round(value, digits), "unit": feature["unit"], "push": round(push, 2)}
        )
    factors.sort(key=lambda f: -abs(f["push"]))
    return {
        "pct": round(100 / (1 + math.exp(-score))),
        "factors": factors[:3],
        "model": "VitalDB",
        "outcome": "ICU stay or death in hospital",
        "average": m["base_rate_pct"],
    }


def euroscore(person: Person, case: Case, proc: Proc, urgency: str) -> dict:
    c = case.cardiac or {}
    age, female = person.age, person.sex == "F"
    weight = case.weight_kg or 75
    clearance = (140 - age) * weight * (0.85 if female else 1) / (72 * (person.labs.get("CREA") or 1.0))
    lvef, pa = c.get("lvef") or 60, c.get("pa_systolic") or 25
    kidney = 0.6421508 if c.get("dialysis") else 0.8592256 if clearance <= 50 else 0.303553 if clearance <= 85 else 0
    lv = 0.9346919 if lvef <= 20 else 0.8084096 if lvef <= 30 else 0.3150652 if lvef <= 50 else 0
    terms = [
        ("Age", f"{age} y", 0.0285181 * max(1, age - 59)),
        ("Female", "", 0.2196434 * female),
        ("Kidney", "dialysis" if c.get("dialysis") else f"CrCl {round(clearance)} mL/min", kidney),
        ("Arteriopathy", "", 0.5360268 * c.get("arteriopathy", 0)),
        ("Poor mobility", "", 0.2407181 * c.get("poor_mobility", 0)),
        ("Redo surgery", "", 1.118599 * c.get("redo", 0)),
        ("Chronic lung disease", "", 0.1886564 * c.get("lung", 0)),
        ("Active endocarditis", "", 0.6194522 * c.get("endocarditis", 0)),
        ("Critical state", "", 1.086517 * c.get("critical", 0)),
        ("Diabetes on insulin", "", 0.3542749 * c.get("iddm", 0)),
        ("NYHA class", str(c.get("nyha") or 1), {2: 0.1070545, 3: 0.2958358, 4: 0.5597929}.get(c.get("nyha"), 0)),
        ("CCS 4 angina", "", 0.2226147 * c.get("ccs4", 0)),
        ("LV function", f"EF {lvef}%", lv),
        ("Recent MI", "", 0.1528943 * c.get("recent_mi", 0)),
        ("PA pressure", f"{pa} mmHg", 0.3491475 if pa >= 55 else 0.1788899 if pa > 30 else 0),
        ("Urgency", EURO_URGENCY[urgency][0], EURO_URGENCY[urgency][1]),
        ("Procedure", proc.title.split(" (")[0], {1: 0.0062118, 2: 0.5521478, 3: 0.9724533}.get(proc.euro_weight, 0)),
        ("Thoracic aorta", "", 0.6527205 * bool(proc.aorta)),
    ]
    score = -5.324537 + sum(t[2] for t in terms)
    factors = sorted(
        ({"label": label, "value": value, "unit": "", "push": round(push, 2)} for label, value, push in terms if push),
        key=lambda f: -f["push"],
    )
    return {
        "pct": round(100 / (1 + math.exp(-score)), 1),
        "factors": factors[:3],
        "model": "EuroSCORE II",
        "outcome": "Death in hospital",
        "average": EUROSCORE_AVERAGE,
    }
