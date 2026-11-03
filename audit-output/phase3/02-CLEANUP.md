# PHASE 3 — DELIVERABLE 02: WORKSPACE SCRIPTS INVENTORY & CLEANUP PLAN

**Author:** Antigravity Principal Technical Lead & DevOps Auditor  
**Date:** November 1, 2026  
**Status:** Prepared for User Approval  

---

## 1. Scratch & Helper Script Inventory

A total of 30 ad-hoc scripts were generated across Phase 1 and Phase 2 in the workspace scratch repository (`<appDataDir>/brain/<conversation-id>/scratch/`). Below is the complete catalog with categorization:

### 1.1 Reusable Engineering Tools (Migrated to `scripts/audit/`)
These scripts provide enduring diagnostic and auditing utility for ongoing development, database verification, and architectural discovery. They have been organized under [`scripts/audit/`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/scripts/audit):

| Script Path | Purpose | Reusability Justification |
| :--- | :--- | :--- |
| `scripts/audit/diff_dbs.py` | Compares SQLite database schemas, tables, and row counts | Essential for ensuring the working database does not drift from or corrupt original state. |
| `scripts/audit/check_imports.py` | Scans codebase for all third-party package imports | Verifies `requirements.txt` coverage against real source code AST. |
| `scripts/audit/inspect_db.py` | Inspects SQLite schema tables and PRAGMA table info | Fast CLI inspection of SQLite database structure. |
| `scripts/audit/inspect_models.py` | Catalogs SQLAlchemy models, columns, and relationships | Useful for architectural discovery and schema verification. |
| `scripts/audit/inspect_routes.py` | Catalogs registered Flask endpoints, URLs, and HTTP methods | Verifies application route surface and endpoint availability. |
| `scripts/audit/capture_screenshots.py` | Automates authenticated Edge CDP browser screenshots | High-fidelity, cookie-authenticated visual verification runner. |

---

### 1.2 Obsolete / One-Off Scratch Scripts (Proposed for Deletion)
The following 25 files are temporary debug helpers, intermediate runner drafts, or ad-hoc troubleshooting scripts that have served their diagnostic purpose and are no longer needed:

| Script Name | Size | Original One-Off Purpose | Proposed Action |
| :--- | :-: | :--- | :-: |
| `check_booking_form.py` | 1,016 B | Tested booking form field parsing | **Delete** |
| `check_creds.py` | 1,222 B | Checked seeded database user credentials | **Delete** |
| `check_doc_reg.py` | 978 B | Tested doctor registration validation rules | **Delete** |
| `check_fe01.py` | 397 B | Counted navbar container divs in `base.html` | **Delete** |
| `check_fixture_err.py` | 1,404 B | Diagnosed pytest test fixture setup | **Delete** |
| `check_gemini.py` | 863 B | Ad-hoc test of Google Gemini API key response | **Delete** |
| `check_reg_errors.py` | 1,026 B | Inspected registration WTForms validation errors | **Delete** |
| `check_tz.py` | 697 B | Inspected Python datetime timezone offsets | **Delete** |
| `check_users_pass.py` | 855 B | Tested Werkzeug password hashing on seed users | **Delete** |
| `get_traceback.py` | 369 B | Captured stack trace for `/doctors` 500 error | **Delete** |
| `get_traceback2.py` | 312 B | Captured stack trace for prescription 500 error | **Delete** |
| `inspect_form.py` | 664 B | Dumped form fields for AppointmentBookingForm | **Delete** |
| `inspect_routes_code.py`| 1,037 B | AST parser inspecting route decorators | **Delete** |
| `list_routes.py` | 515 B | Formatted route list helper | **Delete** |
| `master_runner.py` | 28,324 B| Phase 2 monolithic live test runner | **Delete** |
| `run_full_lifecycle_test.py`| 20,185 B| Intermediate draft of full lifecycle runner | **Delete** |
| `run_live_audit_part1.py`| 6,846 B | Intermediate draft of live audit part 1 | **Delete** |
| `run_live_audit_part2.py`| 5,416 B | Intermediate draft of live audit part 2 | **Delete** |
| `test_ai_service.py` | 795 B | Ad-hoc test of AI chatbot service | **Delete** |
| `test_booking_flow.py` | 2,430 B| Ad-hoc script testing doctor booking | **Delete** |
| `test_doc1_book.py` | 1,171 B| Ad-hoc script testing booking for doctor 1 | **Delete** |
| `test_doc1_booking.py` | 1,097 B| Ad-hoc script testing booking for doctor 1 | **Delete** |
| `test_doc9_booking.py` | 2,270 B| Ad-hoc script testing booking for doctor 9 | **Delete** |
| `test_screenshot.py` | 888 B | Initial headless Edge screenshot experiment | **Delete** |
| `test_socketio_client.py`| 1,053 B| Ad-hoc script testing Socket.IO client polling | **Delete** |

*Note: Per master instructions, these files will only be deleted after user approval.*

---

## 2. Pytest Configuration & Test Scope Enforcement

To prevent pytest from collecting or executing scratch or test files outside the official test suite, a root configuration file [`pytest.ini`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/pytest.ini) was implemented:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v
```

### Verification
Executing `pytest` confirms that test discovery strictly collects exclusively from `tests/`:
- **Collected:** 23 test cases (across `test_appointments.py`, `test_auth.py`, `test_chat.py`, `test_prescriptions.py`, `test_refunds.py`, `test_security.py`).
- **Zero test files** outside `tests/` are collected.
- **Execution baseline:** 20 Passed, 3 xfailed (`ISS-BUG-01`, `ISS-SEC-01`, `ISS-SEC-03`), 0 Failed.

