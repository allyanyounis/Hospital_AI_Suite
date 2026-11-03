# PHASE 2 — LOCAL APPLICATION STARTUP LOG

## 1. Execution Command & Environment

```powershell
cd "c:\Users\Mubeen\Desktop\Quick Care FYP\Quick Care FYP"
$env:DEV_DATABASE_URL = "sqlite:///quickcare_local_test.db"
$env:ENABLE_EMAILS = "false"
$env:AGORA_ENABLE_RECORDING = "false"
.\venv\Scripts\python.exe run.py
```

---

## 2. Server Configuration & Endpoints

- **Server Interface:** `0.0.0.0:5000`
- **Primary Loopback URL:** `https://127.0.0.1:5000`
- **Network Interface URL:** `https://192.168.1.17:5000`
- **Protocol:** HTTPS (SSL/TLS Enabled)
- **Certificates Employed:**
  - Certificate: `localhost+3.pem`
  - Private Key: `localhost+3-key.pem`
- **Debug Mode:** `True` (active with Werkzeug interactive debugger and PIN)
- **Database Engine:** SQLite 3 (`instance/quickcare_local_test.db`)

---

## 3. Sanitized Terminal Startup Transcript

```text
Werkzeug appears to be used in a production deployment. Consider switching to a production web server instead.
[EXPIRY CHECK] Completed at 2026-11-01 18:32:09
[18:32:09] Scheduler started (payment 10m, completion 1h, expiry 5m)
No appointments need auto-completion
[2026-11-01 18:32:09] No expired payments found.
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on https://127.0.0.1:5000
 * Running on https://192.168.1.17:5000
Press CTRL+C to quit
 * Restarting with stat
Werkzeug appears to be used in a production deployment. Consider switching to a production web server instead.
 * Debugger is active!
 * Debugger PIN: 589-588-650
127.0.0.1 - - [01/Nov/2026 18:32:19] "GET / HTTP/1.1" 200 -
```

---

## 4. Startup Warnings & Observations

1. **Development Server Notice:** Werkzeug development server is serving the Flask application. As confirmed in Phase 1, Gunicorn and Nginx production configurations in `deploy/` are deferred ("Deferred: not deployed").
2. **Interactive Debugger PIN:** Debug mode is enabled (`DEBUG = True`), exposing the interactive Werkzeug pin `589-588-650`.
3. **Database Migration Hooks:** Startup hooks executed `ensure_accounts_schema()`, `ensure_admin_rbac_schema()`, `ensure_qa_schema()`, and `ensure_review_flow_schema()` cleanly against `quickcare_local_test.db`.
4. **HTTPS / SSL Handshake:** Self-signed local SSL certificate (`localhost+3.pem`) successfully negotiated TLS handshakes with modern browser engines (Microsoft Edge) and Python requests clients using loopback certificate validation bypass.

