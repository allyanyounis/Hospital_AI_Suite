# PHASE 2 — LOCAL RUNTIME SETUP REPORT

## 1. Executive Summary

This report documents the local environment setup, dependency resolution, database isolation, and initial configuration of the **Quick Care Connect** telehealth system on the target Windows workstation. All setup activities were conducted strictly without modifying any application source code files (`app/`, `config.py`, `run.py`).

---

## 2. Environment Details

- **Host Operating System:** Microsoft Windows 11 / Windows Server (win32)
- **Target Python Version:** Python 3.11.9 (`C:\Users\Mubeen\AppData\Local\Programs\Python\Python311\python.exe`)
- **Virtual Environment Location:** `c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP\venv`
- **Pip Version (Upgraded):** 26.2.2
- **Git Branch:** `phase-2-local-run` (Local only, no remotes)

---

## 3. Virtual Environment & Dependency Installation

### 3.1 Creation and Activation Commands
```powershell
cd "c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP"
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3.2 Packages Installed
1. Installed existing declared dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Installed Phase 2 authorized auxiliary packages:
   ```powershell
   pip install xhtml2pdf==0.2.28 python-magic-bin==0.4.14 pytest==9.2.0 pytest-cov==7.1.0
   ```
3. Created `requirements-dev.txt`:
   - `pytest>=9.0.0`
   - `pytest-cov>=7.0.0`
   - `xhtml2pdf>=0.2.28`
   - `python-magic-bin>=0.4.14`

### 3.3 Dependency Health Check (`pip check`)
Output of `pip check`:
```text
No broken requirements found.
```

### 3.4 Package Inventory (`pip freeze`)
The complete frozen dependency list was saved to [`audit-output/phase2/pip-freeze.txt`](pip-freeze.txt) (66 total packages). Core packages include:
- `Flask==2.3.3`
- `Flask-SQLAlchemy==3.0.5`
- `Flask-SocketIO==5.3.6`
- `Flask-WTF==1.1.1`
- `WTForms==3.0.1`
- `Werkzeug==2.3.7`
- `xhtml2pdf==0.2.28`
- `pytest==9.2.0`
- `pytest-cov==7.1.0`

---

## 4. Database Protection & Isolation Protocol (Step 1)

To protect the integrity of the original SQLite database against automated startup migrations (`db.create_all()` and `ALTER TABLE` schema updates) and background scheduler modifications:

### 4.1 Original Database Hash Baseline
- **Original Database File:** `instance/quickcare_dev.db`
- **Initial SHA-256 Hash:** `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850`

### 4.2 Backup & Working Copy Creation
```powershell
New-Item -ItemType Directory -Path "instance\backups" -Force
Copy-Item "instance\quickcare_dev.db" "instance\backups\quickcare_dev_original.db"
Copy-Item "instance\quickcare_dev.db" "instance\quickcare_local_test.db"
```

### 4.3 Redirection Without Code Changes
Inspection of `config.py:38` confirmed that `DevelopmentConfig.SQLALCHEMY_DATABASE_URI` reads:
```python
os.getenv('DEV_DATABASE_URL') or 'sqlite:///quickcare_dev.db'
```
Consequently, the application was directed to run against the working copy purely via process-level environment variable override:
```powershell
$env:DEV_DATABASE_URL = "sqlite:///quickcare_local_test.db"
```
Verification confirmed that the original database `instance/quickcare_dev.db` was not touched.

### 4.4 Final Hash Verification
- **Post-Run SHA-256 Hash:** `170E3E84A920591AD78B32819ED982494C5F1F29B440E60FC8B1A8ECEEC32850`
- **Integrity Status:** **VERIFIED UNCHANGED (100% BIT-FOR-BIT MATCH)**

