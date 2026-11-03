"""One-off: export the Operation Theatre POC's synthetic hospital (poc/hospital.db) to
app/modules/theatre/data/demo.json, the data behind `python -m app seed demo-theatre`.

Dates become day offsets from the POC's "today", so the demo can be replayed in any week. Run from backend/:

    python tools/theatre/export_poc.py [path/to/hospital.db]
"""

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

POC_DB = Path(r"C:\Users\haris\work\OperationTheater\poc\hospital.db")
OUT = Path(__file__).resolve().parents[2] / "app" / "modules" / "theatre" / "data" / "demo.json"

LAB_CODES = {
    "Haemoglobin": "HGB",
    "White cells": "WBC",
    "Platelets": "PLT",
    "Sodium": "NA",
    "Potassium": "K",
    "Creatinine": "CREA",
    "Glucose": "GLU",
    "Albumin": "ALB",
    "INR": "INR",
}
VITALS = {"Heart rate": "heart_rate", "Systolic BP": "systolic_bp", "SpO2": "spo2", "Temperature": "temperature_c"}
HISTORY = {"Indication": "indication", "Condition": "condition", "Surgery": "surgery"}
REPORTS = {
    "Ultrasound": "ultrasound",
    "ECG": "ecg",
    "X-ray": "xray",
    "Anaesthesia review": "anaesthesia_review",
    "Mammography": "mammography",
    "Pathology": "pathology",
    "CT sinuses": "ct",
    "Echocardiogram": "echo",
    "Coronary angiogram": "angiogram",
}
DEPARTMENTS = {
    "General": ("GSURG", "General Surgery"),
    "Trauma": ("TRAUMA", "Trauma & Orthopaedics"),
    "Gyn & Obstetrics": ("OBGYN", "Obstetrics & Gynaecology"),
    "Otolaryngology": ("ENT", "ENT (Otolaryngology)"),
    "Cardiac": ("CARDSURG", "Cardiac Surgery"),
}


def main() -> None:
    db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else POC_DB)
    db.row_factory = sqlite3.Row
    today = date.fromisoformat(db.execute("select value from meta where key='today'").fetchone()[0])

    def offset(day: str | None) -> int | None:
        return None if day is None else (date.fromisoformat(day) - today).days

    rooms = [dict(r) for r in db.execute("select * from rooms order by id")]
    procedures = [dict(r) for r in db.execute("select * from procedures order by specialty, code")]
    surgeons = []
    for s in db.execute("select * from surgeons order by id"):  # text order (S1, S10, S2…), as the POC iterates them
        surname = s["name"].split()[-1].lower()
        surgeons.append(
            {
                "key": s["id"],
                "username": f"dr{surname}",
                "name": s["name"],
                "specialty": s["specialty"],
                "active": bool(s["active"]),
                "days": [
                    [r["weekday"], r["start"], r["end"]]
                    for r in db.execute("select * from surgeon_days where surgeon_id=? order by weekday", (s["id"],))
                ],
                "leave": [
                    [offset(r["start_day"]), offset(r["end_day"]), r["reason"]]
                    for r in db.execute("select * from surgeon_leave where surgeon_id=? order by id", (s["id"],))
                ],
            }
        )

    patients = []
    for p in db.execute("select * from patients order by id"):
        labs, vitals = [], {}
        for r in db.execute("select * from labs where patient_id=? order by day, rowid", (p["id"],)):
            if r["test"] in VITALS:
                vitals.setdefault(r["day"], {})[VITALS[r["test"]]] = r["value"]
            else:
                labs.append([offset(r["day"]), LAB_CODES[r["test"]], r["value"]])
        history, reports = [], []
        for r in db.execute("select * from records where patient_id=? order by day, rowid", (p["id"],)):
            if r["kind"] in HISTORY:
                history.append([offset(r["day"]), HISTORY[r["kind"]], r["text"]])
            else:
                reports.append([offset(r["day"]), REPORTS[r["kind"]], r["kind"], r["text"]])
        patients.append(
            {
                "key": p["id"],
                "name": p["name"],
                "sex": {"F": "Female", "M": "Male"}.get(p["sex"], ""),
                "age": p["age"],
                "allergies": "" if p["allergies"] == "None known" else p["allergies"],
                "labs": labs,
                "vitals": [{"day": offset(day), **values} for day, values in sorted(vitals.items())],
                "history": history,
                "reports": reports,
                # pre-op data of the patient's case(s)
                "asa": p["asa"],
                "weight_kg": p["weight_kg"],
                "height_cm": p["height_cm"],
                "cardiac": json.loads(p["cardiac"]) if p["cardiac"] else None,
            }
        )

    cases = [
        {
            "key": c["id"],
            "patient": c["patient_id"],
            "code": c["code"],
            "room": c["room"],
            "day": offset(c["day"]),
            "seq": c["seq"],
            "urgency": c["urgency"].lower(),
            "overrun": c["overrun"],
            "surgeon": c["surgeon_id"],
            "deferred": bool(c["deferred"]),
        }
        for c in db.execute("select * from cases order by id")
    ]

    demo = {
        "source": "OperationTheater POC synthetic hospital (poc/seed_db.py); days are offsets from 'today'",
        "today": today.isoformat(),
        "departments": {k: list(v) for k, v in DEPARTMENTS.items()},
        "rooms": rooms,
        "procedures": procedures,
        "surgeons": surgeons,
        "patients": patients,
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(demo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUT} ({len(patients)} patients, {len(cases)} cases, {len(surgeons)} surgeons)")


if __name__ == "__main__":
    main()
