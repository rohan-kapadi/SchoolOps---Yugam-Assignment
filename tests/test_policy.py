"""Unit tests for deterministic policy engine and boundary conditions."""

import pytest

from agent_api.services.policy_engine import evaluate_weather_policy


@pytest.fixture
def baseline_safe_weather():
    return {
        "max_temp": 30.0,
        "rain_probability_max": 20,
        "rain_sum": 0.0,
    }


@pytest.fixture
def baseline_safe_aqi():
    return {
        "us_aqi": 100,
        "pm2_5": 25.0,
    }


# ==========================================
# Baseline Safe Tests
# ==========================================

def test_policy_all_safe(baseline_safe_weather, baseline_safe_aqi):
    result = evaluate_weather_policy(baseline_safe_weather, baseline_safe_aqi, route_rain=0.0)
    assert result["status"] == "SAFE"
    assert result["reasons"] == []
    assert result["closure_recommendation"] is False
    assert result["route_delay"] is False


# ==========================================
# Gate 1 Boundary Tests
# ==========================================

def test_aqi_boundary_200_safe_201_action(baseline_safe_weather):
    # AQI 200 does not trigger (> 200 required)
    res_200 = evaluate_weather_policy(baseline_safe_weather, {"us_aqi": 200})
    assert res_200["status"] == "SAFE"
    assert res_200["closure_recommendation"] is False

    # AQI 201 triggers ACTION_REQUIRED
    res_201 = evaluate_weather_policy(baseline_safe_weather, {"us_aqi": 201})
    assert res_201["status"] == "ACTION_REQUIRED"
    assert any("AQI 201" in r for r in res_201["reasons"])
    assert res_201["closure_recommendation"] is False


def test_temp_boundary_40_safe_40_1_action(baseline_safe_aqi):
    # Temp 40 does not trigger (> 40.0 required)
    w_40 = {"max_temp": 40.0, "rain_probability_max": 10, "rain_sum": 0.0}
    res_40 = evaluate_weather_policy(w_40, baseline_safe_aqi)
    assert res_40["status"] == "SAFE"

    # Temp 40.1 triggers ACTION_REQUIRED
    w_40_1 = {"max_temp": 40.1, "rain_probability_max": 10, "rain_sum": 0.0}
    res_40_1 = evaluate_weather_policy(w_40_1, baseline_safe_aqi)
    assert res_40_1["status"] == "ACTION_REQUIRED"
    assert any("40.1" in r for r in res_40_1["reasons"])


def test_rain_prob_boundary_59_safe_60_action(baseline_safe_weather, baseline_safe_aqi):
    # Rain prob 59 does not trigger (>= 60 required)
    w_59 = dict(baseline_safe_weather, rain_probability_max=59)
    res_59 = evaluate_weather_policy(w_59, baseline_safe_aqi)
    assert res_59["status"] == "SAFE"

    # Rain prob 60 triggers ACTION_REQUIRED
    w_60 = dict(baseline_safe_weather, rain_probability_max=60)
    res_60 = evaluate_weather_policy(w_60, baseline_safe_aqi)
    assert res_60["status"] == "ACTION_REQUIRED"
    assert any("60%" in r for r in res_60["reasons"])


def test_daily_rain_boundary_9_9_safe_10_action(baseline_safe_weather, baseline_safe_aqi):
    # Rain 9.9 does not trigger (>= 10.0 required)
    w_9_9 = dict(baseline_safe_weather, rain_sum=9.9)
    res_9_9 = evaluate_weather_policy(w_9_9, baseline_safe_aqi)
    assert res_9_9["status"] == "SAFE"

    # Rain 10.0 triggers ACTION_REQUIRED
    w_10 = dict(baseline_safe_weather, rain_sum=10.0)
    res_10 = evaluate_weather_policy(w_10, baseline_safe_aqi)
    assert res_10["status"] == "ACTION_REQUIRED"
    assert any("10.0 mm" in r for r in res_10["reasons"])


def test_route_rain_boundary_19_9_no_delay_20_delay(baseline_safe_weather, baseline_safe_aqi):
    # Route rain 19.9 does not trigger delay (>= 20.0 required)
    res_19_9 = evaluate_weather_policy(baseline_safe_weather, baseline_safe_aqi, route_rain=19.9)
    assert res_19_9["route_delay"] is False
    assert res_19_9["status"] == "SAFE"

    # Route rain 20.0 triggers delay
    res_20 = evaluate_weather_policy(baseline_safe_weather, baseline_safe_aqi, route_rain=20.0)
    assert res_20["route_delay"] is True
    assert res_20["status"] == "ACTION_REQUIRED"
    assert any("20.0 mm" in r for r in res_20["reasons"])

    # List of stops where one stop reaches 20 mm
    res_stops = evaluate_weather_policy(baseline_safe_weather, baseline_safe_aqi, route_rain=[5.0, 12.0, 20.5])
    assert res_stops["route_delay"] is True


def test_closure_recommendation_boundaries(baseline_safe_weather, baseline_safe_aqi):
    # AQI 300 does not recommend closure (> 300 required, though > 200 triggers action)
    res_300 = evaluate_weather_policy(baseline_safe_weather, {"us_aqi": 300})
    assert res_300["status"] == "ACTION_REQUIRED"
    assert res_300["closure_recommendation"] is False

    # AQI 301 recommends closure
    res_301 = evaluate_weather_policy(baseline_safe_weather, {"us_aqi": 301})
    assert res_301["status"] == "ACTION_REQUIRED"
    assert res_301["closure_recommendation"] is True

    # Rain 49.9 does not recommend closure (>= 50 required)
    w_49_9 = dict(baseline_safe_weather, rain_sum=49.9)
    res_49_9 = evaluate_weather_policy(w_49_9, baseline_safe_aqi)
    assert res_49_9["closure_recommendation"] is False

    # Rain 50.0 recommends closure
    w_50 = dict(baseline_safe_weather, rain_sum=50.0)
    res_50 = evaluate_weather_policy(w_50, baseline_safe_aqi)
    assert res_50["closure_recommendation"] is True

    # Gate assertion: AQI 301 and rain 50 -> closure recommendation
    res_both = evaluate_weather_policy(w_50, {"us_aqi": 301})
    assert res_both["status"] == "ACTION_REQUIRED"
    assert res_both["closure_recommendation"] is True


# ==========================================
# Incomplete Data / None Tests
# ==========================================

def test_missing_or_none_data_returns_incomplete_data(baseline_safe_weather, baseline_safe_aqi):
    # Weather is None
    res_no_weather = evaluate_weather_policy(None, baseline_safe_aqi)
    assert res_no_weather["status"] == "INCOMPLETE_DATA"

    # AQI is None
    res_no_aqi = evaluate_weather_policy(baseline_safe_weather, None)
    assert res_no_aqi["status"] == "INCOMPLETE_DATA"

    # Both None
    res_both_none = evaluate_weather_policy(None, None)
    assert res_both_none["status"] == "INCOMPLETE_DATA"

    # Missing specific fields
    w_incomplete = {"max_temp": 30.0}  # missing rain prob and rain sum
    res_partial = evaluate_weather_policy(w_incomplete, baseline_safe_aqi)
    assert res_partial["status"] == "INCOMPLETE_DATA"

    # Tool status 'data_unavailable'
    unavailable_tool = {"status": "data_unavailable", "reason": "Timeout"}
    res_unavail = evaluate_weather_policy(unavailable_tool, baseline_safe_aqi)
    assert res_unavail["status"] == "INCOMPLETE_DATA"


def test_tool_envelopes_parsing(baseline_safe_weather, baseline_safe_aqi):
    # Accepts tool response format {"status": "ok", "data": {...}}
    weather_tool_res = {"status": "ok", "data": baseline_safe_weather}
    aqi_tool_res = {"status": "ok", "data": baseline_safe_aqi}

    res = evaluate_weather_policy(weather_tool_res, aqi_tool_res)
    assert res["status"] == "SAFE"


def test_dynamic_rules_extension(baseline_safe_weather, baseline_safe_aqi):
    """Demonstrate live-interview extension without modifying policy_engine code."""
    custom_rules = {
        "aqi_outdoor_threshold": 200,
        "max_temp_threshold": 40.0,
        "rain_prob_threshold": 60,
        "daily_rain_threshold": 10.0,
        "aqi_closure_threshold": 300,
        "closure_rain_threshold": 50.0,
        "route_rain_threshold": 20.0,
        "dynamic_rules": [
            {
                "field": "wind_speed_max",
                "operator": ">",
                "threshold": 50.0,
                "reason": "Severe winds (> 50 km/h): halt outdoor activities",
            }
        ],
    }

    # Wind speed 45 (below threshold) -> SAFE
    weather_windy = dict(baseline_safe_weather, wind_speed_max=45.0)
    res1 = evaluate_weather_policy(weather_windy, baseline_safe_aqi, rules=custom_rules)
    assert res1["status"] == "SAFE"

    # Wind speed 55 (above threshold) -> ACTION_REQUIRED
    weather_gale = dict(baseline_safe_weather, wind_speed_max=55.0)
    res2 = evaluate_weather_policy(weather_gale, baseline_safe_aqi, rules=custom_rules)
    assert res2["status"] == "ACTION_REQUIRED"
    assert any("Severe winds" in r for r in res2["reasons"])

