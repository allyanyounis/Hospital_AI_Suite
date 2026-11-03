"""One-off: record what the POC's board shows for its own day at 10:50 (now=650), so tests/test_theatre_engine.py can
check the ported planner gives the same numbers. Run from backend/ with the backend venv (needs numpy):

    python tools/theatre/golden.py [path/to/OperationTheater/poc]
"""

import json
import sys
from pathlib import Path

POC = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\haris\work\OperationTheater\poc")
OUT = Path(__file__).resolve().parents[2] / "tests" / "data" / "theatre_golden.json"
NOW = 650


def main() -> None:
    sys.path.insert(0, str(POC))
    import server  # the POC's server.py

    db = server.connect()
    board = server.board(db, NOW, None, with_proposals=True)

    def move(s):
        return None if not s else {"case": s["case"], "date": s["date"], "over_pct": s["after"]["over_pct"]}

    golden = {
        "now": NOW,
        "today": board["today"],
        "rooms": [
            {
                "code": room["id"],
                "finish": room["finish"],
                "forecast": room["forecast"],
                "cases": [
                    {
                        "case": c["id"],
                        "start": c["start"],
                        "end": c["end"],
                        "state": c["state"],
                        "risk": c["risk"],
                        "late_pct": c["late_pct"],
                        "latest": c["latest"],
                    }
                    for c in room["cases"]
                ],
                "suggestion": move(room["suggestion"]),
                "nudge": move(room["nudge"]),
            }
            for room in board["rooms"]
        ],
        "proposals": [
            {
                "case": p["case"],
                "slot": p["slot"],
                "before_over": p["before_over"],
                "after_over": p["after_over"],
                "pushed": [x["case"] for x in p["pushed"]],
                "move": p["move"] and p["move"]["case"],
            }
            for p in board["proposals"]
        ],
        "calendar_fit": server.calendar(db, "5-511.11")["days"][1]["rooms"][0].get("fit"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(golden, indent=1), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
