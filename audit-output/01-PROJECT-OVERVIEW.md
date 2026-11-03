# 01 — PROJECT OVERVIEW & WORKSPACE DISCOVERY

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Repository Type:** Standalone Monolithic Web Application (Flask Full-Stack)  
**Academic / Institutional Context:** Final Year Project (FYP), University of the Punjab  
**Live Site Deployment:** [https://quickcares.me](https://quickcares.me)  
**Audit Date:** November 1, 2026  
**Auditor:** Principal Software Architect & Lead Security Auditor  

---

## 1. Executive Mission & Domain Context

**Quick Care Connect** is a multi-role healthcare and telemedicine web application built specifically for Pakistan's healthcare ecosystem. It provides an end-to-end bridge connecting **patients**, **PMDC/PMC-verified doctors**, and **administrative staff** through a structured consultation lifecycle.

### Core Domain Capabilities:
1. **Multi-Role Role-Based Access Control (RBAC):** Distinct functional portals for `patient`, `doctor`, `admin` (super-admin), and sub-admin staff roles (`accountant`, `doctors_manager`, `patient_support_manager`).
2. **Consultation Lifecycle & Escrow Gate:** Slot reservation is gated by payment verification. Patients book 30-minute physical or video consultation slots. For manual bank/wallet payments (EasyPaisa/JazzCash), patients upload payment screenshot proofs which an admin must review and approve before the doctor is notified or time slots are locked. Alternatively, automated checkout is supported via Safepay.
3. **WebRTC Real-Time Telehealth:** Web-based video consultations powered by the Agora RTC SDK, with virtual waiting rooms, doctor-initiated call activation, punctuality checks, mutual attendance gates, and optional cloud recording stored in DigitalOcean Spaces.
4. **Real-Time Patient-Doctor Messaging:** WebSockets via Flask-SocketIO (`async_mode='threading'`) for consultation chat, file sharing, and live updates.
5. **Clinical Prescriptions & Records:** Digital prescription generator with diagnosis, vitals, multi-medicine schedules, lab tests, and automated PDF compilation; personal health document vault (lab reports, CT scans, MRIs).
6. **Community Q&A with AI Assistant:** Patient medical Q&A forum with doctor responses, peer follow-ups, helpfulness voting, and an integrated role-aware AI chatbot using Google Gemini 1.5 Flash (with OpenRouter fallback).
7. **Medical Publishing & Disease Database:** Doctor-authored health articles moderated by admins via TinyMCE, paired with a public disease and symptoms encyclopedia with doctor recommendation funnels.
8. **Financial Management & Settlement:** Platform commission deduction (default 20%), automated refund calculation on doctor/patient cancellations and no-shows, doctor payout request processing, and financial transaction ledgering.

---

## 2. Workspace & Git Discovery

| Attribute | Discovery Finding | Evidence / Reference |
| :--- | :--- | :--- |
| **Workspace Root** | `c:\Users\Mubeen\Desktop\Quick Care FYP` | Active IDE Workspace Path |
| **Project Root** | `c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP` | Inner project folder housing application files |
| **Version Control** | Git 2.45+ (Windows) | Git repository initialized in `Quick Care FYP/.git` |
| **Current Branch** | `main` | Tracking `origin/main` |
| **Latest Commit** | `203547f` | `"Quick Care Connect & AI Healthcare Assistance - complete FYP project."` |
| **Remote Origin** | `https://github.com/zohaibahmad447/FYP-Project.git` | `git remote -v` |
| **Working Tree Status** | Modified / Uncommitted deletion | `_push_clean.py` deleted in working tree (preserved per safety rules) |
| **Untracked / Ignored Artifacts** | Development SQLite DBs, local TLS certificates, executables | `instance/quickcare_dev.db` (384 KB), `localhost+3.pem`, `mkcert.exe.exe` (tracked binary: 4.8MB) |

---

## 3. Project File Tree & Directory Topology

```
Quick Care FYP/
├── app/
│   ├── forms/                       # WTForms class definitions
│   │   └── __init__.py              # LoginForm, UnifiedRegistrationForm, BlogForm, etc.
│   ├── jobs/                        # Scheduled cron background tasks
│   │   ├── __init__.py
│   │   └── check_expired_appointments.py # No-show detection & timeout dispute handler
│   ├── routes/                      # 14 Flask Blueprint route modules (168 endpoints)
│   │   ├── admin.py                 # Admin dashboard, moderation, approvals, recordings (1,544 lines)
│   │   ├── admin_staff.py           # Granular sub-admin staff CRUD & permission management
│   │   ├── appointments.py          # Slot booking, appointment actions, chat API (1,454 lines)
│   │   ├── auth.py                  # Login, registration, password reset, session control
│   │   ├── blogs.py                 # Public blog feed, article view, contributor ranking
│   │   ├── diseases.py              # Disease knowledgebase and specialty doctor recommendation
│   │   ├── doctors.py               # Doctor dashboard, schedule settings, earnings, appeals (1,683 lines)
│   │   ├── home.py                  # Public landing, about, contact, FAQ, doctor directory, geocoding
│   │   ├── patients.py              # Patient dashboard, booking, document uploads, refunds (1,471 lines)
│   │   ├── payments.py              # Safepay checkout, return interstitial, webhook, status poll
│   │   ├── prescriptions.py         # Prescription builder, viewer, PDF export trigger
│   │   ├── qa.py                    # Community Q&A forum, voting, bookmarking, AI chat endpoint
│   │   ├── reviews.py               # Post-consultation patient star rating & fraud screening
│   │   └── video.py                 # Agora token generation, queue status, call gates
│   ├── services/                    # Shared infrastructure and external API services
│   │   ├── accounts_service.py      # Earning credits, platform revenue logging, refunds
│   │   ├── ai_chatbot_service.py    # Gemini 1.5 Flash + OpenRouter prompt engineer (1,064 lines)
│   │   ├── email_service.py         # Flask-Mail wrapper with embedded HTML templates (776 lines)
│   │   ├── recording_service.py     # Agora Cloud Recording REST API client (start/stop)
│   │   └── socketio_events.py       # Flask-SocketIO event handlers (chat, video signaling)
│   ├── static/                      # Static assets served to web clients
│   │   ├── css/                     # Custom stylesheet modules (main.css, video-call.css, etc.)
│   │   ├── js/                      # Frontend JavaScript (video-call.js, main.js, doctor-queue.js)
│   │   ├── images/                  # UI assets, medical illustrations, logos, team photos
│   │   ├── landing_page/            # Marketing video clips (MP4 format)
│   │   ├── prescriptions/           # Generated PDF prescription files
│   │   └── uploads/                 # User-uploaded files (CNICs, degrees, medical docs, payment proofs)
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── admin/                   # 16 Admin portal templates
│   │   ├── auth/                    # Login, unified registration, password recovery templates
│   │   ├── blogs/                   # Blog index and reader templates
│   │   ├── components/              # Reusable template components (modals, dropdowns)
│   │   ├── diseases/                # Disease encyclopedia templates
│   │   ├── doctors/                 # 12 Doctor portal templates
│   │   ├── errors/                  # Custom 404 error page
│   │   ├── home/                    # Landing page, about, terms, privacy, FAQ
│   │   ├── partials/                # Global footer, status badges, scroll-to-top
│   │   ├── patients/                # 15 Patient portal templates
│   │   ├── payments/                # Safepay popup interstitial template
│   │   ├── prescriptions/           # Prescription create, view, and PDF HTML layout
│   │   ├── qa/                      # Q&A forum and question thread templates
│   │   └── base.html                # Master base layout template
│   ├── utils/                       # Business logic helper libraries
│   │   ├── accounts_migration.py    # Runtime table column schema patcher
│   │   ├── admin_permissions.py     # Granular panel RBAC and endpoint guard decorators
│   │   ├── admin_rbac_migration.py  # Runtime Admin RBAC table migrations
│   │   ├── appointment_status.py    # Badge styling and label formatters
│   │   ├── appointment_workflow.py  # Booking deadlines and doctor notification triggers
│   │   ├── auth.py                  # User session extraction and role decorators
│   │   ├── blog_covers.py           # Static fallback image assigner for articles
│   │   ├── categories.py            # Medical specialty definitions and hospital mappings
│   │   ├── cleanup_expired_payments.py # Unpaid booking auto-cancellation logic
│   │   ├── file_upload.py           # File validation, extension checking, image resizing
│   │   ├── geocoding.py             # Geoapify forward geocoder proxy
│   │   ├── pdf_generator.py         # xhtml2pdf prescription renderer
│   │   ├── practice_organizer.py    # Doctor weekly hospital timetable parser
│   │   ├── prescription_gate.py     # 3-minute video consultation verification gate
│   │   ├── process_completion_reviews.py # 24-hour review auto-closure job
│   │   ├── qa_migration.py          # Runtime Q&A schema patcher
│   │   ├── recording_playback.py    # URLSafeTimedSerializer signed token generator
│   │   ├── review_flow_migration.py # Runtime review workflow schema patcher
│   │   ├── review_fraud.py          # IP hashing, geo-lookup, and review fraud heuristics
│   │   ├── review_fraud_migration.py# Runtime review fraud schema patcher
│   │   ├── slots.py                 # 30-minute interval slot reservation engine
│   │   ├── spaces_storage.py        # DigitalOcean Spaces boto3 presigned URL manager
│   │   └── timezone.py              # Pakistan Standard Time (Asia/Karachi) helpers
│   ├── database.py                  # SQLAlchemy db instance anchor
│   ├── models.py                    # 27 SQLAlchemy database models (860 lines)
│   ├── scheduler.py                 # APScheduler BackgroundScheduler setup
│   └── __init__.py                  # Flask Application Factory (`create_app`)
├── deploy/                          # Production Linux configuration templates
│   ├── gunicorn.conf.py             # Gunicorn WSGI configuration (1 worker, 16 threads)
│   ├── nginx-quickcare.conf         # Nginx reverse proxy configuration for domain
│   ├── nginx-quickcare-ip.conf      # Nginx configuration for direct IP access
│   ├── quickcare.service            # Systemd service unit file
│   └── README.txt                   # Deployment quick notes
├── instance/                        # SQLite runtime storage
│   ├── quickcare_dev.db             # Development database (384 KB, 29 tables)
│   ├── quickcare.db                 # Unused database file (0 bytes)
│   └── quick_care.db                # Unused database file (0 bytes)
├── migrations/                      # Ad-hoc database migration scripts
│   ├── add_accounts_models.py
│   ├── add_answer_replies.py
│   ├── add_answer_replies_indexes.py
│   ├── add_answer_reply_photo.py
│   ├── add_doctor_balance_and_session_tracking.py
│   ├── add_doctor_payout_method_fields.py
│   ├── add_payment_deadline.py
│   ├── add_prescription_models.py
│   ├── add_qa_mvp_features.py
│   ├── add_services_field.py
│   └── add_video_call_state.py
├── .env                             # Active local environment variables
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore definitions
├── config.py                        # Centralized configuration classes
├── CONTRIBUTORS.md                  # Project team attribution
├── localhost+3.pem                  # Development TLS certificate
├── localhost+3-key.pem              # Development TLS private key
├── mkcert.exe.exe                   # Binary certificate generation tool (tracked in git)
├── README.md                        # Application documentation
├── requirements.txt                 # Python package manifest
├── run.py                           # Local development HTTPS entry point
└── wsgi.py                          # Production WSGI entry point
```

---

## 4. Key Architectural Patterns & Decisions

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Web Browsers)"]
        Browser["Desktop & Mobile Browsers"]
        SocketClient["Socket.IO Client JS"]
        AgoraSDK["Agora RTC Web SDK"]
    end

    subgraph IngressLayer ["Ingress & Web Server"]
        Nginx["Nginx Reverse Proxy (:80 / :443)"]
        StaticServe["Static Files Bypass (/static/)"]
    end

    subgraph AppLayer ["Application Runtime (Gunicorn / Flask)"]
        WSGI["Gunicorn WSGI (1 Worker, 16 Threads)"]
        AppFactory["Flask create_app()"]
        Blueprints["14 Blueprints (168 Endpoints)"]
        Scheduler["APScheduler (Daemon Thread)"]
        SocketServer["Flask-SocketIO (Threading Mode)"]
    end

    subgraph PersistenceLayer ["Persistence & External Services"]
        SQLiteDB[("SQLite Database (quickcare_dev.db)")]
        LocalUploads["Local Filesystem (app/static/uploads)"]
        SafepayAPI["Safepay Payment Gateway"]
        AgoraCloud["Agora RTC & Cloud Recording"]
        DOSpaces["DigitalOcean Spaces (S3 Compatible)"]
        GeminiAPI["Google Gemini 1.5 Flash / OpenRouter"]
        MailServer["Namecheap Private Email (SMTP)"]
    end

    Browser -->|HTTP Requests| Nginx
    Browser -->|WebSocket Upgrade| Nginx
    Nginx -->|/static/ direct serve| StaticServe
    StaticServe --> LocalUploads
    Nginx -->|Proxy Pass :8000| WSGI
    WSGI --> AppFactory
    AppFactory --> Blueprints
    AppFactory --> SocketServer
    AppFactory --> Scheduler
    Blueprints --> SQLiteDB
    Blueprints --> LocalUploads
    Blueprints --> SafepayAPI
    Blueprints --> AgoraCloud
    Blueprints --> GeminiAPI
    Blueprints --> MailServer
    SocketServer --> SQLiteDB
    SocketClient <-->|WebSockets| SocketServer
    AgoraSDK <-->|Audio/Video Media| AgoraCloud
    AgoraCloud -.->|HLS / MP4 Upload| DOSpaces
    Scheduler -->|Cron Jobs (5m/10m/1h)| SQLiteDB
```

---

## 5. Summary of Modules & Lines of Code

| Module | Location | Estimated Lines | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Doctors** | `app/routes/doctors.py` | 1,683 | Doctor dashboard, schedule management, earnings, appeals, registration updates |
| **Admin** | `app/routes/admin.py` | 1,544 | Doctor onboarding approvals, payment reviews, refunds, payouts, recordings |
| **Patients** | `app/routes/patients.py` | 1,471 | Doctor search, booking, payment upload, document vault, refund claim submission |
| **Appointments** | `app/routes/appointments.py` | 1,454 | Slot generation API, appointment state transitions, chat HTTP fallback |
| **AI Chatbot** | `app/services/ai_chatbot_service.py` | 1,064 | Gemini 1.5 Flash prompting, medical guardrails, doctor recommendation matching |
| **Models** | `app/models.py` | 860 | 27 SQLAlchemy data models, properties, relationships |
| **Email Service** | `app/services/email_service.py` | 776 | 15 transactional email templates and async thread dispatch |
| **Auth** | `app/routes/auth.py` | 566 | Unified login/register, password reset token flow, session management |
| **Video** | `app/routes/video.py` | 474 | Agora token builder, queue statuses, mutual attendance gates, no-show detection |
| **SocketIO** | `app/services/socketio_events.py` | 450 | Chat room joining, message broadcast, call start/end signaling |
| **QA** | `app/routes/qa.py` | 480 | Q&A forum indexing, question voting, bookmarking, AI chat endpoint |
| **Admin RBAC** | `app/utils/admin_permissions.py` | 404 | Granular panel grants, role presets, before_request permission enforcement |
| **Payments** | `app/routes/payments.py` | 427 | Safepay checkout redirect, return interstitial, webhook processing |
| **Config** | `config.py` | 140 | Environment configuration, session parameters, third-party credentials |
| **Total Python App Code** | `app/` + root | **~12,500 lines** | Excludes static assets, templates, migrations, and vendor binaries |

---

## 6. Document Integrity & Validation Statement

All details recorded in this overview have been extracted through direct read-only inspection of the repository files, directory listings, Git status, and SQLite database metadata. No assumptions regarding tech stack or architecture were made prior to physical inspection.

