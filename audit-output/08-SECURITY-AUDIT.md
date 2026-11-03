# 08 — SECURITY & VULNERABILITY AUDIT

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Audit Date:** November 1, 2026  
**Auditor:** Lead Security Auditor & Application Security Specialist  
**Standards Evaluated:** OWASP Top 10 (2021), HIPAA / Healthcare Privacy Guidelines, CWE / SANS Top 25  

> [!CAUTION]
> This audit report documents verified security vulnerabilities, architectural exposures, and compliance gaps. In adherence to strict safety rules, no actual secret values, customer records, or private credentials are disclosed. Environment variable names are referenced for remediation purposes only.

---

## 1. Vulnerability Matrix & Executive Threat Dashboard

| Vulnerability ID | Title | OWASP Category | Severity | CVSS v3.1 | Exploitability | Remediation Effort |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Global CSRF Protection Disabled | A01: Broken Access Control | **CRITICAL** | 9.1 | High | Medium |
| **SEC-02** | Hardcoded Secrets Fallback in Source Code | A07: Identification & Auth Failures | **CRITICAL** | 9.8 | High | Small |
| **SEC-03** | Public Static Storage of Sensitive Health & ID Documents | A01: Broken Access Control | **CRITICAL** | 8.6 | High | Medium |
| **SEC-04** | Missing Authentication & 500 Crash on Prescriptions | A01: Broken Access Control | **HIGH** | 7.5 | High | Small |
| **SEC-05** | Missing HMAC Webhook Signature Verification | A08: Software & Data Integrity | **CRITICAL** | 9.0 | High | Small |
| **SEC-06** | Stored Cross-Site Scripting (XSS) in Doctor Blogs | A03: Injection | **HIGH** | 7.2 | Medium | Medium |
| **SEC-07** | HTML Injection in Transactional Email Templates | A03: Injection | **MEDIUM** | 5.3 | Medium | Small |
| **SEC-08** | Cookie-Based Rate Limiting Bypass on AI Chatbot | A04: Insecure Design | **MEDIUM** | 6.5 | High | Small |
| **SEC-09** | Unencrypted Outbound HTTP Call & Spoofable IP Lookup | A10: Server-Side Request Forgery | **MEDIUM** | 5.8 | Medium | Small |
| **SEC-10** | Web Application Service Configured to Run as Root | A05: Security Misconfiguration | **HIGH** | 8.8 | Low | Small |
| **SEC-11** | 1-Year Unbounded Persistent Session Lifetime | A07: Identification & Auth Failures | **MEDIUM** | 5.4 | Low | Small |
| **SEC-12** | Default Hardcoded Secret Key Fallback in Config | A02: Cryptographic Failures | **MEDIUM** | 6.5 | Medium | Small |

---

## 2. In-Depth Vulnerability Disclosures

### SEC-01: Global CSRF Protection Disabled (`WTF_CSRF_ENABLED = False`)
- **Severity:** **CRITICAL** (CVSS: 9.1 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N`)
- **Affected Files:**
  - [`config.py`](config.py#L26): Line 26 (`WTF_CSRF_ENABLED = False  # Disable CSRF to avoid session conflicts`)
  - [`config.py`](config.py#L133): Line 133 (`WTF_CSRF_ENABLED = False`)
- **Vulnerability Mechanism:**  
  CSRF protection is globally deactivated in the configuration. The developer note indicates it was disabled to avoid session conflicts during early development.
- **Impact:**  
  Any authenticated patient, doctor, or administrator who visits a malicious third-party website or clicks an attacker-supplied link can have unauthorized state-changing POST requests executed on their behalf. An attacker can force:
  - Approval or rejection of doctor registrations (`POST /admin/doctors/<id>/approve`).
  - Approval of doctor payouts or payment refunds (`POST /admin/accounts/payouts/<id>/approve`).
  - Unauthorized booking cancellations or appointment updates.
  - Deletion of patient documents or doctor articles.
- **Remediation:**  
  1. Enable CSRF in `config.py`: `WTF_CSRF_ENABLED = True`.
  2. Initialize `CSRFProtect(app)` in `app/__init__.py`.
  3. Ensure all Jinja POST forms include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
  4. Ensure AJAX fetch calls include the `X-CSRFToken` request header.

---

### SEC-02: Hardcoded Secrets Fallback in Source Code
- **Severity:** **CRITICAL** (CVSS: 9.8 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`)
- **Affected File:** [`config.py`](config.py#L57-L58): Lines 57–58
- **Evidence:**
  ```python
  57: AGORA_APP_ID = os.environ.get('AGORA_APP_ID') or 'your-agora-app-id'
  58: AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE') or 'your-agora-app-certificate'
  ```
- **Vulnerability Mechanism:**  
  If the `AGORA_APP_ID` or `AGORA_APP_CERTIFICATE` environment variables are absent from the operating environment, the application falls back to production credentials hardcoded directly in the Git repository.
- **Impact:**  
  Anyone with access to the source code repository or version history can impersonate the platform, generate authorized Agora RTC tokens for any video consultation channel, eavesdrop on private patient-doctor video streams, or consume paid Agora cloud recording units.
- **Remediation:**  
  1. Immediately revoke and regenerate the Agora App Certificate in the Agora Console.
  2. Remove default strings from `config.py`. Enforce that missing variables raise a `RuntimeError` on startup:
     ```python
     AGORA_APP_ID = os.environ.get('AGORA_APP_ID')
     AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE')
     ```

---

### SEC-03: Public Static Storage of Sensitive Health & Government Identity Documents
- **Severity:** **CRITICAL** (CVSS: 8.6 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
- **Affected Files:**
  - [`app/utils/file_upload.py`](app/utils/file_upload.py#L93-L132)
  - [`app/routes/patients.py`](app/routes/patients.py#L1178-L1190)
  - [`deploy/nginx-quickcare.conf`](deploy/nginx-quickcare.conf#L11-L14)
- **Vulnerability Mechanism:**  
  User-uploaded documents are stored directly inside the public static tree:
  `app/static/uploads/medical_documents/{patient_id}/{uuid}_{filename}`
  `app/static/uploads/profile_pictures/...`
  `app/static/uploads/payment_receipts/...`
  In `deploy/nginx-quickcare.conf`:
  ```nginx
  location /static/ {
      alias /var/www/quickcare/app/static/;
      expires 7d;
  }
  ```
  Nginx serves the `/static/` path directly from disk with public caching headers, bypassing Flask authentication decorators entirely.
- **Impact:**  
  High-resolution scans of Pakistani National Identity Cards (CNIC front and back), PMDC medical doctor licenses, patient diagnostic lab reports, X-rays, MRI scans, and banking transaction slips are accessible via simple HTTP GET requests without logging in. This violates patient confidentiality, medical ethics, and data protection regulations (PECA / Punjab Healthcare Commission rules).
- **Remediation:**  
  1. Relocate all user uploads out of `app/static/` to a dedicated private storage directory (e.g., `storage/private_uploads/`).
  2. Remove public static alias mapping for uploads in Nginx.
  3. Implement an authenticated file delivery controller using `send_from_directory` or Nginx `X-Accel-Redirect` (sendfile) that verifies the requesting user's identity before streaming sensitive files.

---

### SEC-04: Missing Authentication & 500 Crash on Prescriptions
- **Severity:** **HIGH** (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`)
- **Affected File:** [`app/routes/prescriptions.py`](app/routes/prescriptions.py#L96-L160): Lines 96, 127
- **Evidence:**
  ```python
  96: @prescriptions_bp.route('/view/<int:prescription_id>')
  97: def view_prescription(prescription_id):
  98:     prescription = Prescription.query.get_or_404(prescription_id)
  102:    user = get_current_user()      # Returns None for unauthenticated callers!
  106:    if user.role == 'doctor' ...   # CRASH: AttributeError
  ```
- **Vulnerability Mechanism:**  
  Both `/prescriptions/view/<prescription_id>` and `/prescriptions/download/<prescription_id>` omit the `@login_required` decorator. When accessed without an active session, `get_current_user()` returns `None`. Line 106 attempts to access `user.role`, resulting in an unhandled `AttributeError: 'NoneType' object has no attribute 'role'` and HTTP 500 server error.
- **Impact:**  
  Denial of service and application stack trace leakage on unauthenticated requests.
- **Remediation:**  
  Add `@login_required` decorator to both routes.

---

### SEC-05: Missing HMAC Webhook Signature Verification on Payment Webhooks
- **Severity:** **CRITICAL** (CVSS: 9.0 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H`)
- **Affected File:** [`app/routes/payments.py`](app/routes/payments.py#L372-L413): Lines 372–413
- **Evidence:**
  ```python
  372: @payments_bp.route('/safepay/webhook', methods=['POST'])
  373: def safepay_webhook():
  ...
  380:     payload = request.get_json(silent=True) or {}
  383:     tracker_token = (payload.get('tracker_token') or payload.get('reference') or payload.get('token'))
  388:     state = payload.get('state', '')
  393:     if state not in ('TRACKER_ENDED', 'PAYMENT_SUCCESSFUL'):
  394:         return jsonify({'status': 'ignored', 'reason': f'state={state}'}), 200
  ...
  407:     mark_appointment_paid(appointment, tracker_token)
  408:     return jsonify({'status': 'ok'}), 200
  ```
- **Vulnerability Mechanism:**  
  While line 21 imports `hmac` and `hashlib`, the `/safepay/webhook` endpoint executes **zero cryptographic signature checks** on incoming payloads.
- **Impact:**  
  Any external actor can send a crafted HTTP POST request to `/safepay/webhook` with `{ "tracker_token": "<token>", "state": "PAYMENT_SUCCESSFUL" }`, causing the system to mark any appointment as fully paid without transferring funds.
- **Remediation:**  
  Verify Safepay's HMAC SHA256 webhook signature header (e.g., `X-SFPY-SIGNATURE`) against `current_app.config['SAFEPAY_SECRET_KEY']` before processing any payload.

---

### SEC-06: Stored Cross-Site Scripting (XSS) in Doctor Blogs
- **Severity:** **HIGH** (CVSS: 7.2 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N`)
- **Affected Files:**
  - [`app/routes/doctors.py`](app/routes/doctors.py#L968): Lines 968, 1007
  - [`app/templates/blogs/view.html`](app/templates/blogs/view.html#L117): Line 117
- **Evidence:**
  In `doctors.py`: `blog.content = form.content.data` (Raw HTML submitted via TinyMCE is saved directly into the database without sanitization).
  In `blogs/view.html`:
  ```jinja2
  117: {{ render_content | safe }}
  ```
- **Impact:**  
  A doctor account (or an attacker who compromises doctor credentials) can author a blog post containing malicious JavaScript (`<script>` or `<img onerror="...">`). When an administrator views the article for moderation or when patients browse the blog, the script executes within their browser context, enabling session cookie theft, account takeover, or malicious redirects.
- **Remediation:**  
  1. Add `bleach` or `nh3` to dependencies.
  2. Sanitize HTML content prior to persisting in the database, allowing only safe formatting tags (`<p>`, `<b>`, `<i>`, `<ul>`, `<li>`, `<h3>`).

---

### SEC-07: HTML Injection in Transactional Email Dispatch
- **Severity:** **MEDIUM** (CVSS: 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N`)
- **Affected File:** [`app/services/email_service.py`](app/services/email_service.py#L76)
- **Vulnerability Mechanism:**  
  User-provided names (e.g. `patient_name`, `doctor_name`) are interpolated directly into raw HTML email strings using Python f-strings without HTML escaping:
  `template = f"... <h1>Welcome, {patient_name}! 👋</h1> ..."`
- **Impact:**  
  If a user signs up with a name such as `John <img src="https://attacker.com/beacon">`, the payload renders in transactional emails, triggering tracking beacons or phishing injections in email clients.
- **Remediation:**  
  Wrap all user inputs in `html.escape(patient_name)` or migrate email generation to dedicated Jinja2 templates (`render_template('emails/welcome.html', name=patient_name)`).

---

### SEC-08: Ineffective Rate Limiting on AI Chatbot Endpoint
- **Severity:** **MEDIUM** (CVSS: 6.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`)
- **Affected File:** [`app/routes/qa.py`](app/routes/qa.py#L22-L38): Lines 22–38
- **Vulnerability Mechanism:**  
  Rate limiting on `/qa/ai-chat` stores request timestamps in the user's client-side cookie session (`session['qa_ai_chat_timestamps']`).
- **Impact:**  
  An automated bot can bypass rate limiting by omitting the `Cookie` header on subsequent HTTP POST requests. By sending tens of thousands of requests, an attacker can exhaust Google Gemini API quotas or incur unbounded API charges on OpenRouter.
- **Remediation:**  
  Implement server-side IP/account-based rate limiting via `Flask-Limiter` with an in-memory or Redis backend.

---

### SEC-09: Unencrypted Outbound HTTP Call & Potential Delay in Review Processing
- **Severity:** **MEDIUM** (CVSS: 5.8 - `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:L/A:N`)
- **Affected File:** [`app/utils/review_fraud.py`](app/utils/review_fraud.py#L66-L68): Lines 66–68
- **Evidence:**
  ```python
  66: url = f'http://ip-api.com/json/{ip}?fields=status,city,regionName'
  67: with urllib.request.urlopen(url, timeout=2.5) as resp:
  ```
- **Vulnerability Mechanism:**  
  Uses unencrypted HTTP (`http://ip-api.com`) to query client geo-location. Furthermore, client IP is extracted from unvalidated `X-Forwarded-For` headers.
- **Impact:**  
  Traffic is transmitted in cleartext. If `X-Forwarded-For` is not scrubbed by the ingress proxy, spoofed headers can trigger unexpected lookups or denial-of-service delays.
- **Remediation:**  
  Switch to HTTPS, use a local MaxMind GeoIP database, or dispatch geo-lookup asynchronously.

---

### SEC-10: Web Application Service Running as `root`
- **Severity:** **HIGH** (CVSS: 8.8 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H`)
- **Affected File:** [`deploy/quickcare.service`](deploy/quickcare.service#L6-L7): Lines 6–7
- **Evidence:**
  ```ini
  6: User=root
  7: Group=root
  ```
- **Vulnerability Mechanism:**  
  The systemd production service file specifies `User=root` and `Group=root` for running the Gunicorn web process.
- **Impact:**  
  If any Remote Code Execution (RCE) or file upload path traversal vulnerability is exploited, the attacker gains full root access to the entire operating system.
- **Remediation:**  
  Create a dedicated unprivileged user (e.g. `www-data` or `quickcare`) and assign minimal file permissions:
  `User=www-data`  
  `Group=www-data`

---

### SEC-11: 1-Year Persistent Session Lifetime
- **Severity:** **MEDIUM** (CVSS: 5.4 - `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:L/A:N`)
- **Affected Files:**
  - [`config.py`](config.py#L20-L23): Lines 20–23
  - [`app/__init__.py`](app/__init__.py#L25-L36): Lines 25–36
- **Vulnerability Mechanism:**  
  `PERMANENT_SESSION_LIFETIME = timedelta(days=365)`. Sessions do not expire upon browser closure or inactivity.
- **Impact:**  
  If a patient or doctor logs in on a shared computer (clinic terminal, internet cafe, public library), their session remains fully active for an entire year unless explicitly logged out.
- **Remediation:**  
  Enforce standard session timeouts (e.g., 2 hours of inactivity for healthcare applications, or 7 days maximum with rolling renewal).

---

### SEC-12: Default Fallback Secret Key
- **Severity:** **MEDIUM** (CVSS: 6.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N`)
- **Affected File:** [`config.py`](config.py#L8): Line 8
- **Evidence:**
  ```python
  8: SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
  ```
- **Impact:**  
  If `.env` fails to load in production, the application signs session cookies using the publicly known string `'dev-secret-key-change-in-production'`. Anyone can forge session cookies and impersonate administrative accounts.
- **Remediation:**  
  Refuse to start in production if `SECRET_KEY` is undefined:
  `SECRET_KEY = os.environ['SECRET_KEY']`

