# PHASE 2 — EXTERNAL SERVICES INVENTORY & ISOLATION REPORT

## 1. Overview & Security Rules

All external services were audited by variable names only. In accordance with Phase 2 isolation rules, no secrets, tokens, API keys, or private URLs are disclosed in this document. Real emails were completely suppressed, cloud storage writes were neutralized, and third-party AI endpoints were tested under controlled invocation caps.

---

## 2. Configured Services & Environment Variables

| Service Category | Environment Variables Present in `.env` | Environment Classification | Local Run Behavior / Isolation Mechanism |
| :--- | :--- | :--- | :--- |
| **Email Service** | `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | Production / Live SMTP credentials present | **FULLY SUPPRESSED.** Injected `$env:ENABLE_EMAILS = "false"`. Verified zero outgoing SMTP socket connections. |
| **Video Telehealth** | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `AGORA_CUSTOMER_KEY`, `AGORA_CUSTOMER_SECRET` | Live Agora App Credentials | **RECORDING SUPPRESSED.** `$env:AGORA_ENABLE_RECORDING = "false"`. Real-time WebRTC token generation was authorized and functional. |
| **Cloud Storage** | `DO_SPACES_KEY`, `DO_SPACES_SECRET`, `DO_SPACES_ENDPOINT`, `DO_SPACES_BUCKET`, `DO_SPACES_REGION` | Live DigitalOcean Spaces S3 bucket | **ZERO WRITES.** No S3 `put_object` or `delete_object` operations performed. Local disk fallback used. |
| **Payment Gateway** | `SAFEPAY_API_KEY`, `SAFEPAY_V1_SECRET_KEY`, `SAFEPAY_ENVIRONMENT`, `SAFEPAY_WEBHOOK_SECRET` | **Sandbox** (`SAFEPAY_ENVIRONMENT=sandbox`, endpoint `https://sandbox.api.getsafepay.com`) | **SAFE.** Mock manual payment flow was utilized for local appointment approval lifecycle. |
| **AI LLM Services** | `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | Development keys | **LIMITED TEST (2 calls total).** Handled via automatic fallback pipeline. |
| **Job Scheduler** | `SCHEDULER_ENABLED` (in `config.py`) | Local APScheduler | Observed run completed on `quickcare_local_test.db` with 0 unintended database modifications. |

---

## 3. Controlled AI Provider Test Results

Per Step 2 instructions, a maximum of 5 test calls was authorized to evaluate the live status of the AI chatbot integration:

### Test Call 1 — Google Gemini (`gemini-1.5-flash`)
- **API Endpoint:** Google Generative Language API (`v1beta`)
- **Model Declared:** `models/gemini-1.5-flash`
- **HTTP Response:** `HTTP 404 Not Found`
- **Error Detail:** `{"error": {"code": 404, "message": "models/gemini-1.5-flash is not found for API version v1beta", "status": "NOT_FOUND"}}`
- **Finding:** The endpoint string `models/gemini-1.5-flash` against the legacy `v1beta` endpoint in `AIChatbotService._call_gemini` failed due to API version deprecation or model naming updates.

### Test Call 2 — OpenRouter Fallback
- **API Endpoint:** OpenRouter Chat Completions (`https://openrouter.ai/api/v1/chat/completions`)
- **Model:** `meta-llama/llama-3-8b-instruct:free`
- **HTTP Response:** `HTTP 401 Unauthorized`
- **Error Detail:** `{"error": {"message": "API key expired.", "code": 401}}`
- **Finding:** The OpenRouter token configured in `.env` is expired.

### Heuristic Fallback Pipeline Verification
- When both external providers failed, `AIChatbotService` automatically routed the request to `_fallback_reply()`:
  ```json
  {
    "success": true,
    "response": "Hello! I am Quick Care AI Assistant. While our cloud AI services are momentarily updating, I can still guide you to consult our certified doctors...",
    "llm_provider": "fallback"
  }
  ```
- **Conclusion:** The resilience fallback mechanism operates as designed, ensuring zero runtime crashes when cloud AI endpoints fail.

---

## 4. APScheduler Observed Run

- **Target Database:** `instance/quickcare_local_test.db`
- **Scheduler Jobs:** Payment expiry (10 min), auto-completion (1 hr), appointment expiry (5 min)
- **Database Modification Delta:** Monitored via `diff_dbs.py`.
- **Observed Row Changes:** **0 rows altered** during clean initial startup run.

