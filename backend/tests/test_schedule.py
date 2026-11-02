"""The shared clinic schedule: validation, saving, and the rules both modules rely on."""

from datetime import date, datetime

from app.schedule import ClinicSchedule, DaySchedule, default_schedule
from tests.conftest import login


def test_default_then_save_and_validate(client):
    login(client)
    default = client.get("/api/schedule").json()
    assert default["is_default"] and [d["enabled"] for d in default["days"]] == [True] * 5 + [False] * 2

    days = [{"enabled": i < 4, "start": "09:00", "end": "13:00", "breaks": []} for i in range(7)]
    days[0] = {"enabled": True, "start": "08:00", "end": "18:00", "breaks": [{"start": "12:30", "end": "13:30"}]}
    body = {"days": days, "slot_minutes": 20, "holidays": ["2026-12-25", "2026-12-24", "2026-12-25"]}
    saved = client.put("/api/schedule", json=body).json()
    assert not saved["is_default"] and saved["slot_minutes"] == 20
    assert saved["holidays"] == ["2026-12-24", "2026-12-25"]  # sorted, de-duplicated
    assert client.get("/api/schedule").json()["days"][0]["breaks"] == [{"start": "12:30", "end": "13:30"}]

    def rejected(day_index: int, **change) -> str:
        bad = [dict(d) for d in days]
        bad[day_index] = {**bad[day_index], **change}
        r = client.put("/api/schedule", json={**body, "days": bad})
        assert r.status_code == 422
        return r.text

    assert "Tuesday" in rejected(1, start="14:00", end="10:00")
    assert "inside working hours" in rejected(0, breaks=[{"start": "18:30", "end": "19:00"}])
    assert "must not overlap" in rejected(
        0, breaks=[{"start": "12:00", "end": "13:00"}, {"start": "12:30", "end": "14:00"}]
    )
    assert client.put("/api/schedule", json={**body, "days": days[:6]}).status_code == 422


def test_slot_grid_restarts_after_breaks():
    schedule = default_schedule()
    tuesday = date(2026, 11, 3)
    grid = [s.strftime("%H:%M") for s in schedule.slot_grid(tuesday)]
    assert grid[0] == "09:00" and "12:45" in grid and "13:00" not in grid and grid[grid.index("12:45") + 1] == "14:00"
    assert grid[-1] == "16:45" and len(grid) == 28


def test_after_hours_uses_clinic_schedule():
    hours = ClinicSchedule(days=[DaySchedule(enabled=i == 0, start="09:00", end="17:00") for i in range(7)])
    monday = datetime(2026, 11, 2)
    assert hours.is_working_time(monday.replace(hour=10))
    assert not hours.is_working_time(monday.replace(hour=18))
    assert not hours.is_working_time(datetime(2026, 11, 3, 10))  # Tuesday is a day off
