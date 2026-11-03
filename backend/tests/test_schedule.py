"""OPD scheduling: each doctor's week (validation, saving, rules) and the hospital's closed dates."""

from datetime import date, datetime

from app.modules.scheduling import DaySchedule, Schedule, default_schedule
from tests.conftest import login


def _doctor_id(client) -> int:
    [doctor] = client.get("/api/staff?bookable=true").json()
    return doctor["id"]


def test_default_then_save_and_validate(client):
    login(client, "admin")  # only admins edit schedules
    url = f"/api/schedules/{_doctor_id(client)}"
    default = client.get(url).json()
    assert default["is_default"] and [d["enabled"] for d in default["days"]] == [True] * 5 + [False] * 2

    days = [{"enabled": i < 4, "start": "09:00", "end": "13:00", "breaks": []} for i in range(7)]
    days[0] = {"enabled": True, "start": "08:00", "end": "18:00", "breaks": [{"start": "12:30", "end": "13:30"}]}
    body = {"days": days, "slot_minutes": 20}
    saved = client.put(url, json=body).json()
    assert not saved["is_default"] and saved["slot_minutes"] == 20
    assert client.get(url).json()["days"][0]["breaks"] == [{"start": "12:30", "end": "13:30"}]
    assert client.put(url, json=body).status_code == 200  # saving again replaces the week

    def rejected(day_index: int, **change) -> str:
        bad = [dict(d) for d in days]
        bad[day_index] = {**bad[day_index], **change}
        r = client.put(url, json={**body, "days": bad})
        assert r.status_code == 422
        return r.text

    assert "Tuesday" in rejected(1, start="14:00", end="10:00")
    assert "inside working hours" in rejected(0, breaks=[{"start": "18:30", "end": "19:00"}])
    assert "must not overlap" in rejected(
        0, breaks=[{"start": "12:00", "end": "13:00"}, {"start": "12:30", "end": "14:00"}]
    )
    assert client.put(url, json={**body, "days": days[:6]}).status_code == 422
    assert client.get("/api/schedules/999").status_code == 404  # not a bookable doctor


def test_hospital_closures_are_sorted_and_deduplicated(client):
    login(client, "admin")
    closures = [{"date": "2026-12-25", "reason": "Christmas"}, {"date": "2026-12-24"}, {"date": "2026-12-25"}]
    saved = client.put("/api/closures", json={"closures": closures}).json()
    assert [c["date"] for c in saved] == ["2026-12-24", "2026-12-25"]
    client.post("/api/logout")
    login(client)  # doctors can read them, not change them
    assert len(client.get("/api/closures").json()) == 2
    assert client.put("/api/closures", json={"closures": []}).status_code == 403


def test_slot_grid_restarts_after_breaks():
    schedule = default_schedule()
    tuesday = date(2026, 11, 3)
    grid = [s.strftime("%H:%M") for s in schedule.slot_grid(tuesday)]
    assert grid[0] == "09:00" and "12:45" in grid and "13:00" not in grid and grid[grid.index("12:45") + 1] == "14:00"
    assert grid[-1] == "16:45" and len(grid) == 28


def test_after_hours_uses_the_doctors_schedule():
    hours = Schedule(days=[DaySchedule(enabled=i == 0, start="09:00", end="17:00") for i in range(7)])
    monday = datetime(2026, 11, 2)
    assert hours.is_working_time(monday.replace(hour=10))
    assert not hours.is_working_time(monday.replace(hour=18))
    assert not hours.is_working_time(datetime(2026, 11, 3, 10))  # Tuesday is a day off
