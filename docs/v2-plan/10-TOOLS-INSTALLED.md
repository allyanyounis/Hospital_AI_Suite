# Quick Care V2 — Deliverable 10: Tools & Environment Installation Log

**Document:** `docs/v2-plan/10-TOOLS-INSTALLED.md`  
**Purpose:** Audit log of all developer tools, container runtime engines, database drivers, and pinned versions installed and verified for Quick Care V2.

---

## 1. Tool Installation Ledger

| Tool / Component | Exact Version | Official Source | Command / Specification | Verification Status | Operational Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WSL2 Platform** | `v3.0.3` (Kernel `6.18.54.1`) | Microsoft | `wsl --status` | **VERIFIED (Active)** | Running WSL2 with default distribution `docker-desktop`. |
| **Docker Desktop for Windows** | `4.97.0` | Official Docker (`winget`) | `winget install Docker.DockerDesktop` | **VERIFIED (Active)** | Docker Desktop UI active with WSL2 engine backend. |
| **Docker CLI** | `29.9.2` (build `a82e528`) | Bundled with Docker Desktop | `docker --version` | **VERIFIED (Active)** | Tested and passed with `docker run --rm hello-world`. |
| **Docker Compose** | `v5.6.1` | Bundled CLI plugin | `docker compose version` | **VERIFIED (Active)** | Orchestrates local development containers via root `docker-compose.yml`. |
| **PostgreSQL 16 + pgvector** | `pgvector/pgvector:pg16` | Official Docker Hub | Root `docker-compose.yml` (`docker compose up -d`) | **VERIFIED (Running)** | Container `quickcare_postgres` running. Port strictly bound to `127.0.0.1:5432->5432/tcp`. Volume `quickcare_pgdata`. |
| **pgvector Extension** | `v0.8.7` | Precompiled in image | `CREATE EXTENSION IF NOT EXISTS vector;` | **VERIFIED (Installed)** | Extension created in `quickcare_dev`. Vector version confirmed: `0.8.7`. |
| **PostgreSQL Python Driver** | `psycopg[binary]` `3.3.6` | PyPI (Official) | `pip install "psycopg[binary]==3.3.6"` | **VERIFIED (Installed)** | Modern Psycopg 3 driver with precompiled libpq binaries. Pinned in `requirements.txt`. |
| **Python pgvector Client** | `pgvector` `0.5.1` | PyPI (Official) | `pip install "pgvector==0.5.1"` | **VERIFIED (Installed)** | Official Python bindings for PostgreSQL pgvector extension. Pinned in `requirements.txt`. |

---

## 2. PostgreSQL Driver Architecture Selection: `psycopg[binary]` vs `psycopg2-binary`

### 2.1 Comparative Analysis
1. **`psycopg2-binary` (Legacy):**
   - The older generation C-wrapper for libpq.
   - Currently in maintenance mode; lacks native support for modern Python 3.11/3.12 async/sync type-hinting.
   - Known C-extension build issues on newer platforms.
2. **`psycopg[binary]` (Psycopg 3 — Selected):**
   - Completely rewritten modern driver for Python 3.8+.
   - Officially recommended by the SQLAlchemy 2.0 core team (`postgresql+psycopg://...`).
   - Native support for binary COPY protocol (crucial for high-speed bulk ingestion of vector embeddings).
   - Bundles pre-compiled binary libpq wheels, guaranteeing zero Visual C++ compiler requirements on Windows.

### 2.2 Recommendation
**Selected:** `psycopg[binary]` pinned in `requirements.txt` when Phase 3 begins.
