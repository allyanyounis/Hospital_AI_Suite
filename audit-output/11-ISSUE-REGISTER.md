# 11 — MASTER ISSUE REGISTER & ROOT CAUSE ANALYSIS

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Audit Date:** November 1, 2026  
**Auditor:** Principal Software Architect & QA Lead  

---

## 1. Issue Summary by Severity

| Severity Level | Count | Focus Areas |
| :--- | :--- | :--- |
| **CRITICAL** | **4** | Global CSRF disabled, hardcoded API secrets, public static file exposure of CNIC/medical records, unverified payment webhook. |
| **HIGH** | **5** | Unauthenticated prescription 500 crash, missing manifest dependency (`xhtml2pdf`), stored XSS in blogs, service running as root, timezone calculation desynchronization. |
| **MEDIUM** | **10** | Duplicated appointment controllers, JSON chat log bottleneck, full table scan in disease funnel, redundant app factory instantiation, HLS video buffering in RAM, unclosed HTML `div`, AI chatbot rate limit bypass, email HTML injection, 1-year session lifetime, zero test coverage. |
| **LOW** | **1** | Tracked 4.8 MB binary (`mkcert.exe.exe`) in Git repository. |
| **TOTAL VERIFIED ISSUES** | **20** | Detailed analysis below. |

---

## 2. Comprehensive Issue Register

### ISS-SEC-01: Global CSRF Protection Disabled (`WTF_CSRF_ENABLED = False`)
- **Severity:** **CRITICAL**
- **Affected Files:** [`config.py`](config.py#L26), [`config.py`](config.py#L133)
- **Line References:** Line 26, Line 133
- **Evidence:** `WTF_CSRF_ENABLED = False  # Disable CSRF to avoid session conflicts`
- **Root Cause:** Deactivated during early development to simplify form testing and never re-enabled for production.
- **Impact:** An attacker can forge cross-site state-changing POST requests, forcing authenticated admins or doctors to approve payouts, cancel appointments, or approve doctor registrations.
- **Recommended Solution:** Enable `WTF_CSRF_ENABLED = True`, initialize `CSRFProtect(app)` in `app/__init__.py`, and ensure all Jinja POST forms and AJAX requests pass CSRF tokens.
- **Dependencies & Risks:** Requires testing all 56 AJAX POST endpoints to ensure `X-CSRFToken` headers are attached.
- **Verification Strategy:** Execute cross-origin POST request with valid session cookie; verify HTTP 400 Bad Request (CSRF token missing).
- **Complexity:** **Medium**

---

### ISS-SEC-02: Hardcoded Secrets Fallback in Source Code
- **Severity:** **CRITICAL**
- **Affected File:** [`config.py`](config.py#L57-L58)
- **Line References:** Lines 57–58
- **Evidence:**
  ```python
  AGORA_APP_ID = os.environ.get('AGORA_APP_ID') or 'your-agora-app-id'
  AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE') or 'your-agora-app-certificate'
  ```
- **Root Cause:** Developer convenience fallback for local testing committed to Git.
- **Impact:** Compromises Agora video consultation infrastructure. Anyone with repository access can generate valid RTC tokens and intercept private medical calls.
- **Recommended Solution:** Revoke existing credentials in the Agora console; remove fallback literals from `config.py`; require credentials from environment.
- **Dependencies & Risks:** Must update `.env` on all deployment targets.
- **Verification Strategy:** Unset environment variables; verify application raises an error rather than using a default string.
- **Complexity:** **Small**

---

### ISS-SEC-03: Unauthenticated Static Storage of Sensitive Health & ID Documents
- **Severity:** **CRITICAL**
- **Affected Files:** [`app/utils/file_upload.py`](app/utils/file_upload.py#L93), [`app/routes/patients.py`](app/routes/patients.py#L1178), [`deploy/nginx-quickcare.conf`](deploy/nginx-quickcare.conf#L11)
- **Line References:** `file_upload.py:93`, `patients.py:1178`, `nginx-quickcare.conf:11`
- **Evidence:** Files saved to `app/static/uploads/`; Nginx serves `/static/` directly without authentication.
- **Root Cause:** Storing user-uploaded confidential documents within the public web server static folder.
- **Impact:** Unauthenticated actors can view and download Pakistani National Identity Cards (CNIC front/back), doctor medical licenses, private patient lab reports, and payment receipts.
- **Recommended Solution:** Relocate uploads to `storage/private_uploads/`; serve exclusively through an authenticated Flask view using `send_from_directory` or Nginx `X-Accel-Redirect`.
- **Dependencies & Risks:** Requires updating stored file paths in the database and updating template `url_for` references.
- **Verification Strategy:** Request document URL without session cookie; verify HTTP 401/403 or redirect to login.
- **Complexity:** **Medium**

---

### ISS-SEC-04: Missing HMAC Signature Verification on Safepay Webhook
- **Severity:** **CRITICAL**
- **Affected File:** [`app/routes/payments.py`](app/routes/payments.py#L372-L413)
- **Line References:** Lines 372–413
- **Evidence:** Endpoint parses JSON and immediately marks appointment paid without verifying any signature header:
  ```python
  if state not in ('TRACKER_ENDED', 'PAYMENT_SUCCESSFUL'): return ...
  mark_appointment_paid(appointment, tracker_token)
  ```
- **Root Cause:** Incomplete webhook implementation; cryptographic validation logic was omitted.
- **Impact:** Any attacker can send an unauthenticated HTTP POST to `/safepay/webhook` and falsely mark unpaid appointments as paid.
- **Recommended Solution:** Verify incoming signature against `SAFEPAY_SECRET_KEY` using HMAC SHA256 before processing.
- **Dependencies & Risks:** Must confirm Safepay's exact signature header format (`X-SFPY-SIGNATURE`).
- **Verification Strategy:** Send unsigned POST payload; verify HTTP 401 Unauthorized.
- **Complexity:** **Small**

---

### ISS-BUG-01: Missing `@login_required` Crashes Prescription View and Download Endpoints
- **Severity:** **HIGH**
- **Affected File:** [`app/routes/prescriptions.py`](app/routes/prescriptions.py#L96-L160)
- **Line References:** Lines 96, 127
- **Evidence:**
  ```python
  @prescriptions_bp.route('/view/<int:prescription_id>')
  def view_prescription(prescription_id):
      prescription = Prescription.query.get_or_404(prescription_id)
      user = get_current_user()      # Returns None when not logged in
      if user.role == 'doctor' ...   # AttributeError: 'NoneType' object has no attribute 'role'
  ```
- **Root Cause:** Omission of `@login_required` decorator on routes that assume `user` is non-null.
- **Impact:** Unauthenticated requests or search crawlers trigger an unhandled HTTP 500 error and stack trace crash.
- **Recommended Solution:** Add `@login_required` to both `view_prescription` and `download_prescription`.
- **Dependencies & Risks:** None.
- **Verification Strategy:** Send unauthenticated GET request to `/prescriptions/view/1`; verify clean redirect to `/auth/login`.
- **Complexity:** **Small**

---

### ISS-DEP-01: Missing `xhtml2pdf` Dependency in `requirements.txt`
- **Severity:** **HIGH**
- **Affected Files:** [`Quick Care FYP/requirements.txt`](requirements.txt), [`app/utils/pdf_generator.py`](app/utils/pdf_generator.py#L4)
- **Line References:** `pdf_generator.py:4` (`from xhtml2pdf import pisa`)
- **Evidence:** `xhtml2pdf` is imported in `pdf_generator.py`, but omitted entirely from `requirements.txt`.
- **Root Cause:** Package was installed manually in the developer's virtualenv without running `pip freeze > requirements.txt`.
- **Impact:** Any fresh environment installation from `requirements.txt` fails when a user attempts to generate or download a prescription PDF (`ModuleNotFoundError`).
- **Recommended Solution:** Add `xhtml2pdf>=0.2.16` to `requirements.txt`.
- **Dependencies & Risks:** May require ReportLab sub-dependencies.
- **Verification Strategy:** In clean virtualenv, run `pip install -r requirements.txt`; test `import xhtml2pdf`.
- **Complexity:** **Small**

---

### ISS-SEC-05: Stored Cross-Site Scripting (XSS) in Doctor Blog Submissions
- **Severity:** **HIGH**
- **Affected Files:** [`app/routes/doctors.py`](app/routes/doctors.py#L968), [`app/templates/blogs/view.html`](app/templates/blogs/view.html#L117)
- **Line References:** `doctors.py:968`, `blogs/view.html:117`
- **Evidence:** `render_content | safe` in Jinja template renders unsanitized HTML stored from TinyMCE.
- **Root Cause:** Absence of HTML sanitization on blog submission paired with Jinja `| safe` filter.
- **Impact:** Stored XSS attacks targeting patients and administrators, allowing cookie theft and admin session compromise.
- **Recommended Solution:** Integrate `bleach` or `nh3` to sanitize blog HTML before saving to database.
- **Dependencies & Risks:** Need to preserve safe formatting tags (`<p>`, `<b>`, `<img>`, `<h3>`).
- **Verification Strategy:** Submit blog with `<script>alert(1)</script>`; verify script tags are stripped upon viewing.
- **Complexity:** **Medium**

---

### ISS-OPS-01: Systemd Service Unit Configured to Execute Gunicorn as `root`
- **Severity:** **HIGH**
- **Affected File:** [`deploy/quickcare.service`](deploy/quickcare.service#L6-L7)
- **Line References:** Lines 6–7
- **Evidence:** `User=root`, `Group=root` in production service unit.
- **Root Cause:** Deployed under root user during FYP staging for simplicity.
- **Impact:** Any remote code execution flaw in dependencies or file handling grants the attacker full root privileges over the host Linux machine.
- **Recommended Solution:** Change user to `www-data` or create a dedicated `quickcare` service account.
- **Dependencies & Risks:** Must ensure file ownership of application directory and database files matches the unprivileged user.
- **Verification Strategy:** Check `ps aux | grep gunicorn` on server; verify process runs as unprivileged user.
- **Complexity:** **Small**

---

### ISS-BUG-02: Timezone Desynchronization Across Appointment Expiry and Cancellation Calculations
- **Severity:** **HIGH**
- **Affected Files:** [`app/routes/patients.py`](app/routes/patients.py#L836), [`app/jobs/check_expired_appointments.py`](app/jobs/check_expired_appointments.py#L22)
- **Line References:** `patients.py:836`, `check_expired_appointments.py:22`
- **Evidence:**
  ```python
  # patients.py:836
  time_diff = appointment_datetime - datetime.now()
  # check_expired_appointments.py:22
  now = datetime.now()
  if now <= slot_start: continue
  ```
- **Root Cause:** Mixing system local time `datetime.now()` or `datetime.utcnow()` with naive Pakistan Standard Time (PKT) appointment timestamps.
- **Impact:** If the server is hosted in UTC or Singapore (UTC+8), appointment cancellation deadlines and no-show detections are off by 5 hours, cancelling appointments prematurely or allowing late cancellations.
- **Recommended Solution:** Standardize all business logic comparisons using `pkt_now_naive()` from `app/utils/timezone.py`.
- **Dependencies & Risks:** Must audit all 40 occurrences of `datetime.now()` across the codebase.
- **Verification Strategy:** Execute test comparing PKT appointment on a UTC-configured machine; verify correct 3-hour delta.
- **Complexity:** **Medium**

---

### ISS-ARCH-01: Extensive Duplication of Core Appointment Lifecycles Across Blueprints
- **Severity:** **MEDIUM**
- **Affected Files:** [`app/routes/appointments.py`](app/routes/appointments.py), [`app/routes/doctors.py`](app/routes/doctors.py), [`app/routes/patients.py`](app/routes/patients.py)
- **Line References:** `appointments.py:38` vs `patients.py:564`, `appointments.py:192` vs `doctors.py:668`, `appointments.py:247` vs `doctors.py:713`
- **Evidence:** Identical controller logic implemented in two separate blueprints under different URLs.
- **Root Cause:** Parallel development without centralized domain service layer.
- **Impact:** Inconsistent business logic, increased maintenance overhead, and bug fixes applied to one file leaving the duplicate vulnerable.
- **Recommended Solution:** Extract appointment lifecycle transitions into a shared `AppointmentService` domain class and have both route endpoints call the shared service, or deprecate duplicate routes.
- **Dependencies & Risks:** Must update template form action URLs to ensure consistent targeting.
- **Verification Strategy:** Verify booking, approving, and rejecting appointments through unified service.
- **Complexity:** **Medium**

---

### ISS-ARCH-02: Quadratic I/O Degradation from Serialized JSON Chat Logs (`chat_logs`)
- **Severity:** **MEDIUM**
- **Affected Files:** [`app/models.py`](app/models.py#L364), [`app/services/socketio_events.py`](app/services/socketio_events.py#L256-L272)
- **Line References:** `models.py:364`, `socketio_events.py:256`
- **Evidence:** Entire conversation is appended to a single JSON list column: `medical_histories.chat_logs`.
- **Root Cause:** Storing relational message entities inside a JSON text field.
- **Impact:** As consultation chat length increases, read/write I/O expands quadratically. Concurrent messages risk overwriting each other.
- **Recommended Solution:** Create a normalized `ChatMessage` relational table (`id`, `appointment_id`, `sender_id`, `message`, `timestamp`).
- **Dependencies & Risks:** Requires database migration and updating socket event handler.
- **Verification Strategy:** Benchmark sending 100 messages; observe linear database performance.
- **Complexity:** **Medium**

---

### ISS-PERF-01: Full Table Scan in Disease Detail View Loading All Doctors into Memory
- **Severity:** **MEDIUM**
- **Affected File:** [`app/routes/diseases.py`](app/routes/diseases.py#L68-L73)
- **Line References:** Lines 68–73
- **Evidence:** `all_approved = Doctor.query.filter_by(is_approved=True, is_verified=True).all()` followed by a Python `for` loop filter.
- **Root Cause:** Filtering in Python memory rather than in SQL.
- **Impact:** Loading every doctor record on every disease view causes severe latency as the doctor registry grows.
- **Recommended Solution:** Perform the filter in the database query:
  `Doctor.query.filter_by(is_approved=True, is_verified=True, category=disease_cat).limit(3).all()`.
- **Dependencies & Risks:** Ensure category naming normalization matches between models.
- **Verification Strategy:** Measure query execution time with 1,000 doctor records.
- **Complexity:** **Small**

---

### ISS-PERF-02: Redundant `create_app()` Invocation Inside Background Payment Cleanup Job
- **Severity:** **MEDIUM**
- **Affected File:** [`app/utils/cleanup_expired_payments.py`](app/utils/cleanup_expired_payments.py#L27)
- **Line References:** Line 27
- **Evidence:** `app = create_app()` inside `cleanup_expired_payments()`, called every 10 minutes by `scheduler.py`.
- **Root Cause:** Script was written as a standalone CLI job and imported into the scheduler without refactoring.
- **Impact:** Spikes memory and CPU every 10 minutes by re-running database schema migrations and initializing extensions in a background thread.
- **Recommended Solution:** Pass existing application context into the job function.
- **Dependencies & Risks:** None.
- **Verification Strategy:** Monitor memory usage during scheduler execution.
- **Complexity:** **Small**

---

### ISS-PERF-03: Excessive Synchronous Memory Buffering During HLS Segment Streaming
- **Severity:** **MEDIUM**
- **Affected File:** [`app/routes/admin.py`](app/routes/admin.py#L926-L950)
- **Line References:** Lines 926–950
- **Evidence:** `raw = fetch_spaces_object(object_key); return Response(raw, mimetype='video/mp2t')`.
- **Root Cause:** Application acts as a synchronous reverse-proxy for video files instead of delegating to cloud storage or Nginx.
- **Impact:** Buffering 2–5 MB video chunks into Flask memory ties up Gunicorn worker threads and causes high latency during recording playback.
- **Recommended Solution:** Configure DigitalOcean Spaces CORS to allow direct client streaming, or use Nginx caching.
- **Dependencies & Risks:** DigitalOcean Spaces bucket permissions.
- **Verification Strategy:** Play recording in admin dashboard; inspect network tab to verify direct streaming.
- **Complexity:** **Medium**

---

### ISS-FE-01: Unclosed Container `div` in Master Base Template (`base.html`)
- **Severity:** **MEDIUM**
- **Affected File:** [`app/templates/base.html`](app/templates/base.html#L413-L502)
- **Line References:** Lines 413, 502
- **Evidence:** Line 413 opens `<div class="container">`, line 422 opens `<div class="collapse navbar-collapse">`, line 501 closes `</div>`, line 502 closes `</nav>`. Container `div` is never closed.
- **Root Cause:** Template markup oversight.
- **Impact:** Misaligns page content, alerts, and footers across mobile viewports.
- **Recommended Solution:** Add closing `</div>` before `</nav>`.
- **Dependencies & Risks:** Visual layout inspection on desktop and mobile.
- **Verification Strategy:** Validate rendered HTML using W3C markup validator.
- **Complexity:** **Small**

---

### ISS-SEC-06: Client-Side Session Cookie Rate-Limiting Bypass on AI Chatbot
- **Severity:** **MEDIUM**
- **Affected File:** [`app/routes/qa.py`](app/routes/qa.py#L22-L38)
- **Line References:** Lines 22–38
- **Evidence:** `timestamps = session.get('qa_ai_chat_timestamps', [])`.
- **Root Cause:** Storing rate-limiting state in client cookies instead of server-side storage.
- **Impact:** Automated scripts can omit the `Cookie` header to make unlimited LLM calls, draining Gemini or OpenRouter quotas.
- **Recommended Solution:** Use `Flask-Limiter` with client IP address keying.
- **Dependencies & Risks:** Requires `Flask-Limiter` package.
- **Verification Strategy:** Send 30 requests without cookies; verify 429 Too Many Requests response.
- **Complexity:** **Small**

---

### ISS-SEC-07: Unescaped HTML Interpolation in Transactional Email Templates
- **Severity:** **MEDIUM**
- **Affected File:** [`app/services/email_service.py`](app/services/email_service.py#L76)
- **Line References:** Line 76
- **Evidence:** `template = f"... <h1>Welcome, {patient_name}! 👋</h1> ..."`
- **Root Cause:** Using Python f-strings without HTML escaping.
- **Impact:** User-controlled strings injected into emails allow tracking beacons or phishing injections.
- **Recommended Solution:** Use `html.escape()` or dedicated Jinja2 email templates.
- **Dependencies & Risks:** None.
- **Verification Strategy:** Register user with HTML tags in name; verify email contains escaped entities.
- **Complexity:** **Small**

---

### ISS-SEC-08: 1-Year Unbounded Persistent Session Lifetime
- **Severity:** **MEDIUM**
- **Affected Files:** [`config.py`](config.py#L20-L23), [`app/__init__.py`](app/__init__.py#L25-L36)
- **Line References:** `config.py:20`, `app/__init__.py:25`
- **Evidence:** `PERMANENT_SESSION_LIFETIME = timedelta(days=365)`.
- **Root Cause:** Intentionally configured to never log users out.
- **Impact:** Expands vulnerability window if a user logs in on a shared hospital or clinic computer.
- **Recommended Solution:** Enforce rolling session timeout (e.g. 7 days) and 2-hour idle timeout on clinical pages.
- **Dependencies & Risks:** Requires user communication regarding session policy.
- **Verification Strategy:** Verify cookie expiration headers in HTTP response.
- **Complexity:** **Small**

---

### ISS-QA-01: Zero Automated Unit or Integration Test Coverage (0.0%)
- **Severity:** **MEDIUM**
- **Affected Files:** Entire repository
- **Evidence:** Zero test files present in workspace.
- **Root Cause:** Testing was performed exclusively via manual ad-hoc browser workflows.
- **Impact:** Any bug fix or refactoring introduces extreme risk of undetected regression.
- **Recommended Solution:** Set up `pytest`, `pytest-flask`, and an in-memory SQLite fixture suite.
- **Dependencies & Risks:** Test suite development time.
- **Verification Strategy:** Run `pytest`; verify test discovery and execution.
- **Complexity:** **Medium**

---

### ISS-DEP-02: Tracked 4.8 MB Windows Binary (`mkcert.exe.exe`) in Git Repository
- **Severity:** **LOW**
- **Affected File:** `Quick Care FYP/mkcert.exe.exe`
- **Evidence:** Tracked executable binary in Git index (`git ls-files`).
- **Root Cause:** Certificate helper utility committed directly to repository.
- **Impact:** Bloats repository clone size; violates source repository best practices.
- **Recommended Solution:** Remove from Git index (`git rm --cached mkcert.exe.exe`) and add `*.exe` to `.gitignore`.
- **Dependencies & Risks:** None.
- **Verification Strategy:** Verify `git status` shows file untracked.
- **Complexity:** **Small**

