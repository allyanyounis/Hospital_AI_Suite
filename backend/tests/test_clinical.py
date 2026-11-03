"""Clinical data API: the chart summary, paged histories, series, reports, and who may read them."""

from app.core.clock import now_local
from app.core.database import session_scope
from app.modules.auth.cli import save_user
from app.modules.patients import Patient
from app.modules.theatre import seed_demo
from tests.conftest import PASSWORD, login


def _demo_patient(mrn="DEMO-P01") -> int:
    with session_scope() as db:
        seed_demo(db, now_local().date())
    with session_scope() as db:
        return db.query(Patient).filter_by(mrn=mrn).one().id


def test_summary_has_latest_labs_with_trend_vitals_and_allergies(client):
    patient_id = _demo_patient("DEMO-P03")  # Ahmed Yilmaz: penicillin allergy
    login(client)
    s = client.get(f"/api/clinical/patients/{patient_id}/summary").json()
    labs = {lab["test"]: lab for lab in s["labs"]}
    assert set(labs) == {"HGB", "WBC", "PLT", "NA", "K", "CREA", "GLU", "ALB", "INR"}
    hgb = labs["HGB"]
    assert hgb["previous"] is not None and hgb["trend"] in ("up", "down", "same")
    assert s["out_of_range"] == sum(1 for lab in s["labs"] if lab["flag"] != "normal")
    assert s["vitals"]["heart_rate"] and s["previous_vitals"]
    assert [a["substance"] for a in s["allergies"]] == ["Penicillin"]
    assert s["report_counts"] and s["history_count"] > 0


def test_lab_history_pages_without_gaps_or_repeats(client):
    patient_id = _demo_patient()
    login(client)
    seen, cursor = [], ""
    while True:
        page = client.get(f"/api/clinical/patients/{patient_id}/labs", params={"limit": 5, "cursor": cursor}).json()
        seen += [r["id"] for r in page["items"]]
        if not (cursor := page["next_cursor"]):
            break
    every = client.get(f"/api/clinical/patients/{patient_id}/labs", params={"limit": 200}).json()
    assert seen == [r["id"] for r in every["items"]] and len(seen) == len(set(seen)) > 5
    times = [r["collected_at"] for r in every["items"]]
    assert times == sorted(times, reverse=True)

    hgb = client.get(f"/api/clinical/patients/{patient_id}/labs", params={"test": "hgb"}).json()["items"]
    assert hgb and {r["test"] for r in hgb} == {"HGB"}
    series = client.get(f"/api/clinical/patients/{patient_id}/labs/series", params={"test": "HGB"}).json()
    assert [p["value"] for p in series] == [r["value"] for r in reversed(hgb)]
    assert client.get(f"/api/clinical/patients/{patient_id}/labs", params={"cursor": "junk"}).status_code == 422


def test_vitals_reports_and_history(client):
    patient_id = _demo_patient()
    login(client)
    vitals = client.get(f"/api/clinical/patients/{patient_id}/vitals").json()["items"]
    assert vitals and all("flags" in v for v in vitals)
    reports = client.get(f"/api/clinical/patients/{patient_id}/reports").json()["items"]
    assert reports and "body" not in reports[0]
    full = client.get(f"/api/clinical/reports/{reports[0]['id']}").json()
    assert full["body"].startswith(full["excerpt"].rstrip("…"))
    only = client.get(f"/api/clinical/patients/{patient_id}/reports", params={"kind": reports[0]["kind"]}).json()
    assert {r["kind"] for r in only["items"]} == {reports[0]["kind"]}
    assert client.get(f"/api/clinical/patients/{patient_id}/reports", params={"kind": "tarot"}).status_code == 422
    history = client.get(f"/api/clinical/patients/{patient_id}/history").json()
    assert {h["kind"] for h in history} <= {"indication", "condition", "surgery"}
    assert client.get("/api/clinical/patients/999999/summary").status_code == 404
    assert len(client.get("/api/clinical/lab-tests").json()) == 9


def test_front_desk_cannot_read_clinical_data(client):
    patient_id = _demo_patient()
    save_user("desk", "Front Desk", "receptionist", PASSWORD)
    login(client, "desk")
    assert client.get(f"/api/clinical/patients/{patient_id}/summary").status_code == 403
    assert client.get("/api/theatre/board").status_code == 200  # theatre lists are for all staff
