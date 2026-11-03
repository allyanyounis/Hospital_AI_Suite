# PHASE 3 — DELIVERABLE 04: AUTOMATED TEST SUITE & COVERAGE REPORT

**Author:** Antigravity Principal QA Automation Engineer & Auditor  
**Date:** November 1, 2026  
**Test Framework:** Pytest 9.2.0 | Coverage.py 7.17.0  
**Runtime Environment:** Windows 10/11 | Python 3.11.9 | SQLite 3  
**Target Branch:** `phase-3-bugfix` (Commit: `8134b43`)  

---

## 1. Test Suite Summary Baseline

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP
configfile: pytest.ini
testpaths: tests
plugins: cov-7.1.0
collected 38 items

================ 36 passed, 2 xfailed, 120 warnings in 18.03s =================
```

- **Total Test Cases Executed:** 38
- **Passed:** 36 (100% of non-deferred tests)
- **XFailed (Expected Failures):** 2 (`ISS-SEC-01` CSRF token enforcement, `ISS-SEC-03` static uploads access control; formally deferred to Phase 4 hardening)
- **Failed / Regressed:** 0 (Zero regressions)

---

## 2. Test Execution Breakdown by Module

### 2.1 `tests/test_appointments.py` (4 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_booking_creation` | Verified patient can book appointment with valid slot and details | **PASSED** |
| `test_booking_unapproved_doctor_rejected` | Verified booking rejected for unapproved/pending doctor profiles | **PASSED** |
| `test_admin_payment_approval_and_commission_split` | Verified admin approval updates status and executes 80/20 fee split | **PASSED** |
| `test_cleanup_expired_payments_reuses_app_context_perf_02` | Verified background job reuses active application context (`ISS-PERF-02`) | **PASSED** |

### 2.2 `tests/test_auth.py` (7 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_patient_registration` | Verified patient sign-up creates user, patient profile, and hashes password | **PASSED** |
| `test_doctor_registration` | Verified doctor registration creates pending profile awaiting admin approval | **PASSED** |
| `test_login_valid_credentials` | Verified session creation and role assignment on correct login | **PASSED** |
| `test_login_invalid_password` | Verified rejected authentication on invalid credentials | **PASSED** |
| `test_login_inactive_user` | Verified de-activated accounts are blocked from logging in | **PASSED** |
| `test_logout` | Verified session cookie clearing upon logout | **PASSED** |
| `test_forgot_password_request` | Verified password reset token generation and submission workflow | **PASSED** |

### 2.3 `tests/test_chat.py` (4 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_chat_page_access_authorized_patient` | Verified authenticated patient can enter appointment chat lobby | **PASSED** |
| `test_chat_page_access_authorized_doctor` | Verified assigned doctor can open appointment consultation chat | **PASSED** |
| `test_chat_unpaid_patient_payment_gate` | Verified unpaid appointment chat access is strictly blocked | **PASSED** |
| `test_ai_chatbot_gemini_model_configurable` | Verified `GEMINI_MODEL` override and prompt URL construction (`Fix 9`) | **PASSED** |

### 2.4 `tests/test_home.py` (3 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_public_doctors_route_redirect_new_bug_01` | Verified `GET /doctors` redirects to `/patients/find-doctors` (`NEW-BUG-01`) | **PASSED** |
| `test_public_doctors_route_followed_ok` | Verified redirect target renders doctor directory with HTTP 200 | **PASSED** |
| `test_navbar_container_div_closed_fe_01` | Verified navbar container `<div>` is closed before `</nav>` tag (`ISS-FE-01`) | **PASSED** |

### 2.5 `tests/test_prescriptions.py` (10 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_doctor_creates_prescription` | Verified digital prescription creation with multi-item medicines | **PASSED** |
| `test_patient_views_prescription` | Verified authenticated patient can view medical prescription | **PASSED** |
| `test_unauthenticated_prescription_view_redirects` | Verified anonymous access redirects to login rather than 500 (`ISS-BUG-01`) | **PASSED** |
| `test_unauthenticated_prescription_download_redirects` | Verified anonymous PDF download redirects to login (`ISS-BUG-01`) | **PASSED** |
| `test_authenticated_prescription_pdf_download` | Verified authenticated PDF generation via `xhtml2pdf` | **PASSED** |
| `test_prescription_create_unpaid_blocked` | Verified unpaid appointment blocks prescription creation (`ISS-CLIN-01`) | **PASSED** |
| `test_prescription_create_video_without_unlock_blocked` | Verified video appointment without 3-min call blocks prescription | **PASSED** |
| `test_prescription_create_video_with_unlock_allowed` | Verified video appointment with 3-min unlock allows prescription | **PASSED** |
| `test_prescription_create_physical_paid_and_approved_allowed` | Verified physical in-clinic appointment bypasses video gate | **PASSED** |
| `test_prescription_create_different_doctor_blocked` | Verified unassigned doctor cannot issue prescription for appointment | **PASSED** |

### 2.6 `tests/test_refunds.py` (5 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_patient_cancellation_request_allowed_more_than_3h` | Verified patient can request cancellation > 3 hours prior | **PASSED** |
| `test_patient_cancellation_blocked_less_than_3h` | Verified cancellation request blocked < 3 hours prior | **PASSED** |
| `test_doctor_approves_cancellation` | Verified doctor review approves cancellation and marks refund eligible | **PASSED** |
| `test_cancellation_window_clock_patched_under_3h` | Clock-patched PKT test: 2h before slot strictly blocked (`ISS-BUG-02`) | **PASSED** |
| `test_cancellation_window_clock_patched_over_3h` | Clock-patched PKT test: 4h before slot allows cancellation (`ISS-BUG-02`) | **PASSED** |

### 2.7 `tests/test_run.py` (2 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_dev_server_default_host_is_loopback` | Verified server binds to `127.0.0.1` by default for safety (`SEC-DEV`) | **PASSED** |
| `test_dev_server_host_bind_all_flag` | Verified server permits `0.0.0.0` when `BIND_ALL_INTERFACES=true` | **PASSED** |

### 2.8 `tests/test_security.py` (3 Tests)
| Test Identifier | Description | Result |
| :--- | :--- | :---: |
| `test_csrf_protection_enforced_xfail` | Global CSRF validation on mutating POST endpoints | **XFAIL** (Phase 4) |
| `test_static_upload_access_control_xfail` | Direct access prevention for sensitive document uploads | **XFAIL** (Phase 4) |
| `test_admin_staff_rbac_ajax_403` | Verified staff RBAC returns HTTP 403 on ungranted panels | **PASSED** |

---

## 3. Code Coverage Telemetry

The test suite exercises 31% of the total application codebase (2,390 out of 7,731 statements). High coverage was achieved across critical business domains:

| Module / Component | Total Statements | Missed | Statement Coverage | Health Status |
| :--- | :-: | :-: | :-: | :---: |
| `app/models.py` | 519 | 40 | **92%** | High |
| `app/utils/pdf_generator.py` | 21 | 2 | **90%** | High |
| `app/forms/__init__.py` | 130 | 18 | **86%** | High |
| `app/utils/appointment_workflow.py` | 33 | 5 | **85%** | High |
| `app/utils/accounts_migration.py` | 13 | 2 | **85%** | High |
| `app/__init__.py` | 148 | 27 | **82%** | High |
| `app/utils/admin_rbac_migration.py` | 30 | 7 | **77%** | Medium-High |
| `app/routes/prescriptions.py` | 100 | 26 | **74%** | Medium-High |
| `app/utils/timezone.py` | 24 | 8 | **67%** | Medium |
| `app/routes/home.py` | 77 | 33 | **57%** | Medium |
| `app/utils/slots.py` | 99 | 45 | **55%** | Medium |
| `app/routes/auth.py` | 348 | 189 | **46%** | Medium |
| `app/utils/auth.py` | 120 | 66 | **45%** | Medium |
| `app/services/email_service.py` | 91 | 49 | **46%** | Medium |
| `app/utils/practice_organizer.py` | 35 | 20 | **43%** | Medium |
| `app/services/accounts_service.py` | 66 | 40 | **39%** | Medium |
| `app/utils/admin_permissions.py` | 155 | 95 | **39%** | Medium |
| `app/utils/cleanup_expired_payments.py` | 59 | 40 | **32%** | Medium |
| `app/routes/diseases.py` | 38 | 26 | **32%** | Low |
| `app/utils/appointment_status.py` | 71 | 50 | **30%** | Low |
| `app/routes/patients.py` | 768 | 550 | **28%** | Low |
| `app/routes/admin_staff.py` | 107 | 80 | **25%** | Low |
| `app/routes/blogs.py` | 50 | 38 | **24%** | Low |
| `app/utils/review_fraud.py` | 94 | 71 | **24%** | Low |
| `app/routes/admin.py` | 872 | 690 | **21%** | Low |
| `app/routes/reviews.py` | 56 | 44 | **21%** | Low |
| `app/services/ai_chatbot_service.py` | 426 | 343 | **19%** | Low |
| `app/routes/payments.py` | 175 | 143 | **18%** | Low |
| `app/routes/doctors.py` | 915 | 799 | **13%** | Low |
| `app/routes/video.py` | 237 | 209 | **12%** | Low |
| `app/routes/qa.py` | 218 | 191 | **12%** | Low |
| **PROJECT TOTAL** | **7,731** | **5,341** | **31%** | **Baseline Established** |

---

## 4. Database Protection Audit

Cryptographic SHA-256 integrity check confirms that the original SQLite database was never opened or modified during test execution or application runs:

| Database File | Expected SHA-256 Checksum | Final Measured SHA-256 Checksum | Verification Status |
| :--- | :--- | :--- | :---: |
| `instance/backups/quickcare_dev_original.db` | `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850` | `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850` | **IDENTICAL** |
| `instance/quickcare_dev.db` | `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850` | `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850` | **UNTOUCHED** |

