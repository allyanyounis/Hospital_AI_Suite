# Hospital AI Suite

One clinic dashboard combining two AI tools that share sign-in, data, schedule and look:

- **AI Medical Scribe**: record a consultation, get a speaker-labelled transcript, draft a structured note where
  every line cites the transcript, run a safety check, sign, then generate ICD-10 codes, a task list and letters.
- **AI Voice Receptionist**: a VAPI voice agent that books, checks and cancels appointments inside the clinic's
  hours, with a live appointments board and call transcripts.

**Synthetic data only** until the items in *Before real patients* (below) are done.

## Quick start (Windows)

Requires Python 3.12, Node 20+ and PostgreSQL 17 (running locally).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # venv, npm, database, .env, admin account
powershell -File scripts\dev.ps1                             # backend :8000 + frontend :3004
```

Open http://localhost:3004 and sign in. Then add keys to `backend/.env` (restart the backend after editing):

| Setting | Needed for |
|---|---|
| `NOTE_PROVIDER` | Which AI writes the notes: `claude`, `groq` or `ollama` (local, no key) |
| `ANTHROPIC_API_KEY` | Notes with `NOTE_PROVIDER=claude` (model `NOTE_MODEL`, default `claude-opus-5-5`) |
| `GROQ_API_KEY` | Notes with `NOTE_PROVIDER=groq` (model `GROQ_MODEL`, default `openai/gpt-oss-120b`) |
| `DEEPGRAM_API_KEY` | Scribe live / uploaded audio transcription (sample consultations work without it) |
| `VAPI_SECRET` | Rejects webhook calls that don't come from your VAPI assistant |

The chosen provider handles everything AI in the scribe: note drafting, safety check, ICD-10 codes, task list and
letters. Groq's free plan allows about 8,000 tokens a minute (roughly one note and its safety check); when Groq asks
the app to slow down it waits and retries, so codes, tasks and letters can take 10–30 seconds on the free plan.

The VAPI public key and assistant id go in `frontend/.env.local`.

<details><summary>Manual setup (Windows PowerShell)</summary>

Backend (first terminal):

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env        # then set DATABASE_URL, SESSION_SECRET and your API keys
.\.venv\Scripts\python.exe -m app.users add drrahman --name "Dr. Rahman" --role admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
Copy-Item .env.example .env.local  # then set the VAPI public key and assistant id
npm install
npm run dev
```

Run only **one** backend at a time. Two copies of the project both started on port 8000 will share the port on
Windows and the browser may reach the wrong one.
</details>

## Pointing the VAPI assistant at this backend

Expose port 8000 (e.g. `ngrok http 8000`) and set the assistant's **Server URL** to `https://<tunnel>/vapi`.
Tools can use `/vapi/schedule_appointment`, `/vapi/cancel_appointment` and `/vapi/check_availability`.
The original receptionist URLs (`/schedule_appointment/`, `/list_appointments/`, `/webhook`, …) still work,
so an existing assistant needs no changes. Set the same secret in VAPI and in `VAPI_SECRET`.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests

cd ..\frontend
npm run typecheck
npm run lint
npm run build
```

Backend tests run against the `hospital_ai_test` database with a fake AI model (no API calls, no cost). If that
database doesn't exist, create it once:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -c "CREATE DATABASE hospital_ai_test OWNER hospital_ai;"
```

## How it's built

```
backend/                       FastAPI + SQLAlchemy 2 + PostgreSQL (psycopg 3)
  app/main.py                  App, middleware, routers
  app/config.py                All settings (env / .env)
  app/database.py, models.py   Engine, sessions, tables (users, audit_log, clinic_schedule, encounters, appointments)
  app/security.py              scrypt passwords, signed session cookie, lockout, roles, WebSocket origin check
  app/auth_router.py           /api/login, /api/logout, /api/me, /api/session, /api/config
  app/audit.py                 Audit trail (ids and counts only, never clinical content)
  app/users.py                 Account CLI: python -m app.users add|reset-password|disable|enable|list
  app/schedule/                Shared clinic schedule: hours, breaks, slot length, closed dates (+ /api/schedule)
  app/scribe/                  Scribe API, live transcription WebSocket, metrics, retention
    notes/                     Drafting, safety review, codes, tasks, letters + one adapter per AI provider
                               (claude.py, groq.py, ollama.py)
    transcription/  samples/   Speech-to-text adapters, demo consultations
  app/reception/               Receptionist: booking rules, VAPI payload parsing, public webhooks, dashboard API, live events
  tests/                       29 tests (scribe flow, live stream, booking rules, webhooks, schedule)

frontend/                      Next.js 16 + React 19 + Tailwind 4 (proxies /api/* to the backend)
  src/app/globals.css          The colour theme, defined once (brand-* maroon, amber highlights)
  src/app/login/               Staff sign-in
  src/app/(app)/               Signed-in pages: / (overview), scribe/*, reception/*, schedule, account
  src/components/shell/        Session, sidebar navigation, top bar
  src/components/ui.tsx        Shared cards, stats, notices, toggles, status pills
  src/lib/api/                 Typed API client
```

**Changing the colours:** edit the `--color-brand-*` scale in `frontend/src/app/globals.css` and the matching hex
values in `frontend/src/lib/theme.ts` (used by charts). Every page follows.

## Database

One PostgreSQL database, `hospital_ai`, holds everything (tests use a separate `hospital_ai_test`). Tables are
created automatically when the backend starts and are defined in `backend/app/models.py`. Times are stored with time
zone; transcripts, notes, codes and tasks are stored as JSONB.

| Table | Used by | Holds |
|---|---|---|
| `users` | Both | Staff accounts |
| `audit_log` | Both | Who did what and when (no clinical content) |
| `clinic_schedule` | Both | Clinic hours, breaks, slot length and closed dates (one row) |
| `encounters` | Scribe | One row per consultation: transcript, draft and signed note, codes, tasks |
| `appointments` | Receptionist | Bookings made by the voice agent, with the call transcript |

<details><summary>Columns</summary>

**`users`**

| Column | Type | Notes |
|---|---|---|
| `username` | varchar(64) | Primary key |
| `display_name` | varchar(120) | Shown in the dashboard, e.g. "Dr. Rahman" |
| `role` | varchar(20) | `clinician` or `admin` |
| `password_hash` | varchar(255) | scrypt hash, never the password itself |
| `active` | boolean | Disabled accounts can't sign in |
| `created_at` | timestamptz | |

**`audit_log`**

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | Primary key |
| `ts` | timestamptz | When it happened |
| `username` | varchar(64) | Who did it |
| `action` | varchar(64) | e.g. `login`, `note.approved`, `appointment.booked` |
| `encounter_id` | varchar(32) | Linked consultation, if any |
| `detail` | jsonb | Ids, counts and settings only |

**`clinic_schedule`** (single row, `id = 1`)

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Always 1 |
| `days` | jsonb | 7 entries, Monday first: open or closed, start, end, breaks |
| `slot_minutes` | integer | Appointment length (default 15) |
| `holidays` | date[] | Dates the clinic is closed |
| `updated_at` | timestamptz | |
| `updated_by` | varchar(64) | Who last changed it |

**`encounters`**

| Column | Type | Notes |
|---|---|---|
| `id` | varchar(32) | Primary key |
| `username` | varchar(64) | Clinician; references `users.username` |
| `created_at` | timestamptz | |
| `source` | varchar(20) | `live`, `recording` or `sample` |
| `audio_seconds` | float | Length of the consultation (audio itself is never stored) |
| `transcript` | jsonb | Speaker-labelled transcript segments |
| `clinician_speaker` | integer | Which speaker is the clinician |
| `patient_name`, `patient_mrn`, `patient_sex`, `patient_dob`, `visit_type` | varchar | Patient and visit details |
| `template_id` | varchar(64) | Note template used |
| `note_status` | varchar(20) | Empty → `drafting` → `ready` or `failed` |
| `note_error` | text | Why drafting failed |
| `model` | varchar(120) | AI model that drafted the note |
| `draft_note` | jsonb | AI draft; every line cites transcript segments |
| `draft_seconds` | float | How long drafting took |
| `drafted_at` | timestamptz | |
| `final_note` | jsonb | Note as signed by the clinician |
| `approved_at` | timestamptz | Set when signed |
| `codes` | jsonb | Suggested ICD-10 codes |
| `tasks` | jsonb | Follow-up task list |
| `lines_drafted`, `lines_kept`, `lines_added`, `lines_removed` | integer | Edit counts at sign-off (kept for metrics) |
| `content_purged_at` | timestamptz | When the retention job erased transcript, notes and patient details |

**`appointments`**

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `patient_name` | varchar(120) | |
| `reason` | varchar(255) | Reason for the visit |
| `start_time` | timestamptz | Appointment time |
| `canceled` | boolean | |
| `call_id` | varchar(64) | VAPI call that made the booking |
| `transcript` | text | End-of-call transcript |
| `created_at` | timestamptz | |

</details>

To browse the data in pgAdmin: **Databases → hospital_ai → Schemas → public → Tables**, right-click a table →
**View/Edit Data → All Rows**.

## Governance built in

| Control | How |
|---|---|
| Sign-in | Named accounts created by an admin (no open sign-up), scrypt hashes, signed 12h httpOnly cookie, lockout after 5 failures |
| Access | Every dashboard API requires sign-in; clinicians see only their own encounters; hospital-wide metrics are admin-only |
| Public webhooks | VAPI endpoints never return other patients' names, only free times; optional shared secret |
| Audit trail | Sign-ins, drafts, safety checks, approvals, letters, bookings, cancellations and schedule changes |
| Retention | Scribe transcripts, notes and patient details erased after `RETENTION_DAYS` (default 7); audio never stored |
| Human in the loop | Nothing reaches the record without clinician sign-off; letters only from a signed note |

## Before real patients

This is pilot-ready software, not a cleared deployment. Before any real patient data: data processing agreements
(Anthropic or Groq, Deepgram, VAPI and its model providers) and data residency; hosting inside the hospital network behind
HTTPS (`SECURE_COOKIES=true`) with encrypted, backed-up PostgreSQL; hospital SSO; a clinical safety case signed off
by the clinical safety officer; privacy impact assessment and patient notice/consent for recording; a measured pilot
and accuracy audit. The **Call Costs** page shows sample numbers until VAPI call data is connected.
