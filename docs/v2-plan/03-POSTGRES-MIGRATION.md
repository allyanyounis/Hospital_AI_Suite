# Quick Care V2 — Deliverable 03: PostgreSQL & pgvector Migration Plan

**Document:** `docs/v2-plan/03-POSTGRES-MIGRATION.md`  
**Purpose:** Architecture, tooling, schema migration, indexing strategy, and code adaptations required to transition from SQLite 3 to PostgreSQL 16+ with `pgvector` running in Docker.

---

## 1. Local Environment Strategy: Docker Desktop with WSL2 (Selected)

Per user authorization, Quick Care V2 standardizes on **Docker Desktop for Windows backed by WSL2**. This guarantees 100% reproducibility across development machines, eliminates native Windows C-compiler dependencies for `pgvector`, and mirrors Linux production deployments.

### 1.1 Root `docker-compose.yml` Specification
The PostgreSQL 16 + pgvector container is configured in the project root:

```yaml
version: '3.8'
services:
  quickcare-postgres:
    image: pgvector/pgvector:pg16
    container_name: quickcare_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-quickcare_dev}
      POSTGRES_USER: ${POSTGRES_USER:-quickcare_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-quickcare_secure_local_pass}
    ports:
      # Strictly bound to loopback 127.0.0.1 for host security
      - "127.0.0.1:5432:5432"
    volumes:
      - quickcare_pgdata:/var/lib/postgresql/data
volumes:
  quickcare_pgdata:
```

### 1.2 Environment Variables (`.env` and `.env.example`)
Variables read by `docker-compose.yml` and Flask SQLAlchemy:
```ini
# PostgreSQL 16 + pgvector (Local Docker Container)
POSTGRES_DB=quickcare_dev
POSTGRES_USER=quickcare_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DATABASE_URL=postgresql://quickcare_user:your_postgres_password@127.0.0.1:5432/quickcare_dev
TEST_DATABASE_URL=postgresql://quickcare_user:your_postgres_password@127.0.0.1:5432/quickcare_test
```

---

## 2. Alembic & Flask-Migrate: Replacing Ad-Hoc Migrations

### 2.1 The Current Defect
In the legacy codebase (`app/__init__.py`), 5 procedural functions run at startup on every app context:
- `ensure_accounts_schema()`
- `ensure_qa_schema()`
- `ensure_review_flow_schema()`
- `ensure_review_fraud_schema()`
- `ensure_admin_rbac_schema()`

These execute raw SQL `ALTER TABLE` via `PRAGMA table_info` inside `try...except Exception: pass`, which causes concurrency deadlocks, locks database files, and silently swallows structural schema errors.

### 2.2 Flask-Migrate Baseline Plan
1. **Remove Startup Alter Calls:** Strip all `ensure_*_schema()` calls from `app/__init__.py:create_app()`.
2. **Initialize Alembic Structure:**
   ```bash
   flask db init
   ```
3. **Generate Initial PostgreSQL Baseline:**
   Generate a comprehensive first migration capturing all 29 models, foreign keys, constraints, and the vector extension:
   ```bash
   flask db migrate -m "0001_initial_postgres_baseline"
   ```
4. **pgvector Extension Initialization:** Inside `0001_initial_postgres_baseline.py`:
   ```python
   def upgrade():
       op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
       # ... create all tables ...
   ```
5. **Execution Command:**
   ```bash
   flask db upgrade
   ```

---

## 3. Indexing Architecture & Missing Foreign Key Fixes

PostgreSQL enforces foreign key constraints but does **not** automatically index foreign key columns. Full table scans during dashboard queries and appointment lookups must be eliminated by adding explicit composite and foreign key indexes in Alembic.

### Critical Indexes to Add:

```sql
-- Appointments Core & Life Cycle Lookups
CREATE INDEX idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor_id ON appointments(doctor_id);
CREATE INDEX idx_appointments_status_payment ON appointments(status, payment_status);
CREATE INDEX idx_appointments_date_time ON appointments(appointment_date, appointment_time);

-- Clinical Records & Consultation Gate Lookups
CREATE INDEX idx_medical_histories_appointment_id ON medical_histories(appointment_id);
CREATE INDEX idx_medical_histories_patient_id ON medical_histories(patient_id);
CREATE INDEX idx_prescriptions_appointment_id ON prescriptions(appointment_id);
CREATE INDEX idx_medical_documents_patient_visible ON medical_documents(patient_id, is_visible_to_doctor);

-- Doctor Financial Ledger & Moderation Lookups
CREATE INDEX idx_doctor_transactions_doctor_id ON doctor_transactions(doctor_id);
CREATE INDEX idx_doctor_payout_requests_doctor_id ON doctor_payout_requests(doctor_id);
CREATE INDEX idx_blogs_status_published ON blogs(status, published_at);
CREATE INDEX idx_reviews_doctor_status ON reviews(doctor_id, status);
CREATE INDEX idx_admin_panel_grants_admin_id ON admin_panel_grants(admin_id);
```

---

## 4. SQLite-Specific Code Adaptations

### 4.1 JSON Column Type Conversion
- **SQLite:** Uses generic `db.JSON` or `db.Text` storage with Python serialization.
- **PostgreSQL:** Update `Doctor.time_slots`, `Doctor.degree_documents`, `Review.tags`, and `MedicalHistory.chat_logs` to use `sqlalchemy.dialects.postgresql.JSONB`.
- **Benefit:** Enables native JSON path queries and GIN indexing on structured slots.

### 4.2 Full-Text Search Adaptation
- **SQLite:** Uses slow `LIKE '%query%'` queries in `diseases.py` and `qa.py`.
- **PostgreSQL:** Add a generated `tsvector` column with GIN index on `Disease (name, symptoms, overview)` and `Question (title, content)`:
  ```sql
  ALTER TABLE diseases ADD COLUMN search_vector tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(symptoms, ''))) STORED;
  CREATE INDEX idx_diseases_fts ON diseases USING GIN(search_vector);
  ```

### 4.3 Disease Route Python Loop Optimization (`app/routes/diseases.py`)
- **Legacy Flaw:** Lines 68–73 loaded all approved doctors in the database into Python memory and iterated in a `for` loop to match specialties.
- **PostgreSQL Adaptation:**
  ```python
  # Replaced with direct parameterized index scan
  related_doctors = Doctor.query.filter(
      func.lower(Doctor.category) == func.lower(disease_cat),
      Doctor.is_approved.is_(True),
      Doctor.is_verified.is_(True)
  ).limit(3).all()
  ```

### 4.4 Date & Time Synchronization
All model datetime timestamps (`created_at`, `updated_at`, `mutual_call_start`) are standardized to `db.DateTime(timezone=True)`, storing normalized UTC on disk and translating to Pakistan Standard Time (`Asia/Karachi`) in view serialization.

---

## 5. PostgreSQL Test Strategy

To prevent SQLite vs PostgreSQL dialect divergence, tests run against an active PostgreSQL instance:
1. **Pytest Fixture (`tests/conftest.py`):** Connects to `TEST_DATABASE_URL` and manages database initialization.
2. **Sub-Second Transaction Rollbacks:**
   Each test function wraps its execution inside an isolated database transaction that rolls back on test teardown:
   ```python
   @pytest.fixture(autouse=True)
   def run_around_tests():
       connection = db.engine.connect()
       transaction = connection.begin()
       options = dict(bind=connection, binds={})
       session = db.create_scoped_session(options=options)
       db.session = session
       yield
       transaction.rollback()
       connection.close()
       session.remove()
   ```
   *Result:* 64+ integration tests execute in < 4 seconds with zero disk cleanup overhead.

---

## 6. Concurrency Note: Multi-Worker Readiness
Migrating to PostgreSQL eliminates SQLite's single-writer database lock. In future deployment phases, Gunicorn can immediately scale from a single thread to multi-worker concurrency:
```python
# deploy/gunicorn.conf.py
workers = 4  # (2 x CPU cores) + 1
threads = 2
worker_class = 'gthread'
```
*Note: Gunicorn multi-worker deployment is an operational benefit of this migration, but production server provisioning remains outside the immediate demo milestone.*
