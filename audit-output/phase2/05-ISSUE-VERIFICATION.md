# PHASE 2 — ISSUE VERIFICATION REPORT
*(Updated in Phase 3 with Empirical Re-Verification, Corrections & Discrepancy Reconciliation)*

---

## 1. Corrections (Phase 3 Audit & Reconciliation)

An independent review of Phase 2 deliverables identified erroneous descriptions in the deferred issues table and highlighted the need to formally record the clinical workflow gap discovered in `/prescriptions/create/<id>`:

1. **Deferred Issue Descriptions Corrected:**
   - **`ISS-SEC-04`**: Previously erroneously described as "Hardcoded SSL certificates in production deployment configs". **Correct description:** Missing Safepay webhook HMAC signature verification (`app/routes/payments.py:safepay_webhook` accepts incoming webhook notifications without validating cryptographic HMAC-SHA256 signature headers).
   - **`ISS-PERF-03`**: Previously erroneously described as "Celery / Redis asynchronous worker configuration". **Correct description:** Synchronous video chunk proxying / cloud recording ingestion (blocking HTTP requests for video chunk ingestion without asynchronous message broker).
2. **Clinical Workflow & Security Gate Defect Identified:**
   - **Prescription Creation Bypass (`NEW-APP-BUG / Gate Gap`):** `app/routes/prescriptions.py:13-33` permits a doctor to issue prescriptions without verifying that the appointment's payment has been approved (`payment_status == 'approved'`) and without enforcing the mutual 3-minute video consultation requirement (`appointment.prescription_unlocked == True`). This stands in direct contrast to `app/routes/doctors.py:773`, which correctly enforces both gates.
3. **Screenshot Authenticity Corrected:**
   - Five previously unauthenticated screenshots (`07_patient_dashboard.png`, `08_admin_dashboard.png`, `09_doctor_dashboard.png`, `10_appointment_details.png`, `12_patient_documents.png`) that duplicated the login screen due to unauthenticated headless browser sessions have been recaptured using Edge CDP with injected session cookies, confirming distinct URLs, unique heading elements, and unique cryptographic hashes.

---

## 2. Issue Verification Register

### ISS-BUG-01: Missing `@login_required` Crashes Prescription View and Download
- **Phase 1 Severity:** HIGH
- **Verification Status:** **CONFIRMED**
- **Test Target:** `GET /prescriptions/view/1` and `GET /prescriptions/download/1` (unauthenticated)
- **Observed Behavior:** Both endpoints trigger an unhandled `HTTP 500 Internal Server Error`.
- **Runtime Stack Trace Evidence:**
  ```text
  File "app/routes/prescriptions.py", line 106, in view_prescription
    if user.role == 'doctor' and user.doctor_profile:
  AttributeError: 'NoneType' object has no attribute 'role'
  ```
  ```text
  File "app/routes/prescriptions.py", line 137, in download_prescription
    if user.role == 'doctor' and user.doctor_profile:
  AttributeError: 'NoneType' object has no attribute 'role'
  ```
- **Root Cause:** Both view functions invoke `user = get_current_user()`, which returns `None` for unauthenticated visitors. Without `@login_required`, the code attempts attribute access on `NoneType`.

---

### ISS-DEP-01: Missing `xhtml2pdf` Dependency in `requirements.txt`
- **Phase 1 Severity:** HIGH
- **Verification Status:** **CONFIRMED & RESOLVED BY VENV INSTALLATION**
- **Observed Behavior:**
  - Before installation: `from xhtml2pdf import pisa` in `app/utils/pdf_generator.py` failed with `ModuleNotFoundError`.
  - With `xhtml2pdf==0.2.28` installed in the virtual environment, an authenticated request to `GET /prescriptions/download/14` returned:
    - Status: `HTTP 200 OK`
    - Content-Type: `application/pdf`
    - Content-Disposition: `attachment; filename="prescription_14.pdf"`
    - Binary PDF Payload: `6,331 bytes`
- **Root Cause:** Package was omitted from the original `requirements.txt`. Adding it to `requirements-dev.txt` and `requirements.txt` fully restores PDF export capability.

---

### ISS-FE-01: Unclosed Container `div` in Master Base Template (`base.html`)
- **Phase 1 Severity:** MEDIUM
- **Verification Status:** **CONFIRMED**
- **Affected File:** `app/templates/base.html` lines 413 to 502
- **Template Markup Evidence:**
  - Line 412: `<nav class="navbar navbar-expand-lg ...">`
  - Line 413: `<div class="container">` (opened)
  - Line 422: `<div class="collapse navbar-collapse" id="navbarNav">` (opened)
  - Line 501: `</div>` (closes line 422 `collapse navbar-collapse`)
  - Line 502: `</nav>` (closes line 412 `navbar`)
- **Impact & Browser Recovery:** The `<div class="container">` opened at line 413 is never closed before `</nav>`. Modern Chromium/Edge HTML5 parsers auto-close the open `div` when encountering the closing `</nav>` tag, preventing catastrophic desktop layout collapse. However, on narrow viewport renders (e.g. mobile 375px), it produces malformed DOM nesting. Screenshots [`01_landing_desktop.png`](screenshots/01_landing_desktop.png) and [`02_landing_mobile.png`](screenshots/02_landing_mobile.png) provide visual documentation.

---

### ISS-SEC-03: Unauthenticated Static Storage of Sensitive Health & ID Documents
- **Phase 1 Severity:** CRITICAL
- **Verification Status:** **CONFIRMED**
- **Test Target:** Direct HTTP GET requests to files in `/static/uploads/` without cookies or session tokens:
  1. `GET https://127.0.0.1:5000/static/uploads/0595c87e7dff47e09a849a21570fa5ba.png`
  2. `GET https://127.0.0.1:5000/static/uploads/medical_documents/2/d62cb163e0ca4b8faa8ba4e3ccaaee35_neurocognitive_tests.png`
- **Observed Behavior:** Both requests returned `HTTP 200 OK` and served private patient files directly.
- **Root Cause:** User-uploaded identification documents (CNIC cards), diagnostic lab reports, and payment transfer receipts are saved directly into `app/static/uploads/`. Static files are served publicly by the web server without routing through role-based access control or session authentication.

---

### ISS-SEC-05: Stored Cross-Site Scripting (XSS) in Doctor Blog Submissions
- **Phase 1 Severity:** HIGH
- **Verification Status:** **CONFIRMED**
- **Test Target:** Doctor created blog post #13 containing:
  ```html
  <p>A healthy heart is essential. <b>xss-verified-marker</b> <script>window.audit_xss=true;</script></p>
  ```
  Admin approved the blog, and an unauthenticated public client requested `GET /blogs/13`.
- **Observed Behavior:** The response body contained raw, unescaped HTML:
  ```html
  <b>xss-verified-marker</b> <script>window.audit_xss=true;</script>
  ```
- **Evidence:** Line 117 of `app/templates/blogs/view.html` renders `{{ blog.content | safe }}`. Because no HTML sanitization (such as `bleach` or `nh3`) is applied upon submission or rendering, arbitrary JavaScript executes in the context of any reader's browser session. Screenshot saved in [`13_blog_view_xss.png`](screenshots/13_blog_view_xss.png).

---

### ISS-SEC-01: Global CSRF Protection Disabled (`WTF_CSRF_ENABLED = False`)
- **Phase 1 Severity:** CRITICAL
- **Verification Status:** **CONFIRMED**
- **Test Target:** State-changing `POST /newsletter` and `POST /auth/login` requests submitted with no CSRF token header (`X-CSRFToken`) or form token (`csrf_token`).
- **Observed Behavior:** Requests were accepted and processed with `HTTP 200` / `HTTP 302`, rather than being rejected with `HTTP 400 Bad Request`.
- **Root Cause:** `WTF_CSRF_ENABLED = False` is explicitly declared in `config.py:26` and `config.py:133`. Cross-site request forgery protection is deactivated across the entire application.

---

### ISS-BUG-02: Timezone Desynchronization Across Appointment Expiry and Cancellation Calculations
- **Phase 1 Severity:** HIGH
- **Verification Status:** **CONFIRMED (via Static & Runtime Analysis)**
- **Evidence:**
  - `app/routes/patients.py:836`: `time_diff = appointment_datetime - datetime.now()` uses the host operating system's local server clock (naive).
  - `app/jobs/check_expired_appointments.py:22`: `now = datetime.now()` compares host local time against database timestamps.
  - `app/routes/patients.py:237, 474, 966`: `datetime.utcnow()` writes UTC timestamps to database columns.
  - `app/utils/timezone.py`: Implements Pakistan Standard Time (PKT, UTC+5) functions (`get_pakistan_now()`, `pkt_now_naive()`).
- **Impact:** Whenever the application runs on UTC-based servers or external cloud environments, appointment cancellation checks and automated expiry background jobs will be offset by 5 hours relative to Pakistan Standard Time.

---

## 3. Discovered New Runtime Issues

### NEW-BUG-01: Missing Template for Public Doctor Directory (`/doctors`)
- **Severity:** HIGH
- **Route:** `GET /doctors`
- **Location:** `app/routes/home.py:136`
- **Error:** `jinja2.exceptions.TemplateNotFound: home/doctors.html`
- **Impact:** Visitors clicking the main "Doctors" link in the global navigation receive an unhandled `HTTP 500 Internal Server Error`. The actual template exists in `app/templates/patients/find_doctors.html` and is served under `/patients/find-doctors`.

### NEW-APP-BUG: Prescription Creation Endpoint Bypasses Payment & Video Consultation Gates
- **Severity:** HIGH
- **Route:** `POST /prescriptions/create/<int:appointment_id>`
- **Location:** `app/routes/prescriptions.py:13-33`
- **Impact:** The route fails to check `appointment.payment_status == 'approved'`, appointment status, or `appointment.prescription_unlocked == True`. A doctor can issue prescriptions for appointments whose payments are still pending and without completing the required 3-minute video consultation.

---

## 4. Out of Scope / Deferred Issues

Per local-only project scope, all server, container, and deployment items are categorized as **Deferred: not deployed**:

| Issue ID | Accurate Description | Phase 2 Disposition |
| :--- | :--- | :--- |
| **ISS-OPS-01** | Production Nginx / Gunicorn configuration inconsistencies | **Deferred: not deployed** |
| **ISS-SEC-04** | Safepay webhook HMAC signature verification missing | **Deferred: not deployed** |
| **ISS-PERF-03** | Synchronous video chunk proxying / recording ingestion | **Deferred: not deployed** |
| **P4-01 – P4-04** | PostgreSQL migration, systemd daemonization, remote Safepay webhooks | **Deferred: not deployed** |
