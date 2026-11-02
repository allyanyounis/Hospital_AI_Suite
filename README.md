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
| `ANTHROPIC_API_KEY` | Scribe note drafting, safety check, codes, tasks, letters (or `NOTE_PROVIDER=ollama` for local) |
| `DEEPGRAM_API_KEY` | Scribe live / uploaded audio transcription (sample consultations work without it) |
| `VAPI_SECRET` | Rejects webhook calls that don't come from your VAPI assistant |

The VAPI public key and assistant id go in `frontend/.env.local`.

<details><summary>Manual setup (any OS)</summary>

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate     # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                                # set DATABASE_URL and SESSION_SECRET
python -m app.users add drrahman --name "Dr. Rahman" --role admin
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend && cp .env.example .env.local && npm install && npm run dev
```
</details>

## Pointing the VAPI assistant at this backend

Expose port 8000 (e.g. `ngrok http 8000`) and set the assistant's **Server URL** to `https://<tunnel>/vapi`.
Tools can use `/vapi/schedule_appointment`, `/vapi/cancel_appointment` and `/vapi/check_availability`.
The original receptionist URLs (`/schedule_appointment/`, `/list_appointments/`, `/webhook`, …) still work,
so an existing assistant needs no changes. Set the same secret in VAPI and in `VAPI_SECRET`.

## Checks

```bash
cd backend  && .venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check app tests
cd frontend && npm run typecheck && npm run lint && npm run build
```

Backend tests run against the `hospital_ai_test` database with a fake AI model (no API calls, no cost).

## How it's built

```
backend/                       FastAPI + SQLAlchemy 2 + PostgreSQL (psycopg 3)
  app/main.py                  App, middleware, routers
  app/config.py                All settings (env / .env)
  app/database.py, models.py   Engine, sessions, tables (users, audit_log, clinic_schedule, encounters, appointments)
  app/security.py              scrypt passwords, signed session cookie, lockout, roles, WebSocket origin check
  app/auth_router.py           /api/login, /api/logout, /api/me, /api/config
  app/audit.py                 Audit trail (ids and counts only, never clinical content)
  app/users.py                 Account CLI: python -m app.users add|reset-password|disable|enable|list
  app/schedule/                Shared clinic schedule: hours, breaks, slot length, closed dates (+ /api/schedule)
  app/scribe/                  Scribe API, live transcription WebSocket, metrics, retention
    notes/  transcription/  samples/   LLM drafting/review/codes/letters, speech-to-text adapters, demo cases
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
(Anthropic, Deepgram, VAPI and its model providers) and data residency; hosting inside the hospital network behind
HTTPS (`SECURE_COOKIES=true`) with encrypted, backed-up PostgreSQL; hospital SSO; a clinical safety case signed off
by the clinical safety officer; privacy impact assessment and patient notice/consent for recording; a measured pilot
and accuracy audit. The **Call Costs** page shows sample numbers until VAPI call data is connected.
