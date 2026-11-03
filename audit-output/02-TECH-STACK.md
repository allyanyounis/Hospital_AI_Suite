# 02 — TECHNOLOGY STACK & DEPENDENCY AUDIT

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Audit Date:** November 1, 2026  
**Auditor:** Principal Software Architect & DevOps Engineer  

---

## 1. Declared vs. Verified Dependencies

The following table compares the dependencies declared in `Quick Care FYP/requirements.txt` against physical repository imports and runtime compatibility.

| Package Name | Declared Version | Import Name | Actual Usage & Role | Compatibility / Integrity Finding |
| :--- | :--- | :--- | :--- | :--- |
| `Flask` | `==2.3.3` | `flask` | Core web application framework; blueprints, context, templating. | **DECLARED**. Released Aug 2023. Fully functional on Python 3.11/3.12. |
| `Flask-SQLAlchemy` | `==3.0.5` | `flask_sqlalchemy` | ORM integration for model definitions and database session handling. | **DECLARED**. Wraps SQLAlchemy 2.0. |
| `Flask-Migrate` | `==4.0.5` | `flask_migrate` | Alembic wrapper for schema migrations. | **ANOMALY**. Initialized in `app/__init__.py`, but no standard `migrations/versions/` exists. |
| `Flask-SocketIO` | `==5.3.6` | `flask_socketio` | WebSocket server for real-time consultation chat & call signaling. | **DECLARED**. Initialized with `async_mode='threading'` for Python 3.12 compatibility. |
| `Flask-WTF` | `==1.2.2` | `flask_wtf` | Form handling and CSRF validation. | **CRITICAL ANOMALY**. CSRF protection is globally disabled via `WTF_CSRF_ENABLED = False`. |
| `Flask-Mail` | `==0.9.1` | `flask_mail` | Transactional email delivery via SMTP. | **DECLARED**. Unmaintained upstream package (last release 2014); functional but legacy. |
| `WTForms` | `==3.0.1` | `wtforms` | Form field definitions, validators. | **DECLARED**. Used in `app/forms/__init__.py`. |
| `Werkzeug` | `==2.3.7` | `werkzeug` | WSGI utility library, password hashing (`generate_password_hash`, `check_password_hash`), `secure_filename`. | **DECLARED**. Standard Flask foundation. |
| `python-socketio` | `==5.8.0` | `socketio` | Engine.IO / Socket.IO protocol implementation. | **DECLARED**. Lower-level dependency of Flask-SocketIO. |
| `python-engineio` | `==4.7.1` | `engineio` | Transport layer for WebSockets and long-polling. | **DECLARED**. Lower-level dependency of python-socketio. |
| `eventlet` | `==0.33.3` | `eventlet` | Async networking library. | **UNUSED / INCOMPATIBLE**. Not imported in code. Application explicitly configures `async_mode='threading'` because eventlet crashes on Python 3.12 and broke HLS video playback. Can be safely purged. |
| `gunicorn` | `==21.2.0` | `gunicorn` | WSGI HTTP Server for production Linux deployment. | **DECLARED**. Configured in `deploy/gunicorn.conf.py` with `workers=1`, `worker_class='gthread'`. Incompatible with native Windows (used on Linux server only). |
| `python-dotenv` | `==1.0.0` | `dotenv` | Environment variable loader (`load_dotenv()`). | **DECLARED**. Used in `config.py` to parse `.env`. |
| `Pillow` | `==10.0.1` | `PIL` | Image manipulation and validation. | **DECLARED**. Used in `app/utils/file_upload.py` for image verification and Lanczos resizing. |
| `python-magic` | `==0.4.27` | `magic` | MIME type identification via file magic numbers. | **DEFECT (WINDOWS)**. Not imported directly in code (`file_upload.py` uses custom dictionary). If imported on Windows, crashes due to missing `libmagic.dll`. |
| `pytz` | `==2023.3` | `pytz` | Timezone database library. | **DECLARED**. Used in `app/utils/timezone.py` for `Asia/Karachi` conversions. |
| `APScheduler` | `==3.10.4` | `apscheduler` | In-process background cron scheduler. | **DECLARED**. Runs 3 periodic jobs in daemon background thread via `app/scheduler.py`. |
| `requests` | `==2.31.0` | `requests` | Synchronous HTTP client. | **DECLARED**. Used for Safepay API calls, OpenRouter/Gemini requests, and Geoapify geocoding. |
| `email_validator` | `==2.1.1` | `email_validator` | Syntax validation for email fields in WTForms. | **DECLARED**. Used by WTForms Email validator. |
| `agora-token-builder` | `==1.0.0` | `agora_token_builder` | Generates Agora RTC dynamic access tokens. | **DECLARED**. Used in `app/routes/video.py` and `app/services/recording_service.py`. |
| `boto3` | `==1.34.162` | `boto3` | AWS SDK for Python (used for DigitalOcean Spaces). | **DECLARED**. Used in `app/utils/spaces_storage.py` for S3 presigned URLs. |
| **`xhtml2pdf`** | **UNDECLARED** | `xhtml2pdf` | HTML to PDF converter using ReportLab. | **CRITICAL DEFECT**. Required by `app/utils/pdf_generator.py:4` (`from xhtml2pdf import pisa`). Missing from `requirements.txt`. Installing from manifest will cause runtime crash when generating prescription PDFs. |

---

## 2. Technology Ecosystem Breakdown

### 2.1 Backend Runtime & Web Server
- **Language & Runtime:** Python 3.10+ (Tested against Python 3.11.9 and Python 3.12.0 on Windows; deployed on Linux).
- **Application Server:**
  - *Local Development:* Native Werkzeug HTTPS server (`python run.py`) running on `https://localhost:5000` via local self-signed certificates generated by `mkcert`.
  - *Production:* Gunicorn 21.2.0 (`deploy/gunicorn.conf.py`) bound to `127.0.0.1:8000`, running 1 worker with 16 threads (`gthread`), managed by `systemd`.
- **Reverse Proxy:** Nginx (`deploy/nginx-quickcare.conf`) terminating HTTP/HTTPS, serving static files directly from `/var/www/quickcare/app/static/`, and proxying `/socket.io/` WebSocket upgrades to Gunicorn.

### 2.2 Persistence & ORM Layer
- **Database Engine:** SQLite 3 (Database file: `instance/quickcare_dev.db`, size: 393,216 bytes).
- **ORM:** SQLAlchemy 2.0 via Flask-SQLAlchemy 3.0.5.
- **Migration Architecture:** Hybrid / Non-standard. Standard Alembic migrations are absent; schema migrations are performed at application startup via ad-hoc procedural scripts (`app/utils/*_migration.py`) executing direct `ALTER TABLE` queries inside `try...except` blocks.

### 2.3 Real-Time & Asynchronous Layer
- **WebSocket Protocol:** Flask-SocketIO 5.3.6 running with `async_mode='threading'`.
- **Scheduled Background Tasks:** APScheduler 3.10.4 (`BackgroundScheduler(daemon=True)`). Executes three periodic jobs:
  1. `cleanup_expired_payments`: Every 10 minutes.
  2. `check_expired_appointments`: Every 5 minutes.
  3. `process_completion_reviews`: Every 1 hour.
- **Email Asynchrony:** Unmanaged native Python threads (`threading.Thread(target=send_async_email, ...).start()`). No message broker (Redis/RabbitMQ) or task queue (Celery/RQ) is present.

### 2.4 Frontend Stack
- **Templating Engine:** Jinja2 3.1.2 (Server-side rendering).
- **CSS Framework:** Bootstrap 5.3.0 (Delivered via jsDelivr CDN) combined with custom scoped stylesheets (`main.css`, `video-call.css`, `doctor-queue.css`, `footer.css`, `info-pages.css`, `recording-watch.css`).
- **Icons & Typography:** Font Awesome 6.4.0 (CDN) and Google Fonts (`Inter` 300, 400, 500, 600, 700).
- **Rich Text Editing:** TinyMCE (Self-hosted vendored bundle in `app/static/`).
- **Mapping & Geocoding:** Leaflet / OpenFreeMap (Tiles via `https://tiles.openfreemap.org/styles/liberty`) paired with server-side Geoapify Geocoding API proxy.
- **Client WebSockets:** Socket.IO Client JS (CDN / static).
- **Video Consultation Client:** Agora Web RTC SDK v4.x loaded dynamically in `video-call.html`.

---

## 3. External Third-Party APIs & Cloud Services

```mermaid
flowchart LR
    QuickCare["Quick Care Connect (Flask Server)"]
    AgoraRTC["Agora RTC Engine (Audio/Video Streams)"]
    AgoraCloud["Agora Cloud Recording REST API"]
    DOSpaces["DigitalOcean Spaces (S3 Compatible)"]
    Safepay["Safepay API (Sandbox / Production)"]
    Gemini["Google Gemini 1.5 Flash (AI Chat)"]
    OpenRouter["OpenRouter API (AI Fallback)"]
    Namecheap["Namecheap Private Email (SMTP)"]
    Geoapify["Geoapify Geocoding API"]
    OpenFreeMap["OpenFreeMap Tile Servers"]

    QuickCare -->|Token Generation| AgoraRTC
    QuickCare -->|Acquire / Start / Stop| AgoraCloud
    AgoraCloud -->|Upload MP4/HLS| DOSpaces
    QuickCare -->|Presigned Playback URLs| DOSpaces
    QuickCare -->|Tracker Creation & Verification| Safepay
    QuickCare -->|Direct LLM Inference| Gemini
    QuickCare -->|Fallback LLM Inference| OpenRouter
    QuickCare -->|Async SMTP (Port 587 TLS)| Namecheap
    QuickCare -->|Address Resolution Proxy| Geoapify
    QuickCare -.->|Client Browser Tiles| OpenFreeMap
```

### Detailed Integration Breakdown:
1. **Agora RTC & Cloud Recording:**
   - RTC Access: Tokens generated server-side using `agora-token-builder` with dynamic UID, channel names (`appointment_{id}`), and 24-hour expiration.
   - Cloud Recording: Triggered via Agora REST API (`api.sd-rtn.com/v1/apps`). Composite recording saves HLS playlists and MPEG-TS segments directly to DigitalOcean Spaces via S3-compatible API (Vendor code 11).
2. **DigitalOcean Spaces (S3-Compatible Object Storage):**
   - Region: `sgp1` (Singapore 1).
   - Usage: Archival storage of video consultations. Admin playback generates temporary presigned URLs (`boto3.client('s3').generate_presigned_url`) expiring after 3600 seconds.
3. **Safepay Payment Gateway:**
   - Environment: Sandbox (`https://sandbox.api.getsafepay.com`) and Production.
   - Flow: Server generates order tracker tokens (`/order/v1/init`), redirects patient to Safepay hosted checkout, verifies payment upon return via Tracker API (`/order/v1/{tracker_token}`), and handles incoming webhooks.
4. **Google Gemini & OpenRouter AI:**
   - Model: `gemini-1.5-flash` via direct Google Generative Language REST API.
   - Fallback: OpenRouter endpoint (`openrouter/free`) with automated retry logic when Gemini quotas or timeouts occur.
5. **Namecheap Private Email:**
   - SMTP Server: `mail.privateemail.com`, Port 587 with STARTTLS.
6. **Geoapify & OpenFreeMap:**
   - Forward geocoding server proxy (`/api/geocode`) queries Geoapify API to convert clinic addresses to latitude/longitude coordinates; OpenFreeMap delivers map vector tiles without API keys.

---

## 4. Tech Stack Risks & Technical Debt

1. **Undeclared Critical Dependency (`xhtml2pdf`):**  
   Missing from `requirements.txt`. Clean environment setup using `pip install -r requirements.txt` will fail silently during installation and crash with `ModuleNotFoundError` during user checkout / prescription download.
2. **Dead / Superfluous Dependency (`eventlet`):**  
   Declared in `requirements.txt` but unused in application code. Causes severe installation friction on Windows and is fundamentally incompatible with Python 3.12.
3. **Unchecked Binary in Git Repository (`mkcert.exe.exe`):**  
   A 4.8 MB Windows binary executable is tracked directly in the Git repository root. Storing binaries in Git bloats repository size and poses a security risk.
4. **Legacy Mail Package (`Flask-Mail`):**  
   `Flask-Mail` has been unmaintained for nearly a decade. Modern Flask ecosystems use `Flask-Mailman` or direct API clients (SendGrid, Postmark, Mailgun, Amazon SES).
5. **Lack of Caching & In-Memory Store:**  
   No Redis or Memcached instance exists. Session state, AI rate-limiting timestamps, and Socket.IO messages are stored in client cookies, local SQLite tables, or memory variables.

