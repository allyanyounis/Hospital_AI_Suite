# PHASE 2 — AUTOMATED TEST BASELINE & CODE COVERAGE REPORT

## 1. Executive Summary

A clean, modular, and repeatable automated test suite has been established in `tests/` using **pytest** and **pytest-cov**. The test suite executes in **8.53 seconds** against an isolated SQLite test database with all third-party external services (Agora, DigitalOcean Spaces, Safepay, Gemini AI, Flask-Mail) mocked or suppressed.

Known defects and security vulnerabilities identified in Phase 1 are explicitly marked with `@pytest.mark.xfail`, providing an honest, reproducible baseline that passes in CI/CD while tracking issues to be resolved in future phases.

---

## 2. Test Execution Summary

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP
plugins: cov-7.1.0
collected 23 items

tests/test_appointments.py::test_booking_creation PASSED                 [  4%]
tests/test_appointments.py::test_booking_unapproved_doctor_rejected PASSED [  8%]
tests/test_appointments.py::test_admin_payment_approval_and_commission_split PASSED [ 13%]
tests/test_auth.py::test_patient_registration PASSED                     [ 17%]
tests/test_auth.py::test_doctor_registration PASSED                      [ 21%]
tests/test_auth.py::test_login_valid_credentials PASSED                  [ 26%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 30%]
tests/test_auth.py::test_login_inactive_user PASSED                      [ 34%]
tests/test_auth.py::test_logout PASSED                                   [ 39%]
tests/test_auth.py::test_forgot_password_request PASSED                  [ 43%]
tests/test_chat.py::test_chat_page_access_authorized_patient PASSED      [ 47%]
tests/test_chat.py::test_chat_page_access_authorized_doctor PASSED       [ 52%]
tests/test_chat.py::test_chat_unpaid_patient_payment_gate PASSED         [ 56%]
tests/test_prescriptions.py::test_doctor_creates_prescription PASSED     [ 60%]
tests/test_prescriptions.py::test_patient_views_prescription PASSED      [ 65%]
tests/test_prescriptions.py::test_unauthenticated_prescription_view_xfail XFAIL [ 69%]
tests/test_prescriptions.py::test_authenticated_prescription_pdf_download PASSED [ 73%]
tests/test_refunds.py::test_patient_cancellation_request_allowed_more_than_3h PASSED [ 78%]
tests/test_refunds.py::test_patient_cancellation_blocked_less_than_3h PASSED [ 82%]
tests/test_refunds.py::test_doctor_approves_cancellation PASSED          [ 86%]
tests/test_security.py::test_csrf_protection_enforced_xfail XFAIL (ISS-SEC-01) [ 91%]
tests/test_security.py::test_static_upload_access_control_xfail XFAIL (ISS-SEC-03) [ 95%]
tests/test_security.py::test_admin_staff_rbac_ajax_403 PASSED            [100%]

================= 20 passed, 3 xfailed in 8.53s ==================
```

### Metrics Breakdown
- **Total Test Cases:** 23
- **Passed:** 20 (87.0%)
- **Expected Failures (`xfail`):** 3 (13.0%)
- **Unexpected Failures:** **0**
- **Errors:** **0**
- **Test Duration:** 8.53 seconds

---

## 3. Registered XFAIL Known Issues

| Test Identifier | Associated Issue ID | Expected Behavior (Fixed) | Current Behavior (Baseline) |
| :--- | :--- | :--- | :--- |
| `test_unauthenticated_prescription_view_xfail` | `ISS-BUG-01` | HTTP 302 Redirect to `/auth/login` | HTTP 500 (`AttributeError: 'NoneType' object has no attribute 'role'`) |
| `test_csrf_protection_enforced_xfail` | `ISS-SEC-01` | HTTP 400 Bad Request (Missing CSRF Token) | HTTP 200/302 (Accepted without CSRF token because `WTF_CSRF_ENABLED=False`) |
| `test_static_upload_access_control_xfail` | `ISS-SEC-03` | HTTP 401 / 403 / 404 Access Denied | HTTP 200 (Static uploaded documents served publicly without session) |

---

## 4. Code Coverage Analysis (`pytest-cov`)

Coverage measurement spans all application packages under `app/`:

```text
Name                                     Stmts   Miss  Cover
------------------------------------------------------------
app\__init__.py                            148     27    82%
app\database.py                              2      0   100%
app\forms\__init__.py                      130     18    86%
app\jobs\__init__.py                         0      0   100%
app\jobs\check_expired_appointments.py      68     68     0%
app\models.py                              519     39    92%
app\routes\admin.py                        872    690    21%
app\routes\admin_staff.py                  107     80    25%
app\routes\appointments.py                 839    751    10%
app\routes\auth.py                         348    189    46%
app\routes\blogs.py                         50     38    24%
app\routes\diseases.py                      38     26    32%
app\routes\doctors.py                      914    799    13%
app\routes\home.py                          97     54    44%
app\routes\patients.py                     767    561    27%
app\routes\payments.py                     175    143    18%
app\routes\prescriptions.py                 91     28    69%
app\routes\qa.py                           218    191    12%
app\routes\reviews.py                       56     44    21%
app\routes\video.py                        237    209    12%
app\scheduler.py                            32     25    22%
app\services\accounts_service.py            66     40    39%
app\services\ai_chatbot_service.py         425    356    16%
app\services\email_service.py               91     49    46%
app\services\recording_service.py          212    186    12%
app\services\socketio_events.py            272    243    11%
app\utils\accounts_migration.py             13      2    85%
app\utils\admin_permissions.py             155     95    39%
app\utils\admin_rbac_migration.py           30      7    77%
app\utils\appointment_status.py             71     50    30%
app\utils\appointment_workflow.py           25      4    84%
app\utils\auth.py                          120     65    46%
app\utils\blog_covers.py                    11      7    36%
app\utils\categories.py                     44     23    48%
app\utils\file_upload.py                    81     67    17%
app\utils\geocoding.py                      27     20    26%
app\utils\pdf_generator.py                  21      2    90%
app\utils\practice_organizer.py             35     20    43%
app\utils\qa_migration.py                   14      2    86%
app\utils\review_flow_migration.py          14      2    86%
app\utils\review_fraud.py                   94     71    24%
app\utils\review_fraud_migration.py         19      4    79%
app\utils\slots.py                          99     45    55%
app\utils\timezone.py                       24      9    62%
------------------------------------------------------------
TOTAL                                     7671   5349    30%
```

### Coverage Highlights
- **Total Executable Statements:** 7,671
- **Missed Statements:** 5,349
- **Overall Line Coverage:** **30%**
- **High-Coverage Core Modules:**
  - `app/database.py`: 100%
  - `app/models.py`: 92% (Data models, schemas, relationships)
  - `app/utils/pdf_generator.py`: 90% (PDF layout engine with `xhtml2pdf`)
  - `app/forms/__init__.py`: 86% (WTForms validation logic)
  - `app/utils/qa_migration.py`: 86%
  - `app/utils/accounts_migration.py`: 85%
  - `app/utils/appointment_workflow.py`: 84%
  - `app/__init__.py`: 78% (App factory & blueprint registration)
  - `app/utils/admin_rbac_migration.py`: 77%
  - `app/routes/prescriptions.py`: 69% (Clinical digital prescriptions)
  - `app/utils/timezone.py`: 62%
  - `app/utils/slots.py`: 55%

---

## 5. Running the Test Suite Locally

To run the baseline test suite at any time:
```powershell
cd "Quick Care FYP"
.\venv\Scripts\Activate.ps1
pytest --cov=app -v
```

