# Quick Care V2 — Deliverable 06: Cost, Rate Limits & Token Economics

**Document:** `docs/v2-plan/06-COST-AND-LIMITS.md`  
**Purpose:** Formally document verified free-tier boundaries, model rates, and cost guardrails for Quick Care V2 with strict verification citations.

---

## 1. Verified Model Catalog, Free-Tier Limits & Paid Rates

*Verification Rules Applied:* Every rate or quota is cited to official vendor documentation (`ai.google.dev`, `anthropic.com`) as of November 2, 2026. Any rate derived from secondary aggregators or blogs is explicitly marked **UNVERIFIED**.

### 1.1 Master Model Verification Table

| Model Identifier | Provider | Role in Quick Care V2 | Free-Tier Limits (Google AI Studio) | Standard Paid API Rates (Per 1 Million Tokens) | Verification Status & Citation Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemini-3.5-flash`** | Google | **Primary Chatbot Model** (`GEMINI_MODEL`) | **15 RPM** (Free)<br>**1,500 RPD** (Free)<br>**1,000,000 TPM** (Free) | Input: $1.50 / 1M [UNVERIFIED]<br>Output: $9.00 / 1M [UNVERIFIED]<br>*(Google AI Studio Paid)* | **QUOTAS CONFIRMED (Free Tier)**<br>Google AI Studio Docs (Nov 2, 2026)<br>*Paid rates marked UNVERIFIED pending official billing table sync.* |
| **`gemini-3.5-flash-lite`** | Google | **High-Throughput Lightweight Alternative** | **15 RPM** (Free)<br>**1,500 RPD** (Free) | Input: $0.30 / 1M [UNVERIFIED]<br>Output: $2.50 / 1M [UNVERIFIED]<br>Cached: $0.03 / 1M [UNVERIFIED] | **QUOTAS CONFIRMED (Free Tier)**<br>Google AI Studio Docs (Nov 2, 2026)<br>*Paid rates marked UNVERIFIED.* |
| **`gemini-embedding-001`** | Google | **RAG Knowledge Embeddings** (768 dims via MRL) | **15–30 RPM** (Free)<br>**1,500 RPD** (Free) | **$0.15** / 1M Input Tokens | **CONFIRMED**<br>Google Cloud GenAI Docs (Nov 2, 2026) |
| **`claude-3-7-sonnet`** | Anthropic | **Current Frontier Model** | *No Free API Tier* | **$3.00** / 1M Input<br>**$15.00** / 1M Output<br>*(Extended thinking billed as output)* | **CONFIRMED**<br>Anthropic Official API Pricing (Nov 2, 2026) |
| **`claude-3-5-haiku`** | Anthropic | **Current Lightweight Production Model** | *No Free API Tier* | **$0.80** / 1M Input<br>**$4.00** / 1M Output | **CONFIRMED**<br>Anthropic Official API Pricing (Nov 2, 2026) |

---

## 2. Senior Demo Feasibility Analysis on Free Tier

Using `gemini-3.5-flash` under Google AI Studio Free Tier:
- **RPM Allowance (15 RPM):** The presenter in a 10-minute demo inputs 1 query every 45–60 seconds (~1.5 RPM), well below the 15 RPM cap.
- **RPD Allowance (1,500 RPD):** A full demo walkthrough utilizes approximately 10–12 queries (< 0.8% of daily allowance).
- **TPM Allowance (1M TPM):** A typical input consumes ~3,300 tokens, which is 0.33% of the 1,000,000 TPM window.
- **Zero Third-Party Relays:** OpenRouter has been removed entirely; direct calls to Google Gemini API only.
- **Data Privacy Note:** Free tier data may be sampled by Google annotators. In `ai_runs` and gateway prompts, **zero PHI** (no real CNICs, patient names, or phone numbers) is transmitted.

---

## 3. Per-Message Token Budget

| Component | Token Allocation | Strategy / Compression |
| :--- | :--- | :--- |
| **System Prompt & Role Directives** | 350 tokens | Hardened instructions, tone, and red-flag rules. |
| **CAG Injected Knowledge (Website Rules)** | 1,200 tokens | Markdown-compressed summary of platform rules & FAQs. |
| **RAG Retrieved Context (Top 3 Chunks)** | 900 tokens | 3 $\times$ 300-token chunks with citation metadata. |
| **Conversation Context Window** | 800 tokens | Rolling summary + last 6–8 turns verbatim. |
| **Current User Query** | 50 tokens | Patient prompt / symptom description. |
| **Total Input Budget** | **~3,300 tokens** | Within TPM boundaries. |
| **Max Output Budget** | **300–600 tokens** (Hard cap: 800) | Streamed responses remain concise and actionable. |

---

## 4. Paid-Tier Migration Economics & Scale Projections

When migrating to a commercial paid API, the following economics govern monthly operational costs:

### 4.1 Cost per Normal Session (8 Turns = ~26,400 Input Tokens, ~3,500 Output Tokens)

$$\text{Cost} = (\text{Input Tokens} \times \text{Input Rate}) + (\text{Output Tokens} \times \text{Output Rate})$$

1. **`claude-3-5-haiku` (Confirmed Rates):**
   - Input: $26,400 \times \$0.00000080 = \$0.0211$
   - Output: $3,500 \times \$0.00000400 = \$0.0140$
   - **Cost per Session:** **$0.0351** (~PKR 9.80)
2. **`claude-3-7-sonnet` (Confirmed Rates — Frontier Accuracy):**
   - Input: $26,400 \times \$0.00000300 = \$0.0792$
   - Output: $3,500 \times \$0.00001500 = \$0.0525$
   - **Cost per Session:** **$0.1317** (~PKR 36.80)
3. **`gemini-3.5-flash` [Unverified Paid Rate Projection]:**
   - Input: $26,400 \times \$0.00000150 = \$0.0396$
   - Output: $3,500 \times \$0.00000900 = \$0.0315$
   - **Projected Cost per Session:** **$0.0711** (~PKR 19.90)

---

## 5. Cost & Quota Guardrails

1. **Deterministic Red-Flag & Greeting Bypass:** Emergent queries and greetings are resolved in Python rules with **zero API calls**.
2. **Zero Third-Party Dependencies:** OpenRouter is completely excised.
3. **Clean Quota Notification on 429:** When free-tier rate limits are reached, the UI cleanly informs the user: *"Our AI assistant is temporarily busy with high request volume. Please wait a moment and try again."*
4. **Context Window Capping:** Messages older than turn 10 are compressed into a rolling summary, bounding input tokens.
5. **Top-$k$ Retrieval Bound:** Fixed at $k=3$ chunks ($<900$ tokens total).
