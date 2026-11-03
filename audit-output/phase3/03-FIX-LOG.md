# PHASE 3 — DELIVERABLE 03: DEFECT RESOLUTION & BUG FIX LOG

**Author:** Antigravity Principal Technical Lead & DevOps Auditor  
**Date:** November 1, 2026  
**Branch:** `phase-3-bugfix`  
**Base Commit:** `203547f` (Clean checkout)  
**Verification Environment:** Windows 10/11 | Python 3.11.9 | SQLite  

---

## 1. Executive Summary

During Phase 3, 9 authorized code modifications, defect corrections, and security hardening fixes were implemented using a strict Test-Driven Development (TDD) cycle:
1. Formulate and execute a targeted failing test case.
2. Implement the smallest focused code modification.
3. Validate test passage and verify zero regressions across the full pytest suite.
4. Commit each change as an atomic git commit following the standard `fix(SCOPE): description` convention.

The original development database (`instance/quickcare_dev.db`) was completely isolated and verified byte-for-byte unchanged across all phases.

---

## 2. Comprehensive Defect Resolution Register

### 2.1 NEW-BUG-01: Public `/doctors` Route HTTP 500 Crash
- **Defect Description:** Navigating to `GET /doctors` raised `TypeError: object of type 'QueryPagination' has no len()` inside Jinja template rendering of `patients/doctors_list.html`.
- **Root Cause:** `app/routes/home.py:doctors` queried `Doctor.query.paginate(...)` and passed the pagination object directly to a template expecting a materialized list with `.len()`, duplicating the dedicated `/patients/find-doctors` search interface.
- **TDD Test Case:** [`tests/test_home.py:test_public_doctors_route_redirect_new_bug_01`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_home.py#L6)
- **Fix Applied:** Modified `home.py:doctors` to issue an HTTP 302 redirect to `patients.find_doctors` (`/patients/find-doctors`), matching patient discovery architecture.
- **Commit:** `ac44ee5` — `fix(NEW-BUG-01): redirect public doctors route to find-doctors directory`

---

### 2.2 ISS-BUG-01: Unauthenticated Prescription Access
- **Defect Description:** Unauthenticated requests to `/prescriptions/view/<id>` or `/prescriptions/download/<id>` crashed with `AttributeError: 'NoneType' object has no attribute 'role'` instead of prompting the user to sign in.
- **Root Cause:** Neither endpoint had `@login_required` decoration. `get_current_user()` returned `None` for anonymous sessions, causing immediate crashes upon dereferencing `user.role`.
- **TDD Test Case:** [`tests/test_prescriptions.py:test_unauthenticated_prescription_view_redirects`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_prescriptions.py#L71) and `test_unauthenticated_prescription_download_redirects`
- **Fix Applied:** Decorated `view_prescription` and `download_prescription` with `@login_required` in `app/routes/prescriptions.py`.
- **Commit:** `fabb8f3` — `fix(ISS-BUG-01): require authentication for prescription view and download`

---

### 2.3 ISS-CLIN-01: Prescription Clinical Gate Bypass & Consultation Enforcement
- **Defect Description:** Standalone prescription creation (`POST /prescriptions/create/<id>`) allowed doctors to issue prescriptions for unpaid bookings without any video consultation. Conversely, `doctors.py:complete_appointment` unconditionally blocked physical in-clinic appointments because it expected a 3-minute video consultation unlock.
- **Root Cause:** Divergent validation logic across blueprints. `prescriptions.py` lacked checks for payment status, appointment status, and consultation unlock. `doctors.py` lacked awareness of `appointment_type == 'physical'`.
- **TDD Test Suite (5 Cases):**
  - `test_prescription_create_unpaid_blocked`
  - `test_prescription_create_video_without_unlock_blocked`
  - `test_prescription_create_video_with_unlock_allowed`
  - `test_prescription_create_physical_paid_and_approved_allowed`
  - `test_prescription_create_different_doctor_blocked`
- **Fix Applied:** Extracted a unified workflow gate helper [`can_issue_prescription(appointment)`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/app/utils/appointment_workflow.py#L67) in `app/utils/appointment_workflow.py`. Enforced in both `app/routes/prescriptions.py` and `app/routes/doctors.py`:
  - Payment must be approved (`payment_status == 'approved'`).
  - Appointment must be active (`status == 'approved'`).
  - Mutual 3-minute video consultation (`prescription_unlocked == True`) is enforced exclusively for video appointments (`appointment_type == 'video'`), while physical appointments safely bypass video unlock.
- **Commit:** `977ea42` — `fix(ISS-CLIN-01): unify prescription clinical gate with appointment type awareness`

---

### 2.4 ISS-FE-01: Navbar Container Unclosed HTML Tag
- **Defect Description:** The top navigation bar in `app/templates/base.html` had an unclosed `<div class="container">` wrapping the brand and nav links, causing downstream DOM layout disruption across all pages.
- **Root Cause:** Missing `</div>` closing tag before `</nav>` on line 214.
- **TDD Test Case:** [`tests/test_home.py:test_navbar_container_div_closed_fe_01`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_home.py#L18) (parsed DOM via html5lib/BeautifulSoup structure).
- **Fix Applied:** Added the missing `</div>` before `</nav>` in `app/templates/base.html`.
- **Commit:** `24e0075` — `fix(ISS-FE-01): close container div in navbar before nav tag`

---

### 2.5 ISS-BUG-02: Appointment Timing & Cancellation Window Timezone Drift
- **Defect Description:** The 3-hour patient cancellation deadline check and slot expiry checker compared appointment time against system local clock (`datetime.now()`) instead of Pakistan Standard Time (PKT, UTC+5).
- **Root Cause:** Inconsistent clock sources between naive local datetimes and timezone-aware PKT schedules.
- **TDD Test Case:** [`tests/test_refunds.py:test_cancellation_window_clock_patched_under_3h`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_refunds.py#L103) and `test_cancellation_window_clock_patched_over_3h`.
- **Fix Applied:** Standardized appointment comparisons on `pkt_now_naive()` and `get_pakistan_time()` in `app/routes/patients.py` and `app/jobs/check_expired_appointments.py`. Zero `datetime.utcnow()` database write statements were modified, preserving complete backward compatibility with existing records.
- **Commit:** `681b41e` — `fix(ISS-BUG-02): standardize appointment timing and cancellation window on PKT`

---

### 2.6 ISS-PERF-02: Expired Payments Cleanup Job Duplicate App Context
- **Defect Description:** Running the background cleanup job instantiated a redundant Flask application instance (`create_app()`) even when already running inside an active application context, consuming extra memory and database connections.
- **Root Cause:** Missing `has_app_context()` guard in `cleanup_expired_payments()`. Also contained raw Unicode characters (`\u2717`) that threw `UnicodeEncodeError` on Windows consoles.
- **TDD Test Case:** [`tests/test_appointments.py:test_cleanup_expired_payments_reuses_app_context_perf_02`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_appointments.py#L86).
- **Fix Applied:** Added `if not has_app_context(): with app.app_context():` in `app/utils/cleanup_expired_payments.py` and replaced non-ASCII status symbols with ASCII equivalents `[OK]` and `[ERROR]`.
- **Commit:** `6d2fbae` — `fix(ISS-PERF-02): reuse app context in expired payments cleanup job`

---

### 2.7 Dev Server Safety: Default Loopback Binding & Controlled Debug Mode
- **Defect Description:** `run.py` hardcoded `host='0.0.0.0'` and `debug=True`, exposing the local development server and interactive Werkzeug debugger pin to all local network interfaces by default.
- **Root Cause:** Unconditional parameter arguments in `socketio.run()`.
- **TDD Test Case:** [`tests/test_run.py:test_dev_server_default_host_is_loopback`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_run.py#L3) and `test_dev_server_host_bind_all_flag`.
- **Fix Applied:** Configured `run.py` to default to `127.0.0.1` unless `BIND_ALL_INTERFACES=true` or `FLASK_HOST` is explicitly set in the environment. Parameterized debug mode through `FLASK_DEBUG` (defaulting to True for local dev, or False when disabled). Added dynamic SSL certificate detection.
- **Commit:** `d5bd87e` — `fix(SEC-DEV): bind dev server to loopback by default`

---

### 2.8 Dependencies Modernization & Virtual Environment Rebuild
- **Defect Description:** Missing PDF generator package (`xhtml2pdf`), Windows-incompatible magic library without binaries (`python-magic`), unpinned SQLAlchemy causing deprecation warnings, and unused dead dependency (`eventlet`).
- **Root Cause:** Incomplete and unpinned `requirements.txt`.
- **Verification:**
  - Added `xhtml2pdf`
  - Added `python-magic-bin; sys_platform == "win32"`
  - Pinned `SQLAlchemy>=2.0,<2.1`
  - Removed unused `eventlet==0.33.3`
  - Recreated virtual environment `venv/` from scratch under Python 3.11.9.
  - Executed `pip check`: confirmed zero broken or conflicting dependencies.
- **Commit:** `3d7be38` — `fix(deps): update requirements with xhtml2pdf, pinned sqlalchemy, and platform-specific magic`

---

### 2.9 Fix 9: AI Chatbot Modernization & Configurable Flash Model
- **Defect Description:** The chatbot hardcoded the legacy `gemini-1.5-flash` model, which is no longer provisioned for new API keys, causing unhandled fallback to an expired OpenRouter key.
- **Root Cause:** Static string assignment `GEMINI_MODEL = "gemini-1.5-flash"` without environment variable override.
- **TDD Test Case:** [`tests/test_chat.py:test_ai_chatbot_gemini_model_configurable`](file:///C:/Users/Mubeen/Desktop/Quick%20Care%20FYP/Quick%20Care%20FYP/tests/test_chat.py#L67).
- **Fix Applied:** Configured `GEMINI_MODEL` via `os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")`. Verified against Google's Gemini API: `gemini-3.5-flash` responded in 2.44 seconds. Verified live application inference returned `llm_provider: gemini` with specialty `Neurology`.
- **Commit:** `8134b43` — `fix(AI-CHAT): make Gemini model configurable and preserve fallback`

---

## 3. Git History Audit Summary

| Commit SHA | Type | Component | Message Summary |
| :---: | :---: | :---: | :--- |
| `69c00d6` | `chore` | Test Infrastructure | Add pytest suite, dev requirements, and audit scripts |
| `ac44ee5` | `fix` | `NEW-BUG-01` | Redirect public doctors route to find-doctors directory |
| `fabb8f3` | `fix` | `ISS-BUG-01` | Require authentication for prescription view and download |
| `24e0075` | `fix` | `ISS-FE-01` | Close container div in navbar before nav tag |
| `681b41e` | `fix` | `ISS-BUG-02` | Standardize appointment timing and cancellation window on PKT |
| `6d2fbae` | `fix` | `ISS-PERF-02` | Reuse app context in expired payments cleanup job |
| `d5bd87e` | `fix` | `SEC-DEV` | Bind dev server to loopback by default |
| `977ea42` | `fix` | `ISS-CLIN-01` | Unify prescription clinical gate with appointment type awareness |
| `3d7be38` | `fix` | `deps` | Update requirements with xhtml2pdf, pinned sqlalchemy, and platform-specific magic |
| `8134b43` | `fix` | `AI-CHAT` | Make Gemini model configurable and preserve fallback |

