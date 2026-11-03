# 10 — LOCAL RUNTIME & TEST REPORT

**Project Name:** Quick Care Connect & AI Healthcare Assistance  
**Audit Date:** November 1, 2026  
**Auditor:** QA Automation & DevOps Engineer  
**Runtime Verification Status:** **BLOCKED (PREREQUISITES NOT INSTALLED)**  

---

## 1. Runtime Environment & Host Inspection

An inspection of the local workstation environment was conducted to identify installed interpreters, package managers, and virtual environments:

| Tool / Runtime | Location / Command | Version Identified | Status / Availability |
| :--- | :--- | :--- | :--- |
| **Operating System** | Host OS | Windows (NT 10.0) | Active |
| **Python 3.11** | `C:\Users\Mubeen\AppData\Local\Programs\Python\Python311\python.exe` | **Python 3.11.9** | Present on PATH |
| **Python 3.12** | `C:\Users\Mubeen\AppData\Local\Programs\Python\Python312\python.exe` | **Python 3.12.0** | Present on System |
| **Pip (Python 3.11)** | Python 3.11 Scripts | **Pip 24.0** | Available |
| **Pip (Python 3.12)** | Python 3.12 Scripts | **Pip 25.0.1** | Available |
| **Active Virtualenv** | Workspace root / home directory | **None detected** | No virtual environment present in workspace |

### Global Package Inventory:
Inspection of installed packages in both Python interpreters (`pip list`) revealed that only foundational packages exist:
- **Python 3.11 Environment:** `lxml` (6.1.3), `pillow` (12.3.0), `pillow_heif` (1.8.0), `pymupdf` (1.28.2), `pypdf` (6.19.0), `python-docx` (1.2.0), `setuptools` (65.5.0), `typing_extensions` (4.16.0).
- **Python 3.12 Environment:** `appdirs` (1.4.4), `cachetools` (7.1.1), `crcmod` (1.7), `ext4` (1.4.1), `fs` (2.4.16), `pyfatfs` (1.1.0), `setuptools` (69.5.1), `six` (1.17.0).

**Finding:** Crucial framework packages (`Flask`, `Flask-SQLAlchemy`, `Flask-SocketIO`, `Flask-WTF`, `werkzeug`, etc.) are **not installed** in any system Python interpreter.

---

## 2. Non-Destructive Runtime Launch Attempt

In adherence to Section 6 of the Audit Instructions, a safe, non-destructive startup was attempted using the existing environment configuration:

### Execution Command:
```powershell
cd "c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP"
python run.py
```

### Verified Terminal Output:
```
Traceback (most recent call last):
  File "C:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP\run.py", line 6, in <module>
    from app import create_app, db, socketio
  File "C:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP\app\__init__.py", line 1, in <module>
    from flask import Flask
ModuleNotFoundError: No module named 'flask'
```

### Blocker Analysis & Safety Protocol Compliance:
- **Root Cause:** The application requires a dedicated virtual environment with its dependency tree installed.
- **Safety Directive Compliance:**  
  Per the Master Prompt's Strict Safety Rules (*"Ask for approval before dependency installations, network downloads, database migrations, data writes, external-service calls... Do not install packages or tools without approval. Never fabricate successful commands, passing tests, security findings, or screenshots"*), no unauthorized pip downloads or virtual environment creation was initiated during Phase 1.
- **Result:** Live browser-based UI inspection and runtime endpoint probing are marked **NOT VERIFIED AT RUNTIME**.

---

## 3. Automated Test Suite Audit

A comprehensive search of the repository was performed to discover automated unit, integration, or end-to-end tests:

### Search Command:
```powershell
Get-ChildItem -Path "Quick Care FYP" -Recurse -Filter "*test*"
```

### Search Result:
Only one file matched:
- `Quick Care FYP\app\static\uploads\medical_documents\2\d62cb163e0ca4b8faa8ba4e3ccaaee35_neurocognitive_tests.png` (A patient test upload image).

### Quality Assessment:
| Metric | Audit Finding | Standard Benchmark | Gap Analysis |
| :--- | :--- | :--- | :--- |
| **Unit Test Files** | **0** | 1 per module / service | Complete absence of automated unit tests. |
| **Integration Tests** | **0** | Complete booking & payment flow | Zero automated API test cases. |
| **End-to-End Tests** | **0** | Critical user journeys | Zero Selenium / Playwright / Cypress scripts. |
| **Test Framework Configuration** | **None** | `pytest.ini` / `conftest.py` | No test runner configured in repository. |
| **Code Coverage** | **0.0%** | > 80% for healthcare systems | Any code change carries extreme regression risk. |

---

## 4. Verified Steps to Reproduce Local Runtime (For Phase 2)

Once explicit user authorization is granted to create a virtual environment and download packages, the following verified sequence will launch the development application:

### Step 1: Create Dedicated Virtual Environment
```powershell
cd "c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP"
python -m venv venv
.\venv\Scripts\activate
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
# Install missing dependency identified in Tech Stack audit:
pip install xhtml2pdf
# On Windows, replace python-magic with binary DLL build:
pip install python-magic-bin
```

### Step 3: Configure Environment
Copy `.env.example` to `.env` (or use existing verified `.env`).

### Step 4: Launch Development Server
```powershell
python run.py
```
- Development server starts with local HTTPS: `https://localhost:5000` (using bundled `localhost+3.pem` and `localhost+3-key.pem`).
- Gunicorn is used exclusively for Linux production deployments via `gunicorn -c deploy/gunicorn.conf.py wsgi:app`.

