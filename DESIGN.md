# SchoolOps AI — Technical Design Document

## Why Two Services?

SchoolOps AI separates data ownership and agent reasoning into two independently deployable services:

| Service | Port | Responsibility |
|---|---|---|
| **School API** | 8001 | Sole reader of `school-data.json`. Provides typed, validated REST endpoints for all school records. |
| **Agent API** | 8000 | Orchestrates the LLM tool-calling loop, holds SQLite state for drafts and outbox, calls external weather APIs, and enforces approval before any notification is dispatched. |

**Why separation?** The School API acts as the single trusted source of truth for student and event data. The Agent API never imports or directly opens `school-data.json`, preventing accidental data leakage if the agent layer were compromised. This mirrors a production microservice split between a data service and a business logic/AI gateway.

---

## Tool-Calling Flow

```
Principal asks question
         |
         v
[ AgentOrchestrator.ask() ]
         |
         v
1. Build conversation history with system prompt
2. POST to Gemini (v1beta function-calling API)
         |
         v
3. Gemini returns FunctionCall(name, args)
         |
         v
4. Backend dispatches: TOOL_DISPATCH[name](**args)
   |- School tools → httpx → School API (read-only)
   |- Weather tools → httpx → Open-Meteo API (cached)
   |- Location tools → httpx → Open-Meteo Geocoding / India Post API (cached)
   |- policy_engine → evaluate_weather_policy() → pure Python
   |- attendance_service → consecutive_absences() → pure Python
         |
         v
5. Tool result wrapped in FunctionResponse and appended to conversation
6. Loop: If Gemini returns another FunctionCall, repeat from step 3
   (Hard max: 8 tool calls)
         |
         v
7. Gemini returns natural language answer
8. Return { answer, tool_trace, sources }
```

---

## Why Policy Is Deterministic

Weather and AQI thresholds are evaluated entirely in pure Python (`policy_engine.py`) with explicit boundary conditions. The LLM **never evaluates thresholds** — it only receives the already-computed result (`SAFE`, `ACTION_REQUIRED`, `INCOMPLETE_DATA`).

This design choice is critical for correctness, auditability, and testability:
- Boundary tests run in milliseconds with zero API cost.
- Threshold changes require editing only `config.py > POLICY_RULES` (demoed in the interview extension question).
- The LLM interprets and explains the computed result — it cannot override or reinterpret the thresholds.

---

## How Unauthorized Actions Are Prevented

Three independent enforcement layers protect against unauthorized school closure announcements and unsolicited parent messages:

1. **No Send Tool Exposed**: The LLM tool registry (`tool_registry.py`) does not include any tool for sending messages, announcing closures, or broadcasting alerts. Even if prompted to, the LLM cannot perform these actions.

2. **Backend Approval Enforcement**: Message dispatch (`notification_service.py`) checks `draft.status == 'PENDING'` or `'APPROVED'` before populating the outbox. Status transitions are enforced by SQLite constraints and backend logic — the API can only approve after explicit principal action via `POST /drafts/{id}/approve`.

3. **Prompt Injection Resistance**: The system prompt explicitly instructs the model to treat all school data fields as untrusted text. School records returned by tools are wrapped in `{"untrusted_data": ...}` envelopes and the system prompt states that any instructions embedded inside data fields must be ignored. Two planted injections (Event E4's description and Student S100's name) are verified to have zero effect in `test_safety.py`.

---

## Student Data Privacy

Student personally identifiable information (PII — names, phone numbers, home areas, attendance records) is handled with the following protections:

- **Never in system prompts**: Student PII is only surfaced in tool results, inside `untrusted_data` envelopes.
- **Aggregates preferred**: The attendance service returns streak counts per student only (name, class, home area, streak) rather than the full raw attendance history.
- **Parent messages are generic**: Route delay and event notifications describe the route/event generically and never include any individual student's name, attendance record, or other student's details.
- **Production changes needed**: In production, the full student list including parent phone numbers would only be accessible to the notification dispatch service via a service-account-scoped database role, not to any LLM context.

---

## Production Hardening Recommendations

1. Replace `school-data.json` with a managed PostgreSQL or MySQL instance with RBAC.
2. Swap `FakeSender` for the **Meta WhatsApp Business Cloud API** (`messages` endpoint) with idempotency keys and delivery webhooks.
3. Add Redis-based distributed TTL caching instead of the current in-process cache (which resets on worker restart).
4. Enforce rate limiting on `POST /ask` to prevent abuse.
5. Add structured logging and OpenTelemetry traces on tool calls for cost and latency monitoring.
6. Use Kubernetes Secrets or Google Cloud Secret Manager for `LLM_API_KEY` instead of `.env` files.

