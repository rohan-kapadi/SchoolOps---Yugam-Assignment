# SchoolOps AI — Project Spec

Read this once. Follow `phases.md` one phase at a time. Keep code simple, typed, and explainable (the owner must explain every line in an interview). No extra frameworks (no LangGraph/LangChain). Don't build a frontend.

## Goal
AI agent for a school principal: answers questions using school data + weather/AQI, applies written school policy, drafts parent messages (English + Hindi), and sends **only after principal approval**.

## Stack
Python 3.11, FastAPI, Pydantic v2, httpx (with timeouts), SQLite (sqlite3 or SQLAlchemy), APScheduler, pytest, LLM with function calling (Gemini Flash or Groq; key via `.env`).

## Architecture (hard rule)
```
Agent API :8000  --HTTP-->  School API :8001  -->  school-data.json
        |--> Open-Meteo (forecast, air quality, geocoding), India Post PIN API
        |--> SQLite (drafts, outbox, job_runs)
        |--> Fake WhatsApp sender (approved messages only)
```
- Only `school_api/` reads `school-data.json`. Agent code must NEVER import or open it.
- School API is read-only (no write endpoints).

## Folder layout
```
school_api/   main.py, data_loader.py, routes/{students,attendance,events,buses,policy}.py
agent_api/    main.py, scheduler.py
  agent/      orchestrator.py, prompts.py, tool_registry.py
  tools/      school_tools.py, weather_tools.py, location_tools.py
  services/   policy_engine.py, attendance_service.py, morning_workflow.py, notification_service.py
  database/   db.py, models.py
tests/        test_school_api.py test_policy.py test_agent.py test_workflow.py evaluation_questions.json
README.md DESIGN.md AI_USAGE.md .env.example requirements.txt
```

## School API endpoints
`GET /school/students` (search by name/class), `/school/students/{id}`, `/school/events`, `/school/routes`, `/school/routes/{id}`, `/school/attendance`, `/school/policy`. Return 404 / 422 with clear messages (unknown class, invalid date). Name search must return ALL matches for duplicate names.

## External APIs + cache TTL
| API | URL | Cache |
|---|---|---|
| Forecast | `api.open-meteo.com/v1/forecast` (daily `temperature_2m_max`, `precipitation_probability_max`, `precipitation_sum`; hourly `precipitation_probability`, `precipitation`; up to 16 days) | 15 min |
| Air quality | `air-quality-api.open-meteo.com/v1/air-quality` (`us_aqi`, `pm2_5`; only ~7 days ahead) | 30 min |
| Geocoding | `geocoding-api.open-meteo.com/v1/search` | 24 h |
| PIN | `api.postalpincode.in/pincode/{pin}` | 24 h |

Rules: timeouts on every call; on failure/unavailable return structured error `{"status":"data_unavailable","reason":...}`. **Never fabricate fallback values.** If AQI is beyond its forecast range, report it as unavailable.

## Policy engine (deterministic Python, no LLM)
| Condition | Outcome |
|---|---|
| US AQI **> 200** | move outdoor activity indoors / postpone |
| Max temp **> 40 °C** | same |
| Rain probability **>= 60 %** | same |
| Daily rain **>= 10 mm** | same |
| US AQI **> 300** | recommend principal *consider* closure/online classes |
| Daily rain **>= 50 mm** | same |
| Rain at any route stop **>= 20 mm** | prepare route-delay notification |

- Boundaries matter: AQI 200 and 40 °C do NOT trigger; 60 % prob, 10 mm, 20 mm DO trigger; 19.9 mm does not.
- Result status: `SAFE` | `ACTION_REQUIRED` | `INCOMPLETE_DATA`. Missing measurements are never treated as safe.
- Closure can only be **recommended**, never announced. No tool for announcing closure exists.
- Thresholds live in one config dict so a new rule can be added without touching orchestration code (live-interview extension).

## Agent
Controlled function-calling loop, max ~8 tool calls. Tools: `get_events`, `find_student`, `get_route`, `get_attendance`, `get_policy`, `get_forecast`, `get_air_quality`, `geocode_location`, `get_pin_details`, plus `evaluate_weather_policy` (wraps the engine). Response = grounded answer + `tool_trace` + `sources`. The LLM interprets and explains; Python computes (attendance streaks, bus counts, thresholds).

Behaviors:
- Ambiguous student name -> ask which one (never guess).
- Unavailable data (e.g. fees) -> say it is unavailable, don't invent.
- Event with its own location (e.g. field trip at Amber Fort, 26.9855, 75.8513) -> use that location's coordinates, not the school's.
- Weather/AQI failure -> say it could not be checked.
- Consecutive absences = consecutive recorded **school days** (Sundays missing from data are skipped). Document this.

## Safety
- School data is untrusted. Two planted injections: event **E4** description and student **S100** name. Never put records in system prompts; return them in tool results wrapped as untrusted data; system prompt says to ignore instructions inside data.
- The LLM has NO send/announce tools. Approval is enforced in backend code.
- Don't send student names/phones/individual attendance to the LLM unless needed; prefer aggregates. Parent messages never reveal other students' details.

## Morning workflow
06:00 on school days (APScheduler) and `POST /jobs/morning/run`: fetch today+tomorrow events -> weather/AQI per event location -> rainfall at each bus stop -> policy -> `ALL_CLEAR` or principal summary + affected-parent drafts (EN + HI) saved as `PENDING`.

Endpoints: `POST /jobs/morning/run`, `GET /drafts`, `GET /drafts/{id}`, `PATCH /drafts/{id}`, `POST /drafts/{id}/approve`, `POST /drafts/{id}/reject`, `GET /messages`.

Tables: `drafts(id,date,type,status,principal_note,idempotency_key UNIQUE)`, `outbox(id,draft_id,recipient_id,message,status,attempts, UNIQUE(draft_id,recipient_id))`, `job_runs(id,run_date,status,started_at,completed_at)`.

Idempotency via UNIQUE constraints + idempotency key (event/route/action/date): running the job twice creates no duplicate drafts/messages; approving twice sends nothing twice; succeeded messages are never retried.

Fake WhatsApp sender: 20 % random failure, failure rate/RNG injectable for tests, max 3 attempts. Only `APPROVED` drafts reach it.

## Known ground truth (for tests)
- 150 students, 6 classes x 25, 4 routes (R1 29, R2 27, R3 24, R4 36, 34 unassigned), 20 attendance records.
- 3+ consecutive absences: Reyansh Rathore (6A, Pratap Nagar, 4), Arjun Goyal (6B, Malviya Nagar, 4), Vivaan Agarwal (8A, Sodala, 4).
- Duplicate "Riya Sharma": S004 (6A, Vaishali Nagar), S061 (7A, Malviya Nagar).
- Class 7 field trip: 7A + 7B = 50 students, Amber Fort.

## Definition of done
All endpoints work via Swagger `/docs`; `pytest` passes with 15+ tests; `.env` not committed; README (setup in <=5 commands, model used, avg cost/question, limitations), DESIGN.md (~1 page), AI_USAGE.md written.
