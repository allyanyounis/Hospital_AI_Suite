# 04 — MODULE & FEATURE INVENTORY

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Audit Date:** November 1, 2026  
**Auditor:** Senior Full-Stack Engineer & Technical Project Lead  

---

## 1. Inventory Summary & Status Classification

Across the application's 14 blueprints, **168 distinct route endpoints** and **8 WebSocket/background events** were identified and reverse-engineered.

### Status Definitions:
- **Confirmed Implemented (Static Review):** Implementation logic, ORM queries, and view templates are structurally complete and consistent with specifications.
- **Implemented (Runtime Blocked):** Implemented in source code, but runtime verification is blocked by missing local environment dependencies (`flask` not installed in local environment).
- **Partially Implemented:** Functional, but contains explicit `TODO` markers, unhandled edge cases, or stubbed notifications.
- **Broken / Vulnerable:** Contains a verified logic defect, crash on specific input, or critical security loophole.
- **Duplicate / Redundant:** Endpoint logic is duplicated across multiple blueprints under different URL paths.

---

## 2. Comprehensive Module Feature Register

### 2.1 Authentication & Profile Module (`auth_bp`) — `/auth`
*Source: `app/routes/auth.py` | Templates: `app/templates/auth/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET, POST /auth/login` | `login()` | Public | `User`, `Doctor`, `Patient`, `Admin` | Implemented (Runtime Blocked) | Role-based post-login redirection; permanent 1-year session cookie; CSRF disabled. |
| `GET, POST /auth/register` | `register()` | Public | `User`, `Doctor`, `Patient` | Implemented (Runtime Blocked) | Unified registration for both doctor and patient roles; saves CNIC images to static folder. |
| `GET, POST /auth/forgot-password` | `forgot_password()` | Public | `User` | Implemented (Runtime Blocked) | Generates `secrets.token_urlsafe(48)` token; expires in 1 hour; dispatches reset email. |
| `GET, POST /auth/reset-password/<token>` | `reset_password(token)` | Public | `User` | Implemented (Runtime Blocked) | Validates token expiry; enforces 8+ char password complexity with regex. |
| `GET /auth/logout` | `logout()` | Public | `User` | Implemented (Runtime Blocked) | Sets `is_online=False`, clears session, redirects to login. |
| `POST /auth/logout-session` | `logout_session()` | Public | `User` | Implemented (Runtime Blocked) | AJAX JSON endpoint for session cleanup. |
| `GET /auth/profile` | `profile()` | `login_required` | `User` | Implemented (Runtime Blocked) | Dispatches to respective doctor or patient profile view. |

---

### 2.2 Patient Operations Module (`patients_bp`) — `/patients`
*Source: `app/routes/patients.py` | Templates: `app/templates/patients/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /patients/dashboard` | `dashboard()` | `patient_required` | `Patient`, `Appointment` | Implemented (Runtime Blocked) | Displays upcoming visits, unreviewed appointments, medical history snippets. |
| `GET /patients/profile` | `profile()` | `patient_required` | `Patient`, `User` | Implemented (Runtime Blocked) | Patient profile card with emergency contact and blood group. |
| `GET /patients/complete-profile` | `complete_profile()` | `patient_required` | `Patient` | Implemented (Runtime Blocked) | Onboarding wizard for missing mandatory profile fields. |
| `GET, POST /patients/profile/edit` | `edit_profile()` | `patient_required` | `Patient`, `User` | Implemented (Runtime Blocked) | Profile updater; updates address, emergency phone, CNIC images. |
| `GET /patients/find-doctors` | `find_doctors()` | Public / Patient | `Doctor`, `Review` | Implemented (Runtime Blocked) | Multi-criteria doctor filter (city, specialty, price range, rating). |
| `GET /patients/doctors/category/<category>` | `doctors_by_category()`| Public | `Doctor` | Implemented (Runtime Blocked) | Filtered doctor cards by medical specialty. |
| `GET /patients/doctor/<int:doctor_id>` | `doctor_profile()` | Public | `Doctor`, `Review`, `Appointment` | Implemented (Runtime Blocked) | Doctor profile display, hospital timetables, verified reviews. |
| `GET, POST /patients/doctor/<int:doctor_id>/book` | `book_appointment()` | `patient_required` | `Appointment`, `Doctor` | **Duplicate / Risk** | Full booking workflow; **duplicated** in `appointments.py:book_appointment`. |
| `GET /patients/appointments` | `appointments()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Patient appointment history filtered by status. |
| `POST /patients/appointments/<int:appointment_id>/cancel` | `cancel_appointment()` | `patient_required` | `Appointment` | **Broken / Bug** | Uses `datetime.now()` (system local) instead of PKT (`app/utils/timezone.py`), corrupting the 3-hour deadline calculation on non-PKT servers. |
| `GET, POST /patients/appointments/<int:appointment_id>/upload-payment` | `upload_payment()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Uploads Easypaisa/JazzCash/Bank receipt; sets status to `submitted`. |
| `POST /patients/appointments/<int:appointment_id>/reset-payment` | `reset_payment()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Resets payment state to `pending` if previous payment was rejected. |
| `GET /patients/medical-history` | `medical_history()` | `patient_required` | `MedicalHistory`, `MedicalDocument` | Implemented (Runtime Blocked) | Unified timeline of completed visit diagnoses and uploaded documents. |
| `GET, POST /patients/medical-history/import` | `import_medical_history()` | `patient_required` | `MedicalHistory` | Implemented (Runtime Blocked) | Form to record past non-platform medical history. |
| `GET /patients/documents` | `list_documents()` | `patient_required` | `MedicalDocument` | Implemented (Runtime Blocked) | Document management dashboard (lab reports, X-rays, MRIs). |
| `POST /patients/documents/upload` | `upload_document()` | `patient_required` | `MedicalDocument` | **Security Risk** | Uploads private lab reports to public `app/static/uploads/` path. |
| `POST /patients/documents/<int:doc_id>/delete` | `delete_document()` | `patient_required` | `MedicalDocument` | Implemented (Runtime Blocked) | Ownership-verified document deletion. |
| `POST /patients/documents/<int:doc_id>/toggle-visibility` | `toggle_document_visibility()` | `patient_required` | `MedicalDocument` | Implemented (Runtime Blocked) | Allows patient to hide sensitive lab results from doctor view. |
| `GET /patients/refunds` | `refunds()` | `patient_required` | `Refund` | Implemented (Runtime Blocked) | Displays pending and processed refund claims. |
| `POST /patients/refunds/<int:refund_id>/submit-details` | `submit_refund_details()` | `patient_required` | `Refund`, `RefundPayoutDetail` | Implemented (Runtime Blocked) | Patient submits bank account / mobile wallet details for manual refund transfer. |
| `GET /patients/qa` | `qa()` | `patient_required` | `Question` | Implemented (Runtime Blocked) | Patient's posted questions and answers. |
| `GET, POST /patients/qa/ask` | `ask_question()` | `patient_required` | `Question` | Implemented (Runtime Blocked) | Question publishing form with category tagging and anonymity toggle. |

---

### 2.3 Doctor Operations Module (`doctors_bp`) — `/doctors`
*Source: `app/routes/doctors.py` | Templates: `app/templates/doctors/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /doctors/dashboard` | `dashboard()` | `doctor_required` | `Doctor`, `Appointment`, `Question` | Implemented (Runtime Blocked) | Summary dashboard (todays visits, pending approvals, earnings). |
| `GET /doctors/patients/<int:patient_id>/medical-history` | `patient_medical_history()` | `doctor_required` | `MedicalHistory`, `MedicalDocument` | Implemented (Runtime Blocked) | Doctor reviews patient clinical history; guarded by relationship check. |
| `GET /doctors/profile` | `profile()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Doctor public preview and credential summary. |
| `GET /doctors/earnings` | `earnings()` | `doctor_required` | `Doctor`, `DoctorTransaction`, `DoctorPayoutRequest` | Implemented (Runtime Blocked) | Lifetime earnings ledger, withdrawal history, commission deductions. |
| `POST /doctors/earnings/payout-request` | `request_payout()` | `doctor_required` | `Doctor`, `DoctorPayoutRequest` | Implemented (Runtime Blocked) | Request withdrawal (Min PKR 1,000; bank, wallet, or card). |
| `GET, POST /doctors/profile/edit` | `edit_profile()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Edits bio, experience, consultation fee, services offered. |
| `GET, POST /doctors/appointment-settings`| `appointment_settings()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Hospital timetable and 30-min slot schedule manager. |
| `POST /doctors/save-practice` | `save_practice()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Saves specific day-hospital-fee schedule. |
| `POST /doctors/delete-practice` | `delete_practice()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Removes practice schedule for a given day. |
| `GET /doctors/appointments` | `appointments()` | `doctor_required` | `Appointment` | Implemented (Runtime Blocked) | Doctor appointment queue with status indicators. |
| `GET /doctors/appointments/<int:appointment_id>/queue` | `doctor_queue()` | `doctor_required` | `Appointment` | Implemented (Runtime Blocked) | Live virtual waiting room dashboard with real-time patient queue. |
| `POST /doctors/appointments/<int:appointment_id>/approve` | `approve_appointment()` | `doctor_required` | `Appointment` | **Duplicate / Redundant** | Gated by `payment_status == 'approved'`. Duplicated in `appointments.py`. |
| `POST /doctors/appointments/<int:appointment_id>/reject` | `reject_appointment()` | `doctor_required` | `Appointment` | **Duplicate / Redundant** | Duplicated in `appointments.py`. |
| `POST /doctors/appointments/<int:appointment_id>/complete` | `complete_appointment()` | `doctor_required` | `Appointment` | **Duplicate / Redundant** | Duplicated in `appointments.py`. |
| `POST /doctors/cancellation/<int:appointment_id>/approve` | `approve_cancellation()` | `doctor_required` | `Appointment`, `Refund` | Implemented (Runtime Blocked) | Doctor approves patient cancellation request; triggers refund. |
| `POST /doctors/cancellation/<int:appointment_id>/reject` | `reject_cancellation()` | `doctor_required` | `Appointment` | Implemented (Runtime Blocked) | Doctor rejects patient cancellation request. |
| `GET /doctors/blogs` | `blogs()` | `doctor_required` | `Blog` | Implemented (Runtime Blocked) | Doctor's articles list (drafts, published, pending review). |
| `GET, POST /doctors/blogs/new` | `new_blog()` | `doctor_required` | `Blog` | **Security Defect** | Accepts raw HTML from TinyMCE without sanitization. Stored in DB unsanitized. |
| `GET, POST /doctors/blogs/<int:blog_id>/edit` | `edit_blog()` | `doctor_required` | `Blog` | **Security Defect** | Author-validated blog editing without HTML sanitization. |
| `POST /doctors/blogs/<int:blog_id>/submit_for_review` | `submit_for_review_blog()`| `doctor_required` | `Blog` | Implemented (Runtime Blocked) | Submits draft blog post to admin queue. |
| `POST /doctors/blogs/<int:blog_id>/delete` | `delete_blog()` | `doctor_required` | `Blog` | Implemented (Runtime Blocked) | Soft deletes doctor's article. |
| `POST /doctors/blogs/upload-image` | `upload_blog_image()` | `doctor_required` | — | Implemented (Runtime Blocked) | In-editor image uploader for TinyMCE. |
| `GET /doctors/qa` | `qa()` | `doctor_required` | `Question` | Implemented (Runtime Blocked) | Doctor community Q&A feed by specialty. |
| `GET, POST /doctors/qa/answer/<int:question_id>` | `answer_question()` | `doctor_required` | `Answer`, `Question` | Implemented (Runtime Blocked) | Posts clinical answer to patient question. Enforces single-response rule. |
| `POST /doctors/submit-appeal` | `submit_appeal()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Submits appeal against admin registration rejection (max 3 appeals). |
| `GET /doctors/edit-registration` | `edit_registration()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Review form for rejected registration fields. |
| `POST /doctors/update-registration` | `update_registration()` | `doctor_required` | `Doctor` | Implemented (Runtime Blocked) | Updates credentials after rejection for re-review. |

---

### 2.4 Administration & Moderation Module (`admin_bp`) — `/admin`
*Source: `app/routes/admin.py` | Templates: `app/templates/admin/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /admin/dashboard` | `dashboard()` | `admin_required` (dashboard:view) | `User`, `Doctor`, `Patient`, `Appointment` | Implemented (Runtime Blocked) | High-level KPI metrics (active doctors, bookings, revenue, pending tasks). |
| `GET /admin/suspended` | `suspended_doctors()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | Listing of suspended doctor accounts. |
| `GET /admin/doctors` | `doctors()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | Doctor onboarding approval queue. |
| `GET /admin/doctors/<int:doctor_id>/view` | `view_doctor_details()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | Displays PMC verification code, degree documents, CNIC scans. |
| `GET /admin/doctors/<int:doctor_id>/details-json` | `get_doctor_details_json()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | AJAX JSON payload for modal preview. |
| `POST /admin/doctors/<int:doctor_id>/approve` | `approve_doctor()` | `admin_required` (doctors:approve) | `Doctor` | Implemented (Runtime Blocked) | Sets `is_approved=True`, `is_verified=True`; sends welcome email. |
| `POST /admin/doctors/<int:doctor_id>/reject` | `reject_doctor()` | `admin_required` (doctors:approve) | `Doctor` | Implemented (Runtime Blocked) | Sets `is_approved=False`, records rejection reason, increments appeal counter. |
| `POST /admin/doctors/<int:doctor_id>/appeal` | `process_appeal()` | `admin_required` (doctors:approve) | `Doctor` | Implemented (Runtime Blocked) | Accepts or rejects doctor appeal. |
| `GET /admin/appeals` | `appeals()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | Doctor appeal management panel. |
| `GET /admin/rejected` | `rejected_doctors()` | `admin_required` (doctors:view) | `Doctor` | Implemented (Runtime Blocked) | Listing of rejected registrations. |
| `GET /admin/diseases` | `diseases()` | `admin_required` (diseases:view) | `Disease` | Implemented (Runtime Blocked) | Disease knowledgebase index. |
| `GET, POST /admin/diseases/add` | `add_disease()` | `admin_required` (diseases:create) | `Disease` | Implemented (Runtime Blocked) | Creates new disease article with symptoms and severity. |
| `GET, POST /admin/diseases/<int:disease_id>/edit` | `edit_disease()` | `admin_required` (diseases:edit) | `Disease` | Implemented (Runtime Blocked) | Updates disease article. |
| `POST /admin/diseases/<int:disease_id>/delete` | `delete_disease()` | `admin_required` (diseases:delete) | `Disease` | Implemented (Runtime Blocked) | Deactivates or removes disease article. |
| `GET /admin/blogs` | `blogs()` | `admin_required` (blogs:view) | `Blog` | Implemented (Runtime Blocked) | Doctor blog review queue. |
| `POST /admin/blogs/<int:blog_id>/delete` | `delete_blog()` | `admin_required` (blogs:delete) | `Blog` | Implemented (Runtime Blocked) | Soft deletes blog post. |
| `POST /admin/blogs/<int:blog_id>/approve` | `approve_blog()` | `admin_required` (blogs:approve) | `Blog` | Implemented (Runtime Blocked) | Sets `status='published'`, publishes immediately. |
| `POST /admin/blogs/<int:blog_id>/reject` | `reject_blog()` | `admin_required` (blogs:approve) | `Blog` | Implemented (Runtime Blocked) | Sets `status='rejected'` with feedback note. |
| `GET /admin/qa` | `qa()` | `admin_required` (qa:view) | `Question` | Implemented (Runtime Blocked) | Q&A moderation queue. |
| `POST /admin/qa/question/<int:question_id>/delete` | `delete_question()` | `admin_required` (qa:delete) | `Question` | Implemented (Runtime Blocked) | Moderation soft deletion of inappropriate questions. |
| `POST /admin/qa/answer/<int:answer_id>/delete` | `delete_answer()` | `admin_required` (qa:delete) | `Answer` | Implemented (Runtime Blocked) | Moderation soft deletion of inappropriate answers. |
| `GET /admin/patients` | `patients()` | `admin_required` (patients:view) | `Patient` | Implemented (Runtime Blocked) | Patient registry index. |
| `GET /admin/patients/<int:patient_id>/view` | `view_patient()` | `admin_required` (patients:view) | `Patient` | Implemented (Runtime Blocked) | Patient profile inspector. |
| `GET /admin/patients/<int:patient_id>/appointments` | `view_patient_appointments()` | `admin_required` (patients:view) | `Appointment` | Implemented (Runtime Blocked) | History of appointments for a specific patient. |
| `GET /admin/appointments/<int:appointment_id>/recordings` | `appointment_recordings()` | `admin_required` (appointments:view) | `VideoCallRecording` | Implemented (Runtime Blocked) | Video recording inspector for a specific visit. |
| `GET /admin/recordings/<int:recording_id>/watch` | `recording_watch()` | `admin_required` (appointments:view) | `VideoCallRecording` | Implemented (Runtime Blocked) | Dedicated HTML5 player for recorded consultations. |
| `GET /admin/recordings/<int:recording_id>/download` | `recording_download()` | `admin_required` (appointments:view) | `VideoCallRecording` | Implemented (Runtime Blocked) | Compiles and streams a ZIP bundle of HLS `.ts` chunks or MP4. |
| `GET /admin/recordings/<int:recording_id>/hls/<path:filename>` | `recording_hls_asset()` | Playback Token (`?pt=`) | `VideoCallRecording` | Implemented (Runtime Blocked) | Rewrites `.m3u8` playlist paths into presigned URLs. |
| `GET /admin/recordings/<int:recording_id>/seg/<path:filename>` | `recording_hls_segment()`| Playback Token (`?pt=`) | `VideoCallRecording` | **Performance Bottleneck** | Fetches `.ts` video chunk from Spaces and streams via Flask WSGI thread into browser RAM. |
| `GET /admin/appointments` | `appointments()` | `admin_required` (appointments:view) | `Appointment` | Implemented (Runtime Blocked) | Master appointments management ledger. |
| `GET /admin/payments` | `payments()` | `admin_required` (payments:view) | `Appointment` | Implemented (Runtime Blocked) | Manual payment verification queue (EasyPaisa/JazzCash). |
| `POST /admin/payments/<int:appointment_id>/approve` | `approve_payment()` | `admin_required` (payments:approve) | `Appointment` | Implemented (Runtime Blocked) | Sets `payment_status='approved'`; checks slot reservation conflict; notifies doctor. |
| `POST /admin/payments/<int:appointment_id>/reject` | `reject_payment()` | `admin_required` (payments:approve) | `Appointment` | Implemented (Runtime Blocked) | Rejects fake or invalid payment proof screenshot. |
| `POST /admin/payments/<int:appointment_id>/dispute-approve` | `approve_disputed_payment()` | `admin_required` (payments:approve) | `Appointment`, `Refund` | Implemented (Runtime Blocked) | Approves refund for appointments that timed out before admin could review. |
| `POST /admin/payments/<int:appointment_id>/dispute-reject` | `reject_disputed_payment()` | `admin_required` (payments:approve) | `Appointment` | Implemented (Runtime Blocked) | Rejects disputed timeout refund. |
| `GET /admin/accounts` | `accounts()` | `admin_required` (accounts:view) | `PlatformRevenue`, `Refund`, `DoctorTransaction` | Implemented (Runtime Blocked) | Financial dashboard (gross revenue, commission, pending liabilities). |
| `GET /admin/accounts/payment-flow` | `accounts_payment_flow()` | `admin_required` (accounts:view) | `Appointment` | Implemented (Runtime Blocked) | Visual diagram / explanation of payment states. |
| `GET /admin/accounts/refunds` | `accounts_refunds()` | `admin_required` (accounts:view) | `Refund`, `RefundPayoutDetail` | Implemented (Runtime Blocked) | Refund processing ledger with patient bank details. |
| `POST /admin/accounts/refunds/<int:refund_id>/mark-processed` | `refund_mark_processed()` | `admin_required` (accounts:approve) | `Refund` | Implemented (Runtime Blocked) | Marks refund transferred; uploads admin transfer receipt. |
| `GET /admin/accounts/payouts` | `accounts_payouts()` | `admin_required` (accounts:view) | `DoctorPayoutRequest` | Implemented (Runtime Blocked) | Doctor withdrawal requests queue. |
| `POST /admin/accounts/payouts/<int:request_id>/approve` | `payout_approve()` | `admin_required` (accounts:approve) | `DoctorPayoutRequest`, `Doctor` | Implemented (Runtime Blocked) | Approves doctor payout; deducts doctor balance. |
| `POST /admin/accounts/payouts/<int:request_id>/reject` | `payout_reject()` | `admin_required` (accounts:approve) | `DoctorPayoutRequest` | Implemented (Runtime Blocked) | Rejects doctor payout request. |
| `GET /admin/accounts/doctors/<int:doctor_id>/financials` | `doctor_financials()` | `admin_required` (accounts:view) | `Doctor`, `DoctorTransaction` | Implemented (Runtime Blocked) | Detailed audit ledger of a doctor's earnings and deductions. |
| `GET /admin/patients/<int:patient_id>/medical-history` | `view_patient_medical_history()` | `admin_required` (patients:view) | `MedicalHistory` | Implemented (Runtime Blocked) | Administrative review of patient clinical history. |
| `GET /admin/reviews` | `reviews()` | `admin_required` (reviews:view) | `Review` | Implemented (Runtime Blocked) | Patient review moderation panel with IP fraud indicators. |
| `POST /admin/reviews/<int:review_id>/approve` | `approve_review()` | `admin_required` (reviews:approve) | `Review` | Implemented (Runtime Blocked) | Clears flagged review for public display. |
| `POST /admin/reviews/<int:review_id>/reject` | `reject_review()` | `admin_required` (reviews:approve) | `Review` | Implemented (Runtime Blocked) | Rejects fraudulent review. |
| `POST /admin/reviews/<int:review_id>/toggle-visibility` | `toggle_review_visibility()`| `admin_required` (reviews:edit) | `Review` | Implemented (Runtime Blocked) | Hides or shows review on public doctor profile. |

---

### 2.5 Appointments Module (`appointments_bp`) — `/appointments`
*Source: `app/routes/appointments.py` | Templates: `app/templates/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /appointments/` | `index()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Redirects user to their role-specific appointment dashboard. |
| `GET, POST /appointments/book` | `book_appointment()` | `patient_required` | `Appointment`, `Doctor` | **Duplicate Code** | Duplicate of `patients.book_appointment`. |
| `POST /appointments/<int:appointment_id>/approve` | `approve_appointment()` | `doctor_required` | `Appointment` | **Duplicate Code** | Duplicate of `doctors.approve_appointment`. |
| `POST /appointments/<int:appointment_id>/reject` | `reject_appointment()` | `doctor_required` | `Appointment` | **Duplicate Code** | Duplicate of `doctors.reject_appointment`. |
| `POST /appointments/<int:appointment_id>/complete/patient`| `patient_complete_appointment()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Patient confirms completion; unlocks review window. |
| `POST /appointments/<int:appointment_id>/complete` | `complete_appointment()` | `doctor_required` | `Appointment` | **Duplicate Code** | Duplicate of `doctors.complete_appointment`. |
| `POST /appointments/<int:appointment_id>/confirm_completion`| `confirm_completion()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Patient confirms doctor's completion. |
| `POST /appointments/<int:appointment_id>/skip_post_visit_review` | `skip_post_visit_review()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Sets `patient_review_skipped=True` to immediately unlock dispute window. |
| `POST /appointments/<int:appointment_id>/dispute_completion` | `dispute_completion()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Patient raises dispute on incomplete consultation; pauses payout. |
| `POST /appointments/<int:appointment_id>/cancel` | `cancel_appointment()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Cancels appointment; triggers refund calculation. |
| `GET /appointments/<int:appointment_id>` | `view_appointment()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Detailed appointment overview with action buttons. |
| `POST /appointments/<int:appointment_id>/verify-payment` | `verify_payment()` | `admin_required` | `Appointment` | Implemented (Runtime Blocked) | Secondary payment approval handler. |
| `GET /appointments/<int:appointment_id>/chat` | `appointment_chat()` | `login_required` | `Appointment`, `MedicalHistory` | Implemented (Runtime Blocked) | Chat consultation UI; checks payment approval gate. |
| `POST /appointments/api/send-message` | `api_send_message()` | `login_required` | `Appointment`, `MedicalHistory` | **Performance Bottleneck** | Appends message to `medical_histories.chat_logs` JSON column; emits via SocketIO. |
| `GET /appointments/api/messages/<int:appointment_id>` | `get_messages()` | `login_required` | `MedicalHistory` | Implemented (Runtime Blocked) | Fetches historical chat log JSON array. |
| `GET /appointments/api/available-dates/<int:doctor_id>` | `get_available_dates()` | Public | `Doctor`, `Appointment` | Implemented (Runtime Blocked) | Returns dates where doctor has configured active practice. |
| `GET /appointments/api/available-slots/<int:doctor_id>` | `get_available_slots()` | Public | `Doctor`, `Appointment` | Implemented (Runtime Blocked) | Returns free 30-min slots after filtering out paid appointments. |
| `GET /appointments/api/validate-slot/<int:doctor_id>` | `validate_slot()` | Public | `Doctor`, `Appointment` | Implemented (Runtime Blocked) | Pre-booking slot validation check. |

---

### 2.6 Telehealth Video Module (`video_bp`) — `/video`
*Source: `app/routes/video.py` | Templates: `app/templates/video_call.html`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /video/token/<int:appointment_id>` | `get_video_token()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Generates Agora RTC token (role publisher); enforces waiting room time window (doctor: -30m, patient: -15m). |
| `GET /video/queue-status/<int:appointment_id>` | `get_queue_status()` | `login_required` | `Appointment` | **Hardcoded Override** | Contains hardcoded `timedelta(minutes=2)` testing override for no-show grace period (`video.py:210`). |
| `POST /video/start/<int:appointment_id>` | `start_video_call()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Doctor starts the live call; sets `is_call_active=True`, records `mutual_call_start`. |
| `POST /video/recording-start/<int:appointment_id>` | `recording_start()` | `login_required` | `Appointment`, `VideoCallRecording` | Implemented (Runtime Blocked) | Triggers Agora Cloud Recording acquire/start API once both parties are publishing media. |
| `GET /video/check-unlock/<int:appointment_id>` | `check_unlock()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Polling endpoint (every ~12s); checks if mutual video duration exceeded 3 minutes; unlocks prescription. |
| `POST /video/end/<int:appointment_id>` | `end_video_call()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Resets `is_call_active=False`; stops Agora cloud recording; calculates duration. |
| `POST /video/mark-no-show/<int:appointment_id>` | `mark_no_show()` | `login_required` | `Appointment` | Implemented (Runtime Blocked) | Doctor marks patient absent after grace period expires; triggers patient no-show penalty. |

---

### 2.7 Clinical Prescriptions Module (`prescriptions_bp`) — `/prescriptions`
*Source: `app/routes/prescriptions.py` | Templates: `app/templates/prescriptions/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET, POST /prescriptions/create/<int:appointment_id>` | `create_prescription()` | `doctor_required` | `Prescription`, `PrescriptionMedicine`, `PrescriptionTest` | Implemented (Runtime Blocked) | Form to record vitals, diagnosis, chief complaints, medicines, and tests. |
| `GET /prescriptions/view/<int:prescription_id>` | `view_prescription()` | **NONE (Missing `@login_required`)** | `Prescription`, `Appointment` | **Broken / Crash** | Line 102 calls `user = get_current_user()`. If unauthenticated, `user` is `None`. Line 106 does `if user.role == ...`, throwing `AttributeError: 'NoneType' object has no attribute 'role'` (HTTP 500). |
| `GET /prescriptions/download/<int:prescription_id>` | `download_prescription()` | **NONE (Missing `@login_required`)** | `Prescription` | **Broken / Crash** | Crashes with `AttributeError` if unauthenticated. Also crashes with `ModuleNotFoundError: No module named 'xhtml2pdf'` because `xhtml2pdf` is omitted from `requirements.txt`. |

---

### 2.8 Payment Gateway Module (`payments_bp`) — `/` (root)
*Source: `app/routes/payments.py` | Templates: `app/templates/payments/`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/payment-status/<int:appointment_id>` | `payment_status_api()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Polled by checkout popup; queries Safepay Tracker API. |
| `GET /safepay/checkout/<int:appointment_id>` | `safepay_checkout()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Calls Safepay `/order/v1/init` to generate tracker token; redirects to hosted checkout. |
| `GET /safepay/return/<int:appointment_id>` | `safepay_return()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Interstitial callback page after Safepay hosted modal is closed; verifies Tracker status. |
| `POST /safepay/webhook` | `safepay_webhook()` | **Public (NO SIGNATURE CHECK)** | `Appointment` | **CRITICAL SECURITY FLAW** | Processes webhook events without HMAC signature verification. Any unauthenticated caller can forge a JSON payload and mark an appointment paid. |
| `GET /safepay/cancel/<int:appointment_id>` | `safepay_cancel()` | `patient_required` | `Appointment` | Implemented (Runtime Blocked) | Handles checkout cancellation by patient. |

---

### 2.9 Public Content & Q&A Modules (`home_bp`, `qa_bp`, `blogs_bp`, `diseases_bp`, `reviews_bp`)
*Sources: `app/routes/home.py`, `qa.py`, `blogs.py`, `diseases.py`, `reviews.py`*

| Route & Methods | Controller Function | Auth & RBAC | Models Touched | Status | Known Defects / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /` | `home.index()` | Public | `Doctor`, `Blog` | Implemented (Runtime Blocked) | Landing page with featured specialties, top doctors, and blog cards. |
| `GET /api/geocode` | `home.geocode_lookup()` | Public | — | Implemented (Runtime Blocked) | Forward geocoding proxy to Geoapify API. |
| `GET /blogs/<int:blog_id>` | `blogs.view_blog()` | Public | `Blog`, `Doctor` | **Security Defect** | Line 117 of `blogs/view.html` renders `{{ render_content \| safe }}`. Unsanitized doctor blogs cause Stored XSS. |
| `POST /qa/ai-chat` | `qa.ai_chat()` | Public | `Question`, `Doctor` | **Security / Abuse** | Rate limiting is cookie-session based (`session['qa_ai_chat_timestamps']`). Dropping cookies bypasses rate limit, draining LLM credits. |
| `GET /diseases/<int:disease_id>` | `diseases.view_disease()` | Public | `Disease`, `Doctor` | **Performance Flaw** | Lines 68-73 load **ALL approved doctors in the database** into Python memory to filter matching specialties in a `for` loop. |
| `POST /reviews/submit` | `reviews.submit_review()` | `patient_required` | `Review`, `Appointment` | **Latency Flaw** | Calls unencrypted `http://ip-api.com` synchronously with 2.5s timeout on every review submission. |

