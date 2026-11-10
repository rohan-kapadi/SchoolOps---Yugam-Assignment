"""Morning operational workflow evaluating events, route rain, and policy triggers."""

from datetime import date as dt_date, datetime, timedelta
from typing import Any
import httpx

from agent_api.database.db import db_session, init_db
from agent_api.services.policy_engine import evaluate_weather_policy
from agent_api.tools.location_tools import resolve_event_coordinates
from agent_api.tools.school_tools import get_events, get_routes
from agent_api.tools.weather_tools import get_air_quality, get_forecast


def run_morning_workflow(
    run_date: str | dt_date | None = None,
    db_path: str | None = None,
    client: httpx.Client | None = None,
    simulate_adverse_weather: bool = False,
) -> dict[str, Any]:
    """Execute 06:00 AM school day morning operational check.

    1. Checks events today and tomorrow for outdoor weather and air quality policy.
    2. Checks route stops for rainfall >= 20 mm.
    3. Creates PENDING drafts for human approval or ALL_CLEAR record.
    4. Enforces idempotency via UNIQUE(idempotency_key).
    """
    if run_date is None:
        today_date = dt_date.today()
    elif isinstance(run_date, str):
        today_date = dt_date.fromisoformat(run_date)
    else:
        today_date = run_date

    today_str = today_date.strftime("%Y-%m-%d")
    tomorrow_str = (today_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # Ensure tables are initialized
    init_db(db_path)

    job_id = None
    with db_session(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO job_runs (run_date, status, started_at) VALUES (?, 'STARTED', datetime('now'));",
            (today_str,),
        )
        job_id = cursor.lastrowid

    alerts_created: list[dict[str, Any]] = []
    closure_recommended = False
    closure_reasons: list[str] = []

    # ==========================================
    # 1. Event Checks (Today and Tomorrow)
    # ==========================================
    events_res = get_events(client=client)
    events = events_res.get("data", []) if events_res.get("status") == "ok" else []

    relevant_events = [
        e for e in events
        if str(e.get("date")) in (today_str, tomorrow_str)
    ]

    for ev in relevant_events:
        ev_id = ev.get("id")
        ev_date = str(ev.get("date"))
        ev_title = ev.get("title", "Event")
        is_outdoor = bool(ev.get("outdoor", False))

        # Check weather at event specific coordinates
        lat, lon = resolve_event_coordinates(ev.get("lat"), ev.get("lon"))
        if simulate_adverse_weather:
            w_res = {
                "status": "ok",
                "data": {
                    "date": ev_date,
                    "max_temp": 28.0,
                    "rain_probability_max": 85,
                    "rain_sum": 35.0,
                    "hourly_rain": [],
                },
            }
            aq_res = {"status": "ok", "data": {"us_aqi": 120}}
        else:
            w_res = get_forecast(lat, lon, ev_date, client=client)
            aq_res = get_air_quality(lat, lon, ev_date, client=client)

        policy_eval = evaluate_weather_policy(w_res, aq_res)

        if policy_eval.get("closure_recommendation"):
            closure_recommended = True
            closure_reasons.extend(policy_eval.get("reasons", []))

        # If outdoor event requires action due to adverse environmental conditions
        if is_outdoor and policy_eval.get("status") == "ACTION_REQUIRED":
            summary = (
                f"Adverse weather alert for outdoor event '{ev_title}' ({ev_id}) on {ev_date}: "
                f"{'; '.join(policy_eval.get('reasons', []))}. Move indoors or postpone."
            )
            key = f"{ev_date}:EVENT_OUTDOOR:{ev_id}:POSTPONE_OR_INDOOR"

            alerts_created.append({
                "date": ev_date,
                "type": "EVENT_OUTDOOR",
                "status": "PENDING",
                "summary": summary,
                "idempotency_key": key,
                "target_id": ev_id,
            })

    # ==========================================
    # 2. Bus Route Rainfall Checks (Today)
    # ==========================================
    routes_res = get_routes(client=client)
    routes = routes_res.get("data", []) if routes_res.get("status") == "ok" else []

    for route in routes:
        route_id = route.get("id")
        route_name = route.get("name", f"Route {route_id}")
        stops = route.get("stops", [])

        stop_rainfalls: list[float] = []
        if simulate_adverse_weather:
            stop_rainfalls = [35.0]
        else:
            for stop in stops:
                s_lat = stop.get("lat")
                s_lon = stop.get("lon")
                if s_lat is not None and s_lon is not None:
                    stop_w = get_forecast(s_lat, s_lon, today_str, client=client)
                    if stop_w.get("status") == "ok":
                        r_sum = stop_w.get("data", {}).get("rain_sum") or 0.0
                        stop_rainfalls.append(float(r_sum))

        route_policy = evaluate_weather_policy(
            weather={"max_temp": 30.0, "rain_probability_max": 10, "rain_sum": 0.0},
            air_quality={"us_aqi": 100},
            route_rain=stop_rainfalls,
        )

        if route_policy.get("route_delay"):
            max_r = max(stop_rainfalls) if stop_rainfalls else 20.0
            summary = (
                f"Bus {route_name} ({route_id}) delayed: peak rainfall along route stops reached {max_r:.1f} mm "
                "(exceeds 20.0 mm safety delay threshold). Expect 20-30 min delays."
            )
            key = f"{today_str}:ROUTE_DELAY:{route_id}:DELAY_NOTIFICATION"

            alerts_created.append({
                "date": today_str,
                "type": "ROUTE_DELAY",
                "status": "PENDING",
                "summary": summary,
                "idempotency_key": key,
                "target_id": route_id,
            })

    # ==========================================
    # 3. Store Drafts & Principal Summary / ALL_CLEAR
    # ==========================================
    with db_session(db_path) as conn:
        for alert in alerts_created:
            conn.execute(
                """
                INSERT INTO drafts (date, type, status, summary, idempotency_key, target_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO NOTHING;
                """,
                (
                    alert["date"],
                    alert["type"],
                    alert["status"],
                    alert["summary"],
                    alert["idempotency_key"],
                    alert["target_id"],
                ),
            )

        if alerts_created or closure_recommended:
            # Generate principal overview summary draft
            reasons_summary = "; ".join(closure_reasons) if closure_reasons else "Operational weather alerts pending approval."
            closure_note = ""
            if closure_recommended:
                closure_note = " [CRITICAL POLICY NOTE: Severe environmental triggers met; recommend principal consider school closure or online classes.]"

            principal_summary = (
                f"Morning Operational Summary for {today_str}: {len(alerts_created)} parent notification draft(s) pending."
                f"{closure_note} Details: {reasons_summary}"
            )
            summary_key = f"{today_str}:PRINCIPAL_SUMMARY:ALL:DAILY_REPORT"

            conn.execute(
                """
                INSERT INTO drafts (date, type, status, summary, idempotency_key, target_id)
                VALUES (?, 'PRINCIPAL_SUMMARY', 'PENDING', ?, ?, 'ALL')
                ON CONFLICT(idempotency_key) DO NOTHING;
                """,
                (today_str, principal_summary, summary_key),
            )
        else:
            # ALL_CLEAR day creates NO parent drafts
            all_clear_summary = (
                f"Morning Operational Check for {today_str}: ALL CLEAR. "
                "Weather, AQI, and route conditions are safe for normal school operations."
            )
            all_clear_key = f"{today_str}:ALL_CLEAR:ALL:NO_ACTION"

            conn.execute(
                """
                INSERT INTO drafts (date, type, status, summary, idempotency_key, target_id)
                VALUES (?, 'ALL_CLEAR', 'ALL_CLEAR', ?, ?, 'ALL')
                ON CONFLICT(idempotency_key) DO NOTHING;
                """,
                (today_str, all_clear_summary, all_clear_key),
            )

        # Mark job run as completed
        if job_id:
            conn.execute(
                "UPDATE job_runs SET status = 'COMPLETED', completed_at = datetime('now') WHERE id = ?;",
                (job_id,),
            )

    return {
        "status": "completed",
        "run_date": today_str,
        "alerts_count": len(alerts_created),
        "closure_recommended": closure_recommended,
    }
