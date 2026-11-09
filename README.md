# SchoolOps AI — Automated Operations & Safety Assistant for Principals

SchoolOps AI is an intelligent operations assistant designed for school principals and administrators. It integrates read-only student and school data, live weather and air quality forecasting, deterministic environmental safety policy evaluation, and an approval-controlled parent notification workflow.

---

## Architecture

```
                                  +------------------------------------+
                                  |    School Principal / Client       |
                                  +------------------------------------+
                                             |              |
                                  POST /ask  |              | /drafts, /jobs
                                             v              v
+---------------------------------------------------------------------------------------+
|                               Agent API (Port 8000)                                   |
|                                                                                       |
|   +---------------------+    +-------------------------+    +---------------------+   |
|   |  LLM Orchestrator   |--->|   Deterministic Policy  |--->|    Morning Job      |   |
|   |  (Gemini Flash SDK) |    |   Engine (Thresholds)   |    |    (APScheduler)    |   |
|   +---------------------+    +-------------------------+    +---------------------+   |
|              |                            |                            |              |
|              +----------------------------+----------------------------+              |
|                                           |                                           |
|       +-----------------------------------+-----------------------------------+       |
|       |                     |                         |                       |       |
|       v                     v                         v                       v       |
|  +---------+      +--------------------+      +--------------+      +--------------+  |
|  | In-Mem  |      |   Open-Meteo &     |      | SQLite DB    |      | Fake Sender  |  |
|  | TTL     |      |   Postal PIN APIs  |      | (drafts,     |      | (20% fail,   |  |
|  | Cache   |      |   (Forecast/AQI)   |      |  outbox,     |      |  max 3 retry)|  |
|  +---------+      +--------------------+      |  job_runs)   |      +--------------+  |
|                                               +--------------+                        |
+---------------------------------------------------------------------------------------+
                                           | HTTP (Read-Only)
                                           v
+---------------------------------------------------------------------------------------+
|                               School API (Port 8001)                                  |
|                                                                                       |
|       GET /school/students, /events, /routes, /attendance, /policy, /school           |
|                                          |                                            |
|                                          v (Read-only data access)                    |
|                                  [ school-data.json ]                                 |
+---------------------------------------------------------------------------------------+
```

---

## Setup in 5 Commands

```bash
# 1. Clone repository and navigate to directory
git clone https://github.com/rohan-kapadi/SchoolOps---Yugam-Assignment.git && cd "SchoolOps---Yugam-Assignment"

# 2. Create and activate virtual environment
python -m venv .venv && .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration and add your Gemini API key
cp .env.example .env

# 5. Run test suite to verify installation (all 82 tests pass)
python -m pytest -q
```

---

## Running the Services

Start the two independent services in separate terminal windows:

```bash
# Terminal 1: Read-Only School API (Port 8001)
uvicorn school_api.main:app --port 8001

# Terminal 2: Agent API (Port 8000)
uvicorn agent_api.main:app --port 8000
```

- **School API Docs:** [http://localhost:8001/docs](http://localhost:8001/docs)
- **Agent API Docs & Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Environment Variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | *(Required)* | Google Gemini API Key |
| `LLM_MODEL` | `gemini-3.5-flash` | Gemini model for function calling (`gemini-3.5-flash` / `gemini-2.5-flash`) |
| `SCHOOL_API_URL` | `http://127.0.0.1:8001` | URL of the read-only School API service |
| `DB_PATH` | `schoolops.db` | Path to SQLite database for drafts, outbox, and job runs |
| `SENDER_FAIL_RATE` | `0.2` | Failure rate (0.0 to 1.0) for fake WhatsApp notification sender |
| `DEFAULT_HTTP_TIMEOUT` | `10.0` | Timeout in seconds for HTTP tool requests |

---

## Example cURL Commands

### 1. Natural Language Query (`POST /ask`)
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Can we hold the Annual Sports Day outdoors according to the weather forecast and school policy?"}'
```

### 2. Disambiguating Student Names (`POST /ask`)
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Riya Sharma bus stop?"}'
```

### 3. Run Morning Operational Workflow (`POST /jobs/morning/run`)
```bash
curl -X POST "http://localhost:8000/jobs/morning/run" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-11-10"}'
```

### 4. Review Generated Drafts (`GET /drafts`)
```bash
curl -X GET "http://localhost:8000/drafts?status=PENDING"
```

### 5. Principal Approval (`POST /drafts/{id}/approve`)
```bash
curl -X POST "http://localhost:8000/drafts/1/approve"
```

### 6. View Outbox Messages (`GET /messages`)
```bash
curl -X GET "http://localhost:8000/messages"
```

---

## Test Results & Metrics

- **Total Unit & Integration Tests:** 82 passed (100% green)
- **Safety & Evaluation Suite Score:** 18/18 scenarios passed (100.0%)
- **Test Modules:**
  - `tests/test_school_api.py` (17 tests): endpoint validation, case-insensitivity, 404/422 errors, read-only 405 guards.
  - `tests/test_tools.py` (20 tests): Open-Meteo, India Post, TTL caching, network timeouts, AQI 7-day limits.
  - `tests/test_policy.py` (10 tests): strict boundary tests (AQI 200/201, Temp 40/40.1, Rain 9.9/10, Route 19.9/20, AQI 301 closure recommendation).
  - `tests/test_attendance.py` (4 tests): weekend-skipping consecutive absence streaks, real dataset verification.
  - `tests/test_agent.py` (5 tests): tool loop limit (8 max), trace logging, ambiguity clarification, weather failure handling.
  - `tests/test_workflow.py` (7 tests): workflow idempotency, outbox isolation, approval delivery, sender retry up to 3 attempts.
  - `tests/test_safety.py` (19 tests): 18 named evaluation scenarios covering prompt injection resistance (E4, S100), ground truth facts, and safety evaluation score.

### Performance & Cost Metrics
- **Model Used:** `gemini-3.5-flash` / `gemini-2.5-flash`
- **Average Input Tokens / Query:** ~520 tokens
- **Average Output Tokens / Query:** ~110 tokens
- **Average Cost / Query:** ~$0.000072 USD (~$0.07 per 1,000 queries)

---

## Known Limitations

1. **Air Quality Forecast Window:** Open-Meteo Air Quality forecasts are mathematically constrained to ~7 days ahead. Any query for events further out evaluates strictly to `INCOMPLETE_DATA` (never `SAFE`).
2. **Notification Delivery Simulation:** The current sender is a simulated fake sender with a configurable 20% random failure rate and max 3 retries. In production, this connects to the Meta WhatsApp Business Cloud API.
3. **Data Source:** School data is read from `school-data.json` exclusively by `school_api`. Production deployments would back this with a PostgreSQL or MySQL replica with role-based access control (RBAC).

