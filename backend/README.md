# Backend: Hospital AI Suite API

FastAPI + SQLAlchemy 2 + PostgreSQL 17 (psycopg 3), migrations with Alembic. Python 3.12.

## Run

```powershell
docker compose up -d db                                   # from the repo root: PostgreSQL in Docker
cd backend
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt; .venv\Scripts\pip install --no-deps -e .
copy .env.example .env                                    # then fill in (see Settings)
.venv\Scripts\python -m app users add drrahman --name "Dr. Rahman" --role admin
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs. `scripts\setup.ps1` and `scripts\dev.ps1` at the repo root do all of this.

## Layout

The backend is the core of a Hospital Management System: a platform (`core`) and one package per hospital domain.

```
app/
  main.py            create_app(): middleware, startup (migrate, recover drafts, purge), INSTALLED_MODULES
  __main__.py        CLI: python -m app migrate | users …
  models.py          registry importing every module's tables (for Alembic and tests)
  core/              platform; imports no feature module
    config.py          Settings (env vars / backend/.env)
    database.py        engine, sessions, Base + naming convention, column helpers, init_db() = alembic upgrade
    modules.py         ModuleSpec + load_modules(): the module registry
    clock.py           hospital-local vs UTC time
    audit.py           audit_log table + audit()
    events.py          broadcaster for live dashboard updates
  modules/           one package per hospital domain
    system/            /api/health, /api/config, /api/events (live updates socket)
    auth/              accounts and roles, permissions, sessions, /api/login|me|users, account CLI
    organization/      departments                                      /api/departments
    staff/             staff profiles, bookable doctors                 /api/staff
    patients/          master patient index (registry)                  /api/patients
    scheduling/        doctors' OPD weeks, hospital closed dates        /api/schedules, /api/closures
    appointments/      OPD booking rules for every channel              /api/appointments
    scribe/            encounters, AI notes, codes, tasks, metrics      /api/encounters…, live WS
      notes/  transcription/  samples/
    portal/            the signed-in patient's own data                 /api/portal
    reception/         the voice channel: VAPI webhooks, calls, transcripts   /vapi, legacy URLs
    clinical/          labs, vitals, reports, history, allergies        /api/clinical
    theatre/           theatres, procedures, cases, rosters, leave      /api/theatre
      engine/            the planner: pure functions over an in-memory Snapshot (forecast, risk, board, intake)
      experiment/        CP-SAT replanning experiment (research only; never touches real lists)
      demo.py            synthetic theatre hospital: python -m app seed demo-theatre
migrations/          Alembic env + versions (schema history)
tests/               pytest against hospital_ai_test, fake AI model
```

Dependency direction (no cycles): `organization ← staff ← scheduling ← appointments ← reception, portal`;
`patients` and `auth` are used by everyone; `staff, clinical ← theatre`. Later phases: admissions, laboratory,
pharmacy, billing.

### Inside a module

| File | Holds |
|---|---|
| `__init__.py` | The module's **public API**: the only thing other modules may import |
| `module.py` | `MODULE = ModuleSpec(name, title, routers, setup)`: how the app mounts it |
| `models.py` | Its tables (SQLAlchemy) |
| `schemas.py` | Request/response bodies (Pydantic) |
| `service.py` / named rule files (`booking.py`) | Business rules and data access; no HTTP |
| `router.py` | HTTP routes: check permission, call the rules, audit, commit |

### Rules (enforced by `tests/test_architecture.py`)

1. `app/core` never imports `app/modules`.
2. A module imports another only through its package: `from app.modules.patients import Patient`, never
   `app.modules.patients.models`.
3. Every package in `app/modules` has a `module.py` and is listed in `INSTALLED_MODULES`.
4. Only `main.py`, `models.py` and `__main__.py` sit at the top of `app/`; they wire modules together.
5. A module that needs to attach data to another module's rows owns the link table (e.g. `voice_call_bookings`),
   or uses an extension point (e.g. `appointments.register_detail_provider`), so dependencies point one way.

### Adding a hospital module (e.g. laboratory)

1. `app/modules/laboratory/` with `__init__.py`, `module.py`, `models.py`, `schemas.py`, `service.py`, `router.py`.
2. Add `"laboratory"` to `INSTALLED_MODULES` in `app/main.py` and import its models in `app/models.py`.
3. Add its permissions to `Permission` in `auth/permissions.py` and grant them to roles in `ROLE_PERMISSIONS`.
4. `alembic revision --autogenerate -m "add laboratory"`, review the file, run `pytest`.
5. Frontend: a feature folder with `routes.ts`, one line in `src/features/registry.ts` (see frontend/README.md).

## Dependencies

`pyproject.toml` declares what the app needs (minimum versions). The pinned, reproducible sets are generated from it:

| File | Use |
|---|---|
| `requirements.txt` | Production: `pip install -r requirements.txt && pip install --no-deps .` |
| `requirements-dev.txt` | Development: the same pins plus pytest and ruff |

After changing `pyproject.toml`, regenerate both (commands are at the top of each file) and commit them together.

## Authentication and authorization

Five roles, one permission table: [app/modules/auth/permissions.py](app/modules/auth/permissions.py).

| Permission | admin | doctor | nurse | receptionist | patient |
|---|:-:|:-:|:-:|:-:|:-:|
| `dashboard.view`, `staff.view`, `patients.view`, `appointments.view`, `schedule.view`, `theatre.view` | ✓ | ✓ | ✓ | ✓ | |
| `clinical.view` | ✓ | ✓ | ✓ | | |
| `scribe.use`, `theatre.manage`, `theatre.insights` | ✓ | ✓ | | | |
| `appointments.manage` (cancel), `voice_agent.use` | ✓ | ✓ | | ✓ | |
| `patients.manage`, `appointments.book` | ✓ | | | ✓ | |
| `organization.manage`, `staff.manage`, `users.manage`, `schedule.edit`, `metrics.view_all`, `call_costs.view`, `theatre.roster` | ✓ | | | | |
| `portal.use` | | | | | ✓ |

- **Protecting a route:** `user: User = Depends(require("scribe.use"))` (401 signed out, 403 not allowed);
  `current_user` for anything a signed-in user of any role may do; `websocket_user(ws, "<permission>")` for sockets.
  Never compare role names in code: change what a role may do in `ROLE_PERMISSIONS` only.
- **The UI follows the server:** `/api/login` and `/api/me` return the user's `permissions`, and the frontend
  shows pages and buttons from that list.
- **Sessions:** a signed, httpOnly cookie holding `username | session_version | expiry`. Role, active flag and
  permissions are re-read on every request. Resetting a password, changing a role or disabling an account bumps
  `session_version`, which signs that user out everywhere. Five failed sign-ins lock a username for 15 minutes.
- **Patients** are accounts with role `patient`, linked to exactly one `patients` row (database-enforced).
  They see only `/api/portal/*`, scoped to their own record.
- **Accounts:** admins use `/api/users` (and the Users page); the CLI does the same through `auth/service.py`:

```powershell
.venv\Scripts\python -m app users add drkhan --name "Dr. Khan" --role doctor     # then set the profile in Staff
.venv\Scripts\python -m app users add rita --name "Rita" --role receptionist
.venv\Scripts\python -m app users add ali --name "Ali Khan" --role patient --mrn MRN-001 --dob 1980-01-31
.venv\Scripts\python -m app users list | reset-password <user> | disable <user> | enable <user>
```

## Settings

All settings are in `app/core/config.py`, read from environment variables, then `backend/.env` (found relative
to the code, so the working directory doesn't matter). `.env.example` documents each one. Required for a pilot:
`DATABASE_URL`, `SESSION_SECRET`; for the AI features: `ANTHROPIC_API_KEY` (or `NOTE_PROVIDER=ollama`),
`DEEPGRAM_API_KEY`, `VAPI_SECRET`. Use `127.0.0.1` in `DATABASE_URL`, not `localhost`.

## Database

Schema design: [docs/database.md](../docs/database.md).

```powershell
.venv\Scripts\python -m app migrate                              # apply migrations (also done on start)
.venv\Scripts\alembic revision --autogenerate -m "add x to y"   # after changing a models.py; review it
```

## Checks

```powershell
.venv\Scripts\python -m pytest            # needs the db container; uses hospital_ai_test
.venv\Scripts\ruff check app tests migrations
.venv\Scripts\ruff format --check app tests migrations
```
