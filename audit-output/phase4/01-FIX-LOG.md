# Phase 4 Fix Log: Security Hardening (Local Project)

**Branch:** `phase-4-security` (branched from `phase-3-bugfix`)  
**Date:** November 1, 2026  
**Scope:** Remediations for carry-over booking defects (Part 0) and authorized direct security fixes (Part 1).

---

## 1. Summary of Commits

| Issue ID | Category | Commit Hash | Short Description | Files Modified |
| :--- | :--- | :--- | :--- | :--- |
| **ISS-BUG-02b** | Carry-Over Fix | `9a31d4b` | Standardize same-day booking validation on Pakistan Standard Time | `app/routes/patients.py`, `tests/test_appointments.py` |
| **ISS-SEC-02** | Hardcoded Secrets | `b0e60a8` | Remove hardcoded Agora credentials; return clean HTTP 503 if unconfigured | `config.py`, `app/__init__.py`, `app/routes/video.py`, `.env.example`, `tests/test_security.py` |
| **ISS-SEC-05** | Stored XSS | `87d9d92` | Sanitize blog rich text with `nh3` on save & render; harden advice escaping | `app/utils/sanitize.py`, `app/routes/blogs.py`, `app/routes/doctors.py`, `app/templates/prescriptions/pdf_template.html`, `app/templates/patients/profile.html`, `requirements.txt`, `tests/test_sanitize.py` |
| **ISS-SEC-06** | Rate Limiting Bypass | `e2905c9` | Move AI chat rate limiter to server-side memory store keyed by user/IP | `app/utils/rate_limit.py`, `app/routes/qa.py`, `tests/test_chat.py` |
| **ISS-SEC-07** | Email Injection | `e053567` | HTML-escape user-controlled inputs in email f-strings using `markupsafe.escape` | `app/services/email_service.py`, `tests/test_email.py` |
| **ISS-SEC-08** | Session Management | `99d7dc7` | Configurable session lifetime (default 7 days) and conditional secure cookie | `config.py`, `app/__init__.py`, `.env.example`, `tests/test_auth.py` |

---

## 2. Detailed Technical Fix Reports

### 2.1 Part 0: ISS-BUG-02b — Standardize Same-Day Booking Validation on PKT Datetime
- **Root Cause:** In `app/routes/patients.py`, same-day slot validation used `today = date.today()` (evaluating to the local machine system calendar date) while `current_time` was computed from `get_pakistan_time()`. If the server system date differed from PKT (e.g., near midnight boundary), appointments could be incorrectly rejected or accepted. Additionally, `get_pakistan_time()` returned a `time` object which made single-point-in-time boundary assertions brittle.
- **Change Made:**
  - Standardized datetime computation on `now_pkt = get_pakistan_now()`.
  - Extracted `today = now_pkt.date()` and `current_time = now_pkt.time()` from the single synchronized PKT timestamp.
  - Maintained slot comparison: same-day bookings where `appointment_time_obj <= current_time` are rejected with flash error *"Cannot book appointments for past time slots."*.
- **Tests Added (`tests/test_appointments.py`):**
  - `test_booking_same_day_slot_in_past_rejected`: Clock frozen in PKT; past slot rejected.
  - `test_booking_same_day_slot_in_future_allowed`: Future slot allowed.
  - `test_booking_pkt_date_boundary_skew`: System clock set to 23:50 PKT; validates correct day/time boundary matching.
- **Commit:** `9a31d4b`

---

### 2.2 Fix 1.1: ISS-SEC-02 — Remove Hardcoded Agora Credentials
- **Root Cause:** `config.py` contained literal fallback values for `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE`. If environment variables were omitted, the application fell back to exposed credentials. Furthermore, when unconfigured, the video token route crashed with a 500 error.
- **Change Made:**
  - Removed literal fallback strings from `config.py`.
  - Added startup warning in `app/__init__.py:create_app()` notifying administrators when Agora credentials are unset without preventing startup.
  - Updated `/video/token/<appointment_id>` in `app/routes/video.py` to check for missing credentials and return a clean HTTP 503 response (`{'error': 'Video calling is not configured on this server.'}`) instead of raising an uncaught exception.
  - Added placeholder variable names to `.env.example`.
- **Tests Added (`tests/test_security.py`):**
  - `test_video_token_missing_credentials_clean_error`: Clears Agora config keys and verifies HTTP 503 with informative JSON error.
- **Commit:** `b0e60a8`

---

### 2.3 Fix 1.2: ISS-SEC-05 — Sanitize Blog Rich Text with `nh3`
- **Root Cause:** Doctor blog posts rendered using `{{ render_content | safe }}` in `app/templates/blogs/view.html:117` without server-side HTML sanitization, allowing stored cross-site scripting (XSS).
- **Change Made:**
  - Added `nh3` (high-performance Rust-based ammonia sanitizer) to `requirements.txt`.
  - Implemented `app/utils/sanitize.py:sanitize_html()` configured with an allowlist tailored for TinyMCE rich text formatting (`<p>`, `<b>`, `<i>`, `<ul>`, `<ol>`, `<li>`, `<a>`, `<img>`, `<h1>`-`<h6>`, `<table>`, `<blockquote>`, etc.).
  - Configured `link_rel='noopener noreferrer'` and strict URL scheme validation (`http`, `https`, `mailto`).
  - Applied sanitization on blog save and edit (`app/routes/doctors.py:new_blog`, `edit_blog`) and defense-in-depth sanitization on render (`app/routes/blogs.py:view_blog`).
  - Hardened `app/templates/prescriptions/pdf_template.html` by applying `escape` before newline conversion: `{{ prescription.advice | escape | replace('\n', '<br>') | safe }}`.
  - Replaced inline `| safe` in `app/templates/patients/profile.html:569` with explicit Jinja `if/else`.
- **Tests Added (`tests/test_sanitize.py`):**
  - `test_sanitize_html_removes_dangerous_tags`: Strips `<script>`, `onerror`, `<iframe>`, `javascript:`.
  - `test_sanitize_html_preserves_safe_markup`: Preserves formatted text and links with `noopener noreferrer`.
  - `test_blog_view_sanitizes_stored_xss`: Validates defense-in-depth sanitization during template rendering.
- **Commit:** `87d9d92`

---

### 2.4 Fix 1.3: ISS-SEC-06 — Move AI Chat Rate Limiting to Server-Side Store
- **Root Cause:** Rate limiting in `app/routes/qa.py:_ai_rate_limited()` tracked request timestamps in `session['qa_ai_chat_timestamps']`. Clients could bypass rate limits indefinitely by clearing session cookies between requests.
- **Change Made:**
  - Created thread-safe sliding window rate limiter in `app/utils/rate_limit.py:InMemoryRateLimiter`.
  - Keyed by `user:{user.id}` for authenticated accounts; keyed by `ip:{client_ip}` (supporting `X-Forwarded-For` with fallback to `remote_addr`) for anonymous visitors.
  - Maintained the existing business rule: 20 requests per 10-minute sliding window.
  - Implemented automatic pruning of expired entries every 100 requests to prevent unbounded memory growth.
- **Tests Added (`tests/test_chat.py`):**
  - `test_ai_chat_rate_limiting_server_side_cleared_cookies`: Demonstrates that a client clearing cookies after every request is still blocked with HTTP 429 on request #21.
  - `test_ai_chat_rate_limiting_authenticated_user_across_sessions`: Confirms that authenticated user IDs are tracked across session recreation.
- **Commit:** `e2905c9`

---

### 2.5 Fix 1.4: ISS-SEC-07 — HTML Injection in Email f-Strings
- **Root Cause:** All 10 email notification functions in `app/services/email_service.py` interpolated raw user inputs (patient names, doctor names, reported symptoms, rejection reasons, payment methods) directly into HTML template strings via Python f-strings.
- **Change Made:**
  - Imported `markupsafe.escape`.
  - Applied `escape()` to every user-controlled variable across all 10 email functions before template interpolation.
  - Preserved the existing f-string architecture without converting to external Jinja files.
- **Tests Added (`tests/test_email.py`):**
  - `test_appointment_request_email_escapes_html`: Asserts `<script>` and `<b>` tags in patient name and symptoms are converted to HTML entities.
  - `test_appointment_rejection_email_escapes_reason`: Confirms rejection reason containing `<img src=x onerror=...>` is escaped.
  - `test_welcome_emails_escape_names`: Confirms user names with formatting tags are escaped.
  - `test_manual_payment_notification_escapes_user_input`: Confirms payment method and payer name are escaped.
- **Commit:** `e053567`

---

### 2.6 Fix 1.5: ISS-SEC-08 — Configurable Session Lifetime & Secure Cookies
- **Root Cause:** `app/__init__.py` and `config.py` hardcoded session expiration and lifetime to 365 days (`timedelta(days=365)`), preventing auto-logout and creating long-term session hijacking risks. Additionally, `SESSION_COOKIE_SECURE` was fixed to `False` in development and lacked automatic HTTPS detection.
- **Change Made:**
  - Removed 365-day hardcoded overrides.
  - Configured `PERMANENT_SESSION_LIFETIME` and `SESSION_COOKIE_EXPIRES` to read from `PERMANENT_SESSION_LIFETIME_DAYS` (defaulting to 7 days).
  - Configured `SESSION_COOKIE_SECURE` to dynamically activate when `PREFERRED_URL_SCHEME == 'https'` or `os.environ.get('SESSION_COOKIE_SECURE')` is `true`.
  - Maintained `SESSION_COOKIE_SECURE = False` on local HTTP development so login remains functional without SSL.
  - Added configuration keys to `.env.example`.
- **Tests Added (`tests/test_auth.py`):**
  - `test_configurable_session_lifetime_and_cookie_security`: Tests custom env var lifetime (14 days), default lifetime (7 days), and secure cookie flag activation on HTTPS.
- **Commit:** `99d7dc7`

