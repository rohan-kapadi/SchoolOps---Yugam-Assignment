"""Deterministic policy engine for weather and environmental safety rules.

Implements all written school policy rules without using any LLM or heuristic.
Thresholds are sourced from agent_api.config.POLICY_RULES.
"""

from typing import Any

from agent_api.config import POLICY_RULES


def evaluate_weather_policy(
    weather: dict[str, Any] | None,
    air_quality: dict[str, Any] | None,
    route_rain: float | int | list[float | int] | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate weather and air quality metrics against school safety policies.

    Parameters:
        weather: Dict containing forecast data (or tool response with 'data').
        air_quality: Dict containing AQI metrics (or tool response with 'data').
        route_rain: Rainfall measurement at route stops (scalar or list of stops).
        rules: Optional override for policy rules (defaults to config.POLICY_RULES).

    Returns:
        dict with:
            - status: 'SAFE' | 'ACTION_REQUIRED' | 'INCOMPLETE_DATA'
            - reasons: list of human-readable trigger explanations
            - closure_recommendation: bool (recommendation only, never an announcement)
            - route_delay: bool (whether route delays are expected)
    """
    active_rules = rules or POLICY_RULES
    reasons: list[str] = []
    closure_recommendation = False
    route_delay = False
    is_incomplete = False

    # Unwrap tool envelope {status: ok, data: ...} if present
    w_data: dict[str, Any] | None = None
    if isinstance(weather, dict):
        if weather.get("status") == "ok":
            w_data = weather.get("data")
        elif weather.get("status") == "data_unavailable":
            w_data = None
        else:
            w_data = weather

    aq_data: dict[str, Any] | None = None
    if isinstance(air_quality, dict):
        if air_quality.get("status") == "ok":
            aq_data = air_quality.get("data")
        elif air_quality.get("status") == "data_unavailable":
            aq_data = None
        else:
            aq_data = air_quality

    # Extract weather metrics
    max_temp = None
    rain_prob = None
    rain_sum = None
    if isinstance(w_data, dict):
        max_temp = w_data.get("max_temp") if "max_temp" in w_data else w_data.get("temperature_2m_max")
        rain_prob = (
            w_data.get("rain_probability_max")
            if "rain_probability_max" in w_data
            else w_data.get("precipitation_probability_max")
        )
        rain_sum = w_data.get("rain_sum") if "rain_sum" in w_data else w_data.get("precipitation_sum")

    # Extract air quality metrics
    us_aqi = None
    if isinstance(aq_data, dict):
        us_aqi = aq_data.get("us_aqi") if "us_aqi" in aq_data else aq_data.get("aqi")

    # Missing measurements must never be treated as SAFE
    if (
        w_data is None
        or aq_data is None
        or max_temp is None
        or rain_prob is None
        or rain_sum is None
        or us_aqi is None
    ):
        is_incomplete = True

    # 1. AQI outdoor threshold (> 200)
    aqi_outdoor_thresh = active_rules.get("aqi_outdoor_threshold", 200)
    if us_aqi is not None and us_aqi > aqi_outdoor_thresh:
        reasons.append(
            f"Air quality index (AQI {us_aqi}) exceeds outdoor threshold ({aqi_outdoor_thresh}): "
            "move outdoor activity indoors / postpone"
        )

    # 2. Max temperature heat threshold (> 40 °C)
    temp_thresh = active_rules.get("max_temp_threshold", 40.0)
    if max_temp is not None and max_temp > temp_thresh:
        reasons.append(
            f"Maximum temperature ({max_temp}°C) exceeds heat threshold ({temp_thresh}°C): "
            "move outdoor activity indoors / postpone"
        )

    # 3. Rain probability threshold (>= 60%)
    prob_thresh = active_rules.get("rain_prob_threshold", 60)
    if rain_prob is not None and rain_prob >= prob_thresh:
        reasons.append(
            f"Rain probability ({rain_prob}%) meets or exceeds threshold ({prob_thresh}%): "
            "move outdoor activity indoors / postpone"
        )

    # 4. Daily precipitation threshold (>= 10 mm)
    rain_thresh = active_rules.get("daily_rain_threshold", 10.0)
    if rain_sum is not None and rain_sum >= rain_thresh:
        reasons.append(
            f"Daily rainfall ({rain_sum} mm) meets or exceeds threshold ({rain_thresh} mm): "
            "move outdoor activity indoors / postpone"
        )

    # 5. AQI severe closure recommendation (> 300)
    aqi_closure_thresh = active_rules.get("aqi_closure_threshold", 300)
    if us_aqi is not None and us_aqi > aqi_closure_thresh:
        closure_recommendation = True
        reasons.append(
            f"Air quality index (AQI {us_aqi}) exceeds critical threshold ({aqi_closure_thresh}): "
            "recommend principal consider closure or online classes"
        )

    # 6. Daily rain emergency closure recommendation (>= 50 mm)
    closure_rain_thresh = active_rules.get("closure_rain_threshold", 50.0)
    if rain_sum is not None and rain_sum >= closure_rain_thresh:
        closure_recommendation = True
        reasons.append(
            f"Daily rainfall ({rain_sum} mm) meets or exceeds emergency threshold ({closure_rain_thresh} mm): "
            "recommend principal consider closure"
        )

    # 7. Route stop rainfall delay (>= 20 mm)
    route_rain_thresh = active_rules.get("route_rain_threshold", 20.0)
    if route_rain is not None:
        if isinstance(route_rain, (list, tuple)):
            max_route_rain = max(route_rain) if route_rain else 0.0
        else:
            max_route_rain = float(route_rain)

        if max_route_rain >= route_rain_thresh:
            route_delay = True
            reasons.append(
                f"Bus route rainfall ({max_route_rain} mm) meets or exceeds delay threshold ({route_rain_thresh} mm): "
                "prepare route-delay notification"
            )

    # 8. Dynamic pluggable rules (e.g. for interview extension such as wind speed)
    for dyn_rule in active_rules.get("dynamic_rules", []):
        field = dyn_rule.get("field")
        op = dyn_rule.get("operator", ">=")
        thresh = dyn_rule.get("threshold")
        val = None
        if isinstance(w_data, dict) and field in w_data:
            val = w_data[field]
        elif isinstance(aq_data, dict) and field in aq_data:
            val = aq_data[field]

        if val is not None and thresh is not None:
            triggered = False
            if op == ">" and val > thresh:
                triggered = True
            elif op == ">=" and val >= thresh:
                triggered = True
            elif op == "<" and val < thresh:
                triggered = True
            elif op == "<=" and val <= thresh:
                triggered = True
            elif op == "==" and val == thresh:
                triggered = True

            if triggered:
                msg = dyn_rule.get("reason", f"{field} ({val}) triggered rule {op} {thresh}")
                reasons.append(msg)
                if dyn_rule.get("closure_recommendation"):
                    closure_recommendation = True
                if dyn_rule.get("route_delay"):
                    route_delay = True

    # Determine status
    if is_incomplete:
        status = "INCOMPLETE_DATA"
    elif reasons:
        status = "ACTION_REQUIRED"
    else:
        status = "SAFE"

    return {
        "status": status,
        "reasons": reasons,
        "closure_recommendation": closure_recommendation,
        "route_delay": route_delay,
    }
