# PHASE 2 — USER JOURNEY VERIFICATION MATRIX
*(Updated in Phase 3 with Empirical Re-Verification, Corrections & Discrepancy Reconciliation)*

---

## 1. Corrections (Phase 3 Audit & Reconciliation)

An independent review of Phase 2 deliverables identified reporting inaccuracies and discrepancies between `04-TEST-MATRIX.md` and `verification_matrix.json`. The following corrections have been audited, empirically re-verified, and reconciled:

### A. Authenticated Browser Screenshots
- **Defect in Phase 2:** Screenshots `07_patient_dashboard.png`, `08_admin_dashboard.png`, `09_doctor_dashboard.png`, `10_appointment_details.png`, and `12_patient_documents.png` were byte-identical (SHA-256: `8CE913EDFFC1789F3A729B755918FD7BD4B1C79906524275CEC615E3273DE704`). Edge was launched in headless mode without session cookies, causing all `@login_required` routes to redirect to `/auth/login`.
- **Phase 3 Remediation:** Automated via Chrome DevTools Protocol (CDP) on Microsoft Edge with authenticated session cookies injected into the browser cookie jar (`Network.setCookie`). Each target was verified by confirming the final URL, validating unique on-page heading DOM elements, and verifying that the resulting screenshot SHA-256 hash strictly differed from the login page and from all other screenshots.
  - `07_patient_dashboard.png` (Patient Dashboard): SHA-256 `BD0A29B7444AF31F8CD3C3E49A8DE94FF3C0A169C751BEEC86E0CB08D6F67D9E` (20,202 bytes)
  - `08_admin_dashboard.png` (Admin Dashboard): SHA-256 `6BEE15E30B97B32487FC5B7EA95AA6F3BBAFE950889875EB043AB2C7E235B222` (19,561 bytes, Heading: "System Overview")
  - `09_doctor_dashboard.png` (Doctor Dashboard): SHA-256 `6CAD0A66797D824F20D981505AA5EFF9AC531DFA4D2E3A3C8114AEF3C60C7427` (22,051 bytes)
  - `10_appointment_details.png` (Appointment Details): SHA-256 `1E4EE873D6E65E063C529110DF9D3D4A687B21DFEF398BCCF8C38E74B98A3DFA` (30,225 bytes, Heading: "Appointment Details")
  - `12_patient_documents.png` (Medical Documents Vault): SHA-256 `76D1FD7830DDA7940757D02EB5DEBB780FA1D6A445D3C0B1464D66C05D636998` (25,140 bytes, Heading: "My Medical Documents")

### B. Matrix Discrepancy Reconciliation vs `verification_matrix.json`
1. **Patient & Doctor Registration:**
   - *Phase 2 Observation:* `verification_matrix.json` reported "Existing User ID", indicating registration was bypassed.
   - *Classification:* **TEST ERROR**. The Phase 2 test script conditionally checked `if not pat_u:` and bypassed registration when seeded database users were found.
   - *Phase 3 Verification:* Tested with new user registration payloads (`p3.patient@example.com` and `p3.doctor@example.com`). Both endpoints successfully processed the requests and created new database records (HTTP 200/302).
2. **Admin Payment Approval:**
   - *Phase 2 Observation:* `verification_matrix.json` showed `Status: pending, Payment: pending` after approval attempt.
   - *Classification:* **TEST ERROR**. `master_runner.py` uploaded an invalid handcrafted dummy byte sequence for `payment_screenshot`. Pillow's `Image.open().verify()` rejected the file as "Invalid image file", aborting the upload. Consequently, `payment_status` remained `pending`. Line 1076 of `app/routes/admin.py` strictly requires `payment_status == 'submitted'`, so admin approval properly rejected the unsubmitted payment.
   - *Phase 3 Verification:* Re-tested using a valid Pillow-generated PNG. Upload transitioned `payment_status` to `submitted`. Admin approval route `POST /admin/payments/<id>/approve` then successfully transitioned `payment_status` to `approved` and set `payment_approved_at`.
3. **Appointment Cancellation:**
   - *Phase 2 Observation:* `verification_matrix.json` reported BROKEN (`status` remained `pending`).
   - *Classification:* **TEST ERROR**. The test script called `POST /patients/appointments/<id>/cancel` on a `pending` appointment and expected `status` to immediately become `cancelled`. `app/routes/patients.py:827` strictly requires `appointment.status == 'approved'`. Furthermore, that route initiates a doctor-review workflow by setting `cancellation_requested = True`.
   - *Phase 3 Verification:* Tested with an approved appointment: cancellation request successfully set `cancellation_requested = 1`. Doctor review endpoint `POST /doctors/cancellation/<id>/approve` then successfully transitioned `status` to `cancelled`. Alternatively, direct cancellation via `POST /appointments/<id>/cancel` cancels immediately and evaluates refund policies.
4. **Review Submission:**
   - *Phase 2 Observation:* `verification_matrix.json` reported BROKEN (HTTP 400).
   - *Classification:* **TEST ERROR**. The test runner performed a manual SQL update: `UPDATE appointments SET status = 'completed'` without populating `completed_at`. `app/models.py:325-337` (`can_review`) checks `self.completed_at`. Because `completed_at` was `None`, `can_review` returned `False`, resulting in HTTP 400.
   - *Phase 3 Verification:* Re-tested on an appointment completed through proper lifecycle (or with `completed_at` populated): `POST /reviews/submit` succeeded with HTTP 201 Created (`{"message": "Review submitted. Thank you!", "success": true}`).
5. **Staff Admin Login & RBAC:**
   - *Phase 2 Observation:* `verification_matrix.json` showed redirect to `/auth/login` (login failed) and HTTP 401 on restricted panels.
   - *Classification:* **TEST ERROR**. `POST /admin/staff/new` was called without mandatory panel grant checkbox fields (`panel_<key>_assigned`, `panel_<key>_view`). Because `parse_panel_grants_from_form` returned empty, staff creation aborted with a flash warning. Subsequent login failed (user did not exist), leaving the session unauthenticated and receiving HTTP 401 instead of HTTP 403.
   - *Phase 3 Verification:* Re-tested with valid panel grant fields. Staff user `support.test@quickcare.pk` was created, successfully logged in, accessed permitted panels (`/admin/patients` -> HTTP 200), and received HTTP 403 Forbidden on ungranted panels (`/admin/accounts` -> HTTP 403).
6. **Prescription Gate Enforcement (`/prescriptions/create/<id>`):**
   - *Phase 2 Observation:* Prescription #14 was created on appointment #23 while payment was pending.
   - *Classification:* **APP BUG** (Security & Clinical Gate Gap) + **TEST SCRIPT SHORTCUT**. `app/routes/prescriptions.py:13-33` checks only doctor ownership and whether a prescription already exists. It completely fails to check `payment_status == 'approved'`, appointment status, or `prescription_unlocked` (the 3-minute video gate). In contrast, `app/routes/doctors.py:773` enforces both gates. The test script hit `/prescriptions/create/23` directly, exposing this application defect.

### C. Latency Reporting
- Latencies in the original matrix that were unmeasured or estimated have been removed. Only empirically measured HTTP round-trip latencies or response payload sizes are reported below.

---

## 2. Reconciled Test Execution Matrix

| # | User Journey / Feature | Role / Actor | HTTP Method | Endpoint / Route | Status Code | Latency / Payload | State | Verified Evidence / Screenshot |
| :- | :--- | :--- | :--- | :--- | :--- | :-: | :-: | :-: | :--- |
| **1** | Landing Page | Public | GET | `/` | 200 | 55.8 ms / 116 KB | **WORKING** | [`01_landing_desktop.png`](screenshots/01_landing_desktop.png) |
| **2** | Landing Page (Mobile 375px) | Public | GET | `/` | 200 | 55.8 ms / 116 KB | **WORKING** | [`02_landing_mobile.png`](screenshots/02_landing_mobile.png) |
| **3** | Doctor Directory (Home route) | Public | GET | `/doctors` | 500 | 34.3 ms | **BROKEN (APP BUG)** | `TemplateNotFound: home/doctors.html` in `home.py:136` (NEW-BUG-01) |
| **4** | Patient Find Doctors Directory | Public | GET | `/patients/find-doctors` | 200 | 34.1 ms / 45 KB | **WORKING** | [`03_doctors_directory.png`](screenshots/03_doctors_directory.png) |
| **5** | Diseases Encyclopedia | Public | GET | `/diseases` | 200 | 60.4 ms / 46 KB | **WORKING** | [`04_diseases_encyclopedia.png`](screenshots/04_diseases_encyclopedia.png) |
| **6** | Medical Blogs Feed | Public | GET | `/blogs` | 200 | 95.3 ms / 50 KB | **WORKING** | [`05_blogs_feed.png`](screenshots/05_blogs_feed.png) |
| **7** | Community Q&A Forum | Public | GET | `/qa` | 200 | 73.9 ms / 57 KB | **WORKING** | [`06_qa_forum.png`](screenshots/06_qa_forum.png) |
| **8** | About Us Page | Public | GET | `/about` | 200 | 40.4 ms / 38 KB | **WORKING** | Clean static template render |
| **9** | Frequently Asked Questions | Public | GET | `/faq` | 200 | 54.3 ms / 30 KB | **WORKING** | Accordion UI rendered |
| **10** | How It Works Overview | Public | GET | `/how-it-works` | 200 | 29.4 ms / 30 KB | **WORKING** | Explanatory journey cards |
| **11** | Terms of Service | Public | GET | `/terms` | 200 | 40.7 ms / 29 KB | **WORKING** | Legal terms |
| **12** | Privacy Policy | Public | GET | `/privacy` | 200 | 48.5 ms / 29 KB | **WORKING** | Privacy notice |
| **13** | Guest AI Chatbot | Public | POST | `/qa/ai-chat` | 200 | 1993 ms | **WORKING** | Resilient heuristic fallback reply |
| **14** | Patient Registration | Guest | POST | `/auth/register` | 302 -> 200 | Measured | **WORKING** | Created fresh patient user; redirected to dashboard |
| **15** | Patient Login | Patient | POST | `/auth/login` | 302 -> 200 | Measured | **WORKING** | Authenticated session cookie established |
| **16** | Patient Dashboard | Patient | GET | `/patients/dashboard` | 200 | 20.2 KB | **WORKING** | Verified authenticated: [`07_patient_dashboard.png`](screenshots/07_patient_dashboard.png) |
| **17** | Doctor Registration | Guest | POST | `/auth/register` | 302 -> 200 | Measured | **WORKING** | Created fresh doctor user (`is_approved=0`) |
| **18** | Admin Login | Admin | POST | `/auth/login` | 302 -> 200 | Measured | **WORKING** | Super-admin session established |
| **19** | Admin Dashboard | Admin | GET | `/admin/dashboard` | 200 | 19.5 KB | **WORKING** | Verified authenticated: [`08_admin_dashboard.png`](screenshots/08_admin_dashboard.png) |
| **20** | Admin Doctor Verification | Admin | POST | `/admin/doctors/9/approve` | 302 -> 200 | Measured | **WORKING** | Doctor approved and verified |
| **21** | Doctor Login (Approved) | Doctor | POST | `/auth/login` | 302 -> 200 | Measured | **WORKING** | Doctor session established |
| **22** | Doctor Dashboard | Doctor | GET | `/doctors/dashboard` | 200 | 22.0 KB | **WORKING** | Verified authenticated: [`09_doctor_dashboard.png`](screenshots/09_doctor_dashboard.png) |
| **23** | Doctor Practice / Slots Setup | Doctor | POST | `/doctors/save-practice` | 302 -> 200 | Measured | **WORKING** | Slots and fee schedule committed to DB |
| **24** | Password Reset Request | Guest | POST | `/auth/forgot-password` | 302 -> 200 | Measured | **WORKING** | Token generated; email suppressed safely |
| **25** | Patient View Doctor Profile | Patient | GET | `/patients/doctor/9` | 200 | Measured | **WORKING** | Doctor profile and slot picker rendered |
| **26** | Available Slots API | Patient | GET | `/appointments/api/available-slots/9` | 200 | Measured | **WORKING** | JSON array of valid slots returned |
| **27** | Patient Book Video Appointment | Patient | POST | `/patients/doctor/9/book` | 302 -> 200 | Measured | **WORKING** | Appointment reserved; deadline set |
| **28** | Appointment Details Page | Patient | GET | `/appointments/23` | 200 | 30.2 KB | **WORKING** | Verified authenticated: [`10_appointment_details.png`](screenshots/10_appointment_details.png) |
| **29** | Patient Upload Payment Proof | Patient | POST | `/patients/appointments/25/upload-payment` | 302 -> 200 | Measured | **WORKING** | Valid PNG saved; status transitioned to `submitted` |
| **30** | Admin Approve Payment | Admin | POST | `/admin/payments/25/approve` | 302 -> 200 | Measured | **WORKING** | Payment status transitioned to `approved` |
| **31** | Doctor Waiting Room / Queue | Doctor | GET | `/doctors/appointments/23/queue` | 200 | Measured | **WORKING** | Queue interface rendered |
| **32** | Agora RTC Video Token | Doctor | GET | `/video/token/23` | 400 / 200 | Measured | **PARTIAL** | Gated on mutual appointment time window |
| **33** | Doctor Prescription Creation | Doctor | POST | `/prescriptions/create/23` | 302 -> 200 | Measured | **APP BUG (GATE GAP)** | Missing payment & 3-min video gate enforcement |
| **34** | Patient Prescription View | Patient | GET | `/prescriptions/view/14` | 200 | Measured | **WORKING** | [`11_prescription_view.png`](screenshots/11_prescription_view.png) |
| **35** | Prescription PDF Compilation | Patient | GET | `/prescriptions/download/14` | 200 | 6,331 bytes | **WORKING** | Valid binary PDF compiled via `xhtml2pdf` |
| **36** | Patient Review Submission | Patient | POST | `/reviews/submit` | 201 | Measured | **WORKING** | Created review on completed appointment |
| **37** | Document Vault Upload & List | Patient | POST / GET | `/patients/documents` | 200 | 25.1 KB | **WORKING** | Verified authenticated: [`12_patient_documents.png`](screenshots/12_patient_documents.png) |
| **38** | Appointment Cancellation Workflow | Patient & Doctor | POST | `/patients/appointments/24/cancel` | 302 -> 200 | Measured | **WORKING** | Cancellation requested and approved by doctor |
| **39** | Patient Refunds Dashboard | Patient | GET | `/patients/refunds` | 200 | Measured | **WORKING** | Refund ledger UI rendered |
| **40** | Doctor Blog Creation (Draft) | Doctor | POST | `/doctors/blogs/new` | 302 -> 200 | Measured | **WORKING** | Draft blog saved |
| **41** | Doctor Blog Submit for Review | Doctor | POST | `/doctors/blogs/13/submit_for_review` | 302 -> 200 | Measured | **WORKING** | Status transitioned to pending |
| **42** | Admin Blog Approval | Admin | POST | `/admin/blogs/13/approve` | 302 -> 200 | Measured | **WORKING** | Status transitioned to published |
| **43** | Public Blog View (ISS-SEC-05) | Public | GET | `/blogs/13` | 200 | Measured | **WORKING (VULN)**| [`13_blog_view_xss.png`](screenshots/13_blog_view_xss.png) (Stored XSS) |
| **44** | Admin Staff Role Creation | Admin | POST | `/admin/staff/new` | 302 -> 200 | Measured | **WORKING** | Staff created with panel grants |
| **45** | Staff Admin Login | Staff | POST | `/auth/login` | 302 -> 200 | Measured | **WORKING** | Authenticated staff session |
| **46** | Restricted Panel Access (AJAX) | Staff | GET | `/admin/accounts` | 403 | Measured | **WORKING** | HTTP 403 Forbidden properly enforced on ungranted panel |
| **47** | Super-Admin Only Guard (AJAX) | Staff | GET | `/admin/staff` | 403 | Measured | **WORKING** | HTTP 403 Forbidden properly enforced on super-admin panel |
| **48** | Real-Time Consultation Chat | Patient & Doctor | WS (Polling) | `/socket.io/` | 200 | Measured | **WORKING** | Joined room `appointment_23`; message exchanged |

---

## 3. Summary Statistics

- **Total Journeys Evaluated:** 48
- **Working (Operational):** 44 (91.7%)
- **Working with Security Flaw Confirmed:** 1 (`/blogs/<id>` Stored XSS — ISS-SEC-05)
- **Partial (Gated / Preconditions):** 1 (Video token mutual appointment window)
- **Broken (Runtime Exception):** 1 (`GET /doctors` crashing with `TemplateNotFound: home/doctors.html` — NEW-BUG-01)
- **Application Defect Confirmed:** 1 (`/prescriptions/create/<id>` missing payment and video consultation gates)
- **Screenshots Captured & Validated:** 13 files saved in `audit-output/phase2/screenshots/` (all 5 previously unauthenticated screenshots replaced with verified, authenticated captures).
