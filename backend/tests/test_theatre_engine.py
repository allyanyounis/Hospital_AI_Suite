"""The ported planner gives the POC's answers on the POC's own data (tests/data/theatre_golden.json, recorded by
tools/theatre/golden.py from the POC server at 10:50 on its day). Pure functions: no database."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.modules.theatre.demo import anchor_for, demo_snapshot, split_allergies
from app.modules.theatre.engine import planner
from app.modules.theatre.engine.snapshot import Leave

GOLDEN = json.loads((Path(__file__).parent / "data" / "theatre_golden.json").read_text(encoding="utf-8"))


@pytest.fixture
def snap():
    return demo_snapshot()[0]


@pytest.fixture
def key_of():
    _, ids = demo_snapshot()
    by_id = {}
    for key, value in ids.items():
        by_id.setdefault(key[0], {})[value] = key  # "C" -> case id -> "C07", "S" -> surgeon, "O" -> room
    return lambda kind, value: by_id[kind].get(value)


def test_board_matches_the_poc(snap, key_of):
    board = planner.board(snap, GOLDEN["now"], with_proposals=True)
    assert board["today"].isoformat() == GOLDEN["today"]
    for room, gold in zip(board["rooms"], GOLDEN["rooms"], strict=True):
        assert room["code"] == gold["code"]
        assert room["finish"] == gold["finish"]
        for k in ("over_pct", "expected_over", "finish_p90"):
            assert abs(room["forecast"][k] - gold["forecast"][k]) <= 1, (room["code"], k)
        got = [
            {"case": key_of("C", c["id"]), **{k: c[k] for k in ("start", "end", "state", "risk", "late_pct", "latest")}}
            for c in room["cases"]
        ]
        assert got == gold["cases"]
        for tip in ("suggestion", "nudge"):
            mine, theirs = room[tip], gold[tip]
            assert (mine is None) == (theirs is None), (room["code"], tip)
            if mine:
                assert key_of("C", mine["case"]) == theirs["case"]
                assert mine["date"].isoformat() == theirs["date"]
                assert mine["after"]["over_pct"] == theirs["over_pct"]


def test_emergency_proposals_match_the_poc(snap, key_of):
    proposals = planner.board(snap, GOLDEN["now"], with_proposals=True)["proposals"]
    assert [key_of("C", p["case"]) for p in proposals] == [p["case"] for p in GOLDEN["proposals"]]
    for mine, gold in zip(proposals, GOLDEN["proposals"], strict=True):
        slot = {**mine["slot"], "day": mine["slot"]["day"].isoformat(), "room": key_of("O", mine["slot"]["room"])}
        assert slot == gold["slot"]
        assert (mine["before_over"], mine["after_over"]) == (gold["before_over"], gold["after_over"])
        assert [key_of("C", x["case"]) for x in mine["pushed"]] == gold["pushed"]
        assert (mine["move"] and key_of("C", mine["move"]["case"])) == gold["move"]


def test_proposals_leave_the_list_unchanged(snap):
    before = {c.id: c.stored() for c in snap.cases.values()}
    planner.board(snap, GOLDEN["now"], with_proposals=True)
    assert {c.id: c.stored() for c in snap.cases.values()} == before


def test_calendar_fit_matches_the_poc(snap, key_of):
    week = planner.calendar(snap, snap.today, "5-511.11")
    fit = week["days"][1]["rooms"][0]["fit"]
    gold = GOLDEN["calendar_fit"]
    assert fit["day"].isoformat() == gold["day"]
    assert (fit["start"], fit["end"], key_of("S", fit["surgeon_id"])) == (
        gold["start"],
        gold["end"],
        gold["surgeon_id"],
    )


def test_started_cases_stay_and_only_the_running_case_overruns(snap):
    board = planner.board(snap, GOLDEN["now"])
    rows = [c for room in board["rooms"] for c in room["cases"]]
    running = next(c for c in rows if c["state"] == "in")
    done = next(c for c in rows if c["state"] == "done")
    waiting = next(c for c in rows if c["state"] == "wait")
    assert planner.act(snap, done["id"], "later", GOLDEN["now"]) == "This case has started. It stays where it is."
    assert planner.act(snap, waiting["id"], "overrun", GOLDEN["now"]) == "Only the case in theatre can run long."
    assert planner.act(snap, running["id"], "overrun", GOLDEN["now"], minutes=30) is None
    assert snap.cases[running["id"]].overrun == running["overrun"] + 30


def test_defer_and_intake_preview(snap):
    board = planner.board(snap, GOLDEN["now"])
    tip = next(room["suggestion"] for room in board["rooms"] if room["suggestion"])
    trial = snap.copy()
    assert planner.defer(trial, tip["case"], tip["date"]) is None
    assert trial.cases[tip["case"]].deferred and trial.cases[tip["case"]].day == tip["date"]
    assert planner.defer(trial, tip["case"], snap.today) == "Pick a date after today."

    waiting = next(c for c in snap.cases.values() if c.day is None and c.urgency == "urgent")
    preview = planner.intake(snap.copy(), {"case_id": waiting.id}, GOLDEN["now"])
    assert preview["slot"]["day"] == snap.today and "with_moves" in preview
    assert snap.cases[waiting.id].day is None  # the preview worked on a copy


def test_new_patient_case_and_validation(snap):
    assert planner.create_case(snap, {"procedure_code": "nope"}) == ("Choose an operation.", None)
    error, _ = planner.create_case(snap, {"procedure_code": "5-511.11", "patient": {"name": "X"}})
    assert error == "Enter the patient's name and age."
    error, case_id = planner.create_case(
        snap, {"procedure_code": "5-511.11", "patient": {"name": "New Person", "age": 50, "sex": "Female"}}
    )
    assert error is None and case_id < 0 and snap.cases[case_id].day is None
    assert snap.new_patients[snap.cases[case_id].patient_id]["full_name"] == "New Person"


def test_leave_lists_conflicts_with_cover(snap, key_of):
    surgeon = next(s for s in snap.surgeons.values() if key_of("S", s.id) == "S1")
    day = next(c.day for c in snap.cases.values() if c.surgeon_id == surgeon.id and c.day and c.day > snap.today)
    surgeon.leave.append(Leave(99, day, day, "Sick"))
    conflicts = planner.leave_conflicts(snap, surgeon.id, day, day)
    assert conflicts and all(c["day"] == day for c in conflicts)


def test_demo_helpers():
    assert split_allergies("Penicillin (rash), Latex") == [("Penicillin", "rash"), ("Latex", None)]
    poc_today = date(2026, 11, 2)  # a Monday
    for offset in range(-6, 7):
        today = poc_today + timedelta(days=offset)
        anchor = anchor_for(today)
        assert anchor.weekday() == poc_today.weekday() and abs((anchor - today).days) <= 3
