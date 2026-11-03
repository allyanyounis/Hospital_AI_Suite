# Hospital AI Suite

The core of a **Hospital Management System**: departments, staff and roles, a master patient index, doctors' OPD
schedules and appointments, built so further hospital services (admissions and beds, laboratory, pharmacy,
billing) plug in as modules. Two AI tools run on top of it:

- **AI Medical Scribe**: record a consultation, get a speaker-labelled transcript, draft a structured note where
  every line cites the transcript, run a safety check, sign, then generate ICD-10 codes, a task list and letters.
- **AI Voice Receptionist**: a VAPI voice agent that books, checks and cancels appointments with the right doctor
  inside their OPD hours, alongside front-desk booking, a live appointments board and call transcripts.

Plus a **patient chart** (labs, vitals, reports, history, allergies) and an **operating theatre planner**: a live
board of every theatre's list with a Monte Carlo forecast of overrunning past 16:00, a suggested case to move and
where, emergency intake by NCEPOD urgency, booking against surgeons' rosters and leave, per-case risk (VitalDB
model, EuroSCORE II), and a research page (risk model audit, CP-SAT replanning experiment). Load the synthetic
theatre hospital with `python -m app seed demo-theatre` (from `backend/`).

**Synthetic data only** until the items in *Before real patients* (below) are done.

## Quick start (Windows)

Requires Python 3.12, Node 20+ and Docker Desktop (PostgreSQL 17 runs in a container).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # once: db container, venv, npm, env files, migrations, admin
powershell -File scripts\dev.ps1                             # every time: db + backend :8000 + frontend :3004
```

Open http://localhost:3004 and sign in. API docs: http://localhost:8000/docs.

## Configuration (env files)

Every setting comes from an env file (or the environment, which wins). All three are git-ignored; each has a
documented example next to it.

| File | Read by | Holds |
|---|---|---|
| `.env` (repo root) | `docker compose` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` for the container |
| `backend/.env` ([example](backend/.env.example)) | the API | `DATABASE_URL`, `SESSION_SECRET`, `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `VAPI_SECRET`, `HOSPITAL_NAME`, `HOSPITAL_TIMEZONE`, governance settings |
| `frontend/.env.local` ([example](frontend/.env.example)) | Next.js | `NEXT_PUBLIC_VAPI_PUBLIC_KEY`, `NEXT_PUBLIC_VAPI_ASSISTANT_ID`, `BACKEND_URL`, `NEXT_PUBLIC_BACKEND_PORT` / `NEXT_PUBLIC_BACKEND_WS_URL` |

| Key | Needed for |
|---|---|
| `NOTE_PROVIDER` | Which AI writes the notes: `claude` (default), `groq` or `ollama` (local, no key) |
| `ANTHROPIC_API_KEY` | Notes with `NOTE_PROVIDER=claude` (model `NOTE_MODEL`, default `claude-opus-5-5`) |
| `GROQ_API_KEY` | Notes with `NOTE_PROVIDER=groq` (model `GROQ_MODEL`, default `openai/gpt-oss-120b`) |
| `DEEPGRAM_API_KEY` | Scribe live / uploaded audio transcription (sample consultations work without it) |
| `VAPI_SECRET` | Rejects webhook calls that don't come from your VAPI assistant |

The chosen provider handles everything AI in the scribe: note drafting, safety check, ICD-10 codes, task list and
letters. Groq's free plan allows about 8,000 tokens a minute (roughly one note and its safety check); when Groq asks
the app to slow down it waits and retries, so codes, tasks and letters can take 10–30 seconds on the free plan.

Use `127.0.0.1` rather than `localhost` in `DATABASE_URL` and `BACKEND_URL`: on Windows `localhost` tries IPv6
first and the container listens on IPv4. Restart the backend after editing `backend/.env`, and the frontend after
editing `frontend/.env.local`.

Run only **one** backend at a time. Two copies of the project both started on port 8000 share the port on Windows,
and the browser may reach the wrong (older) one.

<details><summary>Manual setup (any OS)</summary>

```bash
docker compose up -d db                             # PostgreSQL 17 on 127.0.0.1:5432 (+ hospital_ai_test)

cd backend
python -m venv .venv && .venv/Scripts/activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt && pip install --no-deps -e .   # pinned (prod: requirements.txt)
cp .env.example .env                                # set DATABASE_URL and SESSION_SECRET
python -m app migrate                               # the API also migrates on start
python -m app users add drrahman --name "Dr. Rahman" --role admin
uvicorn app.main:app --reload --port 8000

cd frontend && cp .env.example .env.local && npm install && npm run dev    # second terminal
```
</details>

## Roles

| Role | Sees |
|---|---|
| **admin** | Everything below, plus departments, staff profiles, user accounts, OPD schedule editing, surgeons' theatre rosters and leave, the theatre demo clock, hospital-wide metrics and call costs |
| **doctor** | Dashboard, patients and their clinical chart, appointments, AI scribe (own encounters and metrics), theatre board with booking, moving and emergency intake, theatre model check, schedules (read-only), staff directory, voice agent test |
| **nurse** | Dashboard, patients and their clinical chart, appointments, theatre board, schedules and staff directory, read-only |
| **receptionist** | Dashboard, patient registration, front-desk booking and cancelling, theatre board (read-only), schedules, staff directory, voice agent test |
| **patient** | **My appointments** portal: their own profile and appointments |

What each role may do is a single table in `backend/app/modules/auth/permissions.py`; the frontend reads the
signed-in user's permissions from the API, so changing that table changes both. Details: `backend/README.md`.

**Doctors and departments:** an admin creates departments, then gives each staff account a profile (department,
title, specialty, registration number). Profiles marked **bookable** get their own OPD week (OPD Schedules page)
and take appointments; hospital-wide closed dates apply to everyone.

## Pointing the VAPI assistant at this backend

Expose port 8000 (e.g. `ngrok http 8000`) and set the assistant's **Server URL** to `https://<tunnel>/vapi`.
Tools can use `/vapi/schedule_appointment`, `/vapi/cancel_appointment` and `/vapi/check_availability`.
The original receptionist URLs (`/schedule_appointment/`, `/list_appointments/`, `/webhook`, …) still work,
so an existing assistant needs no changes. Set the same secret in VAPI and in `VAPI_SECRET`.

With **one** bookable doctor the agent books as before. With several, add an optional `doctor` (name) and/or
`department` (name or code) argument to the booking and availability tools; when neither identifies one doctor, the
reply asks the caller which doctor or department they want and lists who takes appointments. When VAPI sends the
caller's number, a registered patient with that phone number and name is recognised.

## How it's built

Both apps are split into **feature modules** that mirror each other, with shared code kept apart:

| Hospital domain | Backend `app/modules/` | Frontend `src/features/` |
|---|---|---|
| Accounts, roles, sign-in | `auth` | `auth`, `account`, `users` |
| Departments | `organization` | `organization` |
| Staff profiles, bookable doctors | `staff` | `staff` |
| Master patient index (registry) | `patients` | `patients` |
| Doctors' OPD weeks, closed dates | `scheduling` | `schedule` |
| OPD appointments (all channels) | `appointments` | `appointments` |
| AI medical scribe | `scribe` (+ `notes/`, `transcription/`, `samples/`) | `scribe` |
| AI voice receptionist (a booking channel) | `reception` | `reception` |
| Patient portal | `portal` | `portal` |
| Labs, vitals, reports, history, allergies | `clinical` | `clinical` (chart at `/patients/[id]`) |
| Operating theatres (planner, rosters, insights) | `theatre` (+ `engine/`, `experiment/`) | `theatre` |
| Health, config, live events | `system` | — |
| App frame, overview | — | `shell`, `dashboard` |

```
compose.yaml                   PostgreSQL 17 container (credentials from root .env)
backend/                       FastAPI + SQLAlchemy 2 + Alembic — see backend/README.md
  app/core/                    settings, database, module registry, clock, audit trail, live events
  app/modules/<domain>/        __init__ (public API) · module · models · schemas · service · router
  app/main.py · models.py · __main__.py   INSTALLED_MODULES · table registry · CLI (migrate, users)
  migrations/                  schema history
  tests/                       pytest on PostgreSQL, incl. module-boundary and migration checks
frontend/                      Next.js 16 + React 19 + Tailwind 4 — see frontend/README.md
  src/app/                     routes only; each page renders a feature view
  src/features/<feature>/      index.ts (public API) · routes · api · types · components · views
  src/features/registry.ts     every feature's routes: navigation and page access are derived from it
  src/shared/                  http client, UI kit, hooks, formatting, chart theme
  src/config/env.ts            the only place that reads NEXT_PUBLIC_* variables
scripts/                       setup.ps1 (once), dev.ps1 (daily)
docs/database.md               schema, ER diagram and class diagram
```

Module rules (enforced by `backend/tests/test_architecture.py`, and by convention in the frontend): shared
infrastructure never imports a feature; features use each other only through their public `__init__` / `index.ts`.

**Adding a hospital service** (e.g. laboratory) is adding a module on each side: a backend package with `module.py`
listed in `INSTALLED_MODULES`, its tables, permissions and a migration; a frontend feature with `routes.ts` listed in
`src/features/registry.ts`. Step by step: `backend/README.md` and `frontend/README.md`. Planned next phases:
admissions and beds, laboratory, pharmacy, billing.

**Changing the colours:** edit the `--color-brand-*` scale in `frontend/src/app/globals.css` and the matching hex
values in `frontend/src/shared/lib/theme.ts` (used by charts). Every page follows.

## Database

PostgreSQL 17 in Docker, schema normalised to 3NF and managed by Alembic. Tables: `users`, `audit_log`,
`departments`, `staff_members`, `patients`, `doctor_schedules` / `schedule_days` / `schedule_breaks` /
`hospital_closures`, `appointments`, `voice_calls` / `voice_call_bookings`, `encounters` / `encounter_codes` /
`encounter_tasks`, the clinical tables (`lab_tests` / `lab_results`, `vital_signs`, `clinical_reports`,
`clinical_history`, `patient_allergies`) and the theatre tables (`theatres`, `procedures`, `surgical_cases` /
`preop_assessments`, `theatre_rosters`, `staff_leave`). Schema, ER diagram, class diagram and design decisions:
[docs/database.md](docs/database.md).

To change the schema: edit the owning module's `models.py`, run `alembic revision --autogenerate -m "..."` in
`backend/`, review the generated file, run the tests. `docker compose down -v` wipes the database.

A database from before the normalised schema (created by `create_all`, or by the earlier one-file
`0001_initial_schema` migration) can't be upgraded in place: the backend refuses to start on it and says so. It
only ever held synthetic data, so drop and recreate it (or `docker compose down -v`) and start again.

## Checks

```bash
cd backend  && .venv/Scripts/python -m pytest && .venv/Scripts/ruff check app tests migrations
cd frontend && npm run typecheck && npm run lint && npm run build
```

Backend tests run against the `hospital_ai_test` database in the container with a fake AI model (no API calls,
no cost). They also fail if the migrations and models describe different schemas, or a module imports another
module's internals.

## Governance built in

| Control | How |
|---|---|
| Sign-in | Named accounts created by an admin (no open sign-up), scrypt hashes, signed 12h httpOnly cookie, lockout after 5 failures; password resets, role changes and disabling sign the user out everywhere |
| Access | Five roles (**admin**, **doctor**, **nurse**, **receptionist**, **patient**) mapped to permissions in one table ([permissions.py](backend/app/modules/auth/permissions.py)); every API checks a permission; the UI shows only what the user's permissions allow; doctors see only their own encounters; patients see only their own profile and appointments |
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
