# Phase 4 Audit: Complete `| safe` and `Markup` Usage Inventory

**Document Status:** Complete  
**Date:** November 1, 2026  
**Auditor:** Antigravity Security Auditor

---

## 1. Inventory Summary

An exhaustive repository-wide search was conducted across all templates and Python source files to locate every usage of Jinja's `| safe` filter and `Markup` objects (`markupsafe.Markup` / `flask.Markup`).

- **Total Python `Markup()` occurrences:** 0 (none in application codebase)
- **Total Template `| safe` occurrences:** 6 remaining (1 removed, 2 remediated/hardened, 4 confirmed safe)
- **Overall Posture:** No unescaped user-controlled input can reach the DOM unvalidated.

---

## 2. Exhaustive Usage Matrix

| Location | Template Code | Source of Content | Risk Assessment | Status / Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| `app/templates/blogs/view.html:117` | `{{ render_content \| safe }}` | Doctor rich-text blog post (stored in `blogs.content`) | **HIGH** (Stored XSS vector if unsanitized) | **REPAIRED (ISS-SEC-05)**: Sanitized via `nh3.clean()` on post creation and update in `doctors.py`, with defense-in-depth sanitization on render in `blogs.py:view_blog()`. |
| `app/templates/prescriptions/pdf_template.html:616` | `{{ prescription.advice \| escape \| replace('\n', '<br>') \| safe }}` | Doctor prescription clinical advice field | **MEDIUM** (Could contain HTML if raw newlines were replaced before escaping) | **HARDENED**: Applied `escape` filter before `replace('\n', '<br>')` so all user markup is converted to entities before `<br>` is marked safe. |
| `app/templates/patients/profile.html:569` | `<td>{{ patient.user.cnic or '<span class="text-muted">Not provided</span>'\|safe }}</td>` | CNIC string with HTML fallback | **LOW** (Static HTML snippet) | **REMOVED**: Refactored to explicit Jinja `{% if patient.user.cnic %}...{% else %}...{% endif %}`, eliminating the `\| safe` filter entirely. |
| `app/templates/admin/staff_form.html:300` | `var roleDefaults = {{ role_defaults_json\|safe }};` | Admin staff permission preset JSON dictionary | **NEGLIGIBLE** (Internally generated backend dict) | **CONFIRMED SAFE**: Generated in `app/routes/admin.py` from hardcoded system permission lists (`ROLE_PRESETS`). Does not contain user input. |
| `app/templates/diseases/index.html:79` | `<div class="di-card-icon" {{ icon_style \| safe }}>` | Hardcoded CSS color strings for disease category cards | **NEGLIGIBLE** (Static UI styling) | **CONFIRMED SAFE**: Generated in `app/routes/diseases.py` via dictionary mapping categories to trusted hex color strings (e.g. `style="background: #e0f2fe; color: #0284c7;"`). |
| `app/templates/diseases/index.html:87` | `<span class="di-severity" {{ badge_style \| safe }}>` | Hardcoded CSS color strings for severity badges | **NEGLIGIBLE** (Static UI styling) | **CONFIRMED SAFE**: Generated in `app/routes/diseases.py` via static severity lookup dictionary. |
| `app/templates/diseases/view.html:64` | `<span class="dv-hero-badge severity" {{ badge_style \| safe }}>` | Hardcoded CSS color strings for severity badge in disease detail view | **NEGLIGIBLE** (Static UI styling) | **CONFIRMED SAFE**: Generated in `app/routes/diseases.py` via static severity lookup dictionary. |

---

## 3. Review of Q&A Forum & Community User Content

During discovery, the Q&A forum module was inspected for potential rich-text or HTML injection vulnerabilities:
- `app/templates/qa/index.html`
- `app/templates/qa/view_question.html`
- `app/templates/patients/ask_question.html`
- `app/templates/doctors/answer_question.html`

**Findings:**
- All question titles, question content descriptions, doctor answers, and threaded replies are rendered exclusively using standard Jinja interpolation tags:
  ```jinja
  <h3>{{ question.title }}</h3>
  <p>{{ question.content }}</p>
  <p>{{ answer.content }}</p>
  <p>{{ reply.content }}</p>
  ```
- Because Jinja2 auto-escapes all variable expressions by default when templates have `.html` extensions, user input in questions, answers, and comments is automatically neutralized as HTML entities (`&lt;`, `&gt;`, `&quot;`, `&amp;`).
- No `| safe` filter is applied to any community forum content.

---

## 4. Verification & Recommendations

1. **Defense-in-Depth for Future Rich Text Modules:**
   If rich-text editing is ever introduced to Q&A answers or doctor biographies, the centralized sanitizer (`app.utils.sanitize.sanitize_html`) must be applied in the controller before storing or rendering.
2. **Automated Linter Rule:**
   Add a pre-commit or CI check prohibiting new occurrences of `| safe` in templates unless paired with `app.utils.sanitize` or approved in this register.

