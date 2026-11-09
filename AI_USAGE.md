# AI Usage Log — SchoolOps AI

This file documents how AI coding assistants were used during the development of this project.

---

## Tools Used

| Phase | Tool |
|---|---|
| Phase 1 — School API | Cursor (AI autocomplete + inline edit) |
| Phase 2 — External tools & caching | Cursor |
| Phase 3 — Policy engine & attendance | Cursor |
| Phase 4 — LLM agent / /ask endpoint | Antigravity (agentic coding assistant) |
| Phase 5 — Morning workflow & approvals | Antigravity |
| Phase 6 — Safety & evaluation suite | Antigravity |
| Phase 7 — Documentation & frontend | Antigravity |

---

## Helpful Prompts Used

**Prompt 1 — Setting up the tool-calling loop (Phase 4)**
> "Implement a multi-turn Gemini function-calling loop using the google-genai SDK with `http_options={'api_version': 'v1beta'}`. The agent should append `FunctionResponse` as `Content(role='user')` and stop after a maximum of 8 tool calls. Expose 11 tools but never expose a send or announce-closure tool to the LLM."

This helped establish the correct multi-turn pattern. The assistant correctly identified that automatic function calling (AFC) would not work and that explicit `types.FunctionDeclaration` schemas were needed.

**Prompt 2 — Idempotent morning workflow (Phase 5)**
> "Implement a morning workflow that runs at 06:00, checks weather and AQI for all outdoor events and bus routes, and creates PENDING drafts. Use `ON CONFLICT(idempotency_key) DO NOTHING` so running the job multiple times is safe. No messages should be sent without principal approval."

This produced the correct SQLite idempotency pattern and the approval-gated dispatch chain.

**Prompt 3 — Safety test suite (Phase 6)**
> "Write a pytest safety suite that verifies: (1) prompt injection in event descriptions and student names is ignored, (2) the agent never sends a WhatsApp/SMS directly, (3) threshold evaluation is deterministic (no LLM), (4) student data is wrapped in an `untrusted_data` envelope, (5) the /ask endpoint rejects empty questions."

This generated 18 targeted safety checks covering the main threat vectors.

---

## One Wrong AI Output and How It Was Caught

### Parameter Name Shadowing in `weather_tools.py`

**What happened:**
During Phase 2, the AI generated the weather tools and imported `from datetime import date`. However, the function definition for `get_forecast` had a parameter also named `date: str`. Inside the function, the AI wrote:
```python
parsed = date.fromisoformat(date)
```
Because the string parameter `date` shadowed the imported `date` class, Python threw:
`AttributeError: 'str' object has no attribute 'fromisoformat'`.

**How it was caught:**
Running `pytest tests/test_tools.py` immediately caught the crash during unit test execution.

**How it was fixed:**
Aliased the module import to `from datetime import date as dt_date` and called `dt_date.fromisoformat(date)`. The AI was then instructed to use distinct variable names whenever parsing date strings.

---

## Notes

- The LLM API key is in `.env` and is **never committed** to git.
- The model `gemini-3.5-flash` was used (confirmed working; `gemini-2.5-flash` hits a 20 req/day free-tier limit).
- All agent outputs were verified against the ground-truth `school-data.json` before being accepted.
- The policy engine (`policy_engine.py`) was written as pure deterministic Python — no LLM was used for threshold decisions.

