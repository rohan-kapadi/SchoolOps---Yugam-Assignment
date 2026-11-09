"""Unit tests for tool layer (School API tools, weather tools, location tools, and TTL cache).

All tests use mocked network responses (no real external network calls).
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import httpx
import pytest

from agent_api.tools.cache import TTLCache, default_cache
from agent_api.tools.location_tools import (
    geocode_location,
    get_pin_details,
    resolve_event_coordinates,
)
from agent_api.tools.school_tools import (
    find_student,
    get_attendance,
    get_events,
    get_policy,
    get_route,
    get_routes,
    get_school_profile,
    get_student,
    get_students,
)
from agent_api.tools.weather_tools import get_air_quality, get_forecast


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all tool caches before and after each test."""
    default_cache.clear()
    get_forecast.clear_cache()
    get_air_quality.clear_cache()
    geocode_location.clear_cache()
    get_pin_details.clear_cache()
    yield
    default_cache.clear()
    get_forecast.clear_cache()
    get_air_quality.clear_cache()
    geocode_location.clear_cache()
    get_pin_details.clear_cache()


# ==========================================
# TTL Cache Tests
# ==========================================

def test_ttl_cache_basic_and_expiration():
    cache = TTLCache()
    cache.set("key1", "val1", ttl_seconds=0.05)
    assert cache.get("key1") == "val1"

    # Expire entry
    import time
    time.sleep(0.06)
    assert cache.get("key1") is None


def test_ttl_cache_clear_and_delete():
    cache = TTLCache()
    cache.set("k1", "v1", ttl_seconds=100)
    cache.set("k2", "v2", ttl_seconds=100)
    assert len(cache) == 2

    cache.delete("k1")
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"

    cache.clear()
    assert len(cache) == 0


# ==========================================
# School API Tools Tests
# ==========================================

@patch("httpx.Client.get")
def test_school_tools_get_students_success(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json=[
            {"id": "S004", "name": "Riya Sharma", "class": "6A"},
            {"id": "S061", "name": "Riya Sharma", "class": "7A"},
        ],
        request=httpx.Request("GET", "http://test"),
    )

    result = get_students(name="Riya Sharma")
    assert result["status"] == "ok"
    assert len(result["data"]) == 2
    assert result["data"][0]["id"] == "S004"

    # Also test find_student alias
    alias_result = find_student(name="Riya Sharma")
    assert alias_result["status"] == "ok"


@patch("httpx.Client.get")
def test_school_tools_get_student_not_found(mock_get):
    mock_get.return_value = httpx.Response(
        404,
        json={"detail": "Student 'S999' not found"},
        request=httpx.Request("GET", "http://test"),
    )

    result = get_student("S999")
    assert result["status"] == "data_unavailable"
    assert "not found" in result["reason"].lower()


@patch("httpx.Client.get")
def test_school_tools_timeout_handling(mock_get):
    mock_get.side_effect = httpx.TimeoutException("Connection timed out")

    result = get_events()
    assert result["status"] == "data_unavailable"
    assert "timed out" in result["reason"].lower()


@patch("httpx.Client.get")
def test_school_tools_all_endpoints(mock_get):
    # Test routes
    mock_get.return_value = httpx.Response(
        200,
        json=[{"id": "R1", "name": "Route 1"}],
        request=httpx.Request("GET", "http://test"),
    )
    routes_res = get_routes()
    assert routes_res["status"] == "ok"

    route_res = get_route("R1")
    assert route_res["status"] == "ok"

    # Test school profile
    profile_res = get_school_profile()
    assert profile_res["status"] == "ok"

    # Test attendance
    att_res = get_attendance(date="2026-11-09")
    assert att_res["status"] == "ok"

    # Test policy
    mock_get.return_value = httpx.Response(
        200,
        json={"policy": "School Policy Document"},
        request=httpx.Request("GET", "http://test"),
    )
    pol_res = get_policy()
    assert pol_res["status"] == "ok"
    assert "policy" in pol_res["data"]


# ==========================================
# Weather Tools Tests
# ==========================================

@patch("httpx.Client.get")
def test_get_forecast_success_parsing(mock_get):
    date_str = "2026-11-10"
    mock_get.return_value = httpx.Response(
        200,
        json={
            "daily": {
                "time": [date_str],
                "temperature_2m_max": [32.5],
                "precipitation_probability_max": [45.0],
                "precipitation_sum": [5.2],
            },
            "hourly": {
                "time": [f"{date_str}T08:00", f"{date_str}T09:00"],
                "precipitation": [1.2, 2.0],
                "precipitation_probability": [40, 50],
            },
        },
        request=httpx.Request("GET", "http://test"),
    )

    result = get_forecast(26.9124, 75.7873, date_str)
    assert result["status"] == "ok"
    data = result["data"]
    assert data["date"] == date_str
    assert data["max_temp"] == 32.5
    assert data["temperature_2m_max"] == 32.5
    assert data["rain_probability_max"] == 45.0
    assert data["rain_sum"] == 5.2
    assert len(data["hourly_rain"]) == 2
    assert data["hourly_rain"][0]["precipitation"] == 1.2


@patch("httpx.Client.get")
def test_get_forecast_timeout_returns_data_unavailable(mock_get):
    mock_get.side_effect = httpx.TimeoutException("Read timeout")

    result = get_forecast(26.9124, 75.7873, "2026-11-10")
    assert result["status"] == "data_unavailable"
    assert "timed out" in result["reason"].lower()


@patch("httpx.Client.get")
def test_get_forecast_cache_hits_on_second_call(mock_get):
    date_str = "2026-11-10"
    mock_get.return_value = httpx.Response(
        200,
        json={
            "daily": {
                "time": [date_str],
                "temperature_2m_max": [29.0],
                "precipitation_probability_max": [10],
                "precipitation_sum": [0.0],
            },
            "hourly": {"time": [], "precipitation": [], "precipitation_probability": []},
        },
        request=httpx.Request("GET", "http://test"),
    )

    # First call - should trigger HTTP request
    res1 = get_forecast(26.9124, 75.7873, date_str)
    assert res1["status"] == "ok"
    assert mock_get.call_count == 1

    # Second call within TTL with same parameters - must hit cache, no extra HTTP call
    res2 = get_forecast(26.9124, 75.7873, date_str)
    assert res2["status"] == "ok"
    assert res2 == res1
    assert mock_get.call_count == 1


@patch("httpx.Client.get")
def test_get_air_quality_success_parsing(mock_get):
    target_date = (date.today() + timedelta(days=2)).isoformat()
    mock_get.return_value = httpx.Response(
        200,
        json={
            "hourly": {
                "time": [f"{target_date}T08:00", f"{target_date}T09:00"],
                "us_aqi": [185, 210],
                "pm2_5": [45.2, 60.1],
            }
        },
        request=httpx.Request("GET", "http://test"),
    )

    result = get_air_quality(26.9124, 75.7873, target_date)
    assert result["status"] == "ok"
    data = result["data"]
    assert data["date"] == target_date
    assert data["us_aqi"] == 210  # peak AQI
    assert data["pm2_5"] == 60.1  # peak PM2.5


def test_get_air_quality_beyond_range_returns_data_unavailable():
    # Date 12 days in the future (> 7 days)
    far_future = (date.today() + timedelta(days=12)).isoformat()
    result = get_air_quality(26.9124, 75.7873, far_future)

    assert result["status"] == "data_unavailable"
    assert "beyond 7 days" in result["reason"].lower()


@patch("httpx.Client.get")
def test_get_air_quality_timeout_returns_data_unavailable(mock_get):
    target_date = (date.today() + timedelta(days=1)).isoformat()
    mock_get.side_effect = httpx.TimeoutException("Air quality API timeout")

    result = get_air_quality(26.9124, 75.7873, target_date)
    assert result["status"] == "data_unavailable"
    assert "timed out" in result["reason"].lower()


@patch("httpx.Client.get")
def test_get_air_quality_cache_hits_on_second_call(mock_get):
    target_date = (date.today() + timedelta(days=1)).isoformat()
    mock_get.return_value = httpx.Response(
        200,
        json={
            "hourly": {
                "time": [f"{target_date}T10:00"],
                "us_aqi": [150],
                "pm2_5": [35.0],
            }
        },
        request=httpx.Request("GET", "http://test"),
    )

    res1 = get_air_quality(26.9124, 75.7873, target_date)
    assert res1["status"] == "ok"
    assert mock_get.call_count == 1

    res2 = get_air_quality(26.9124, 75.7873, target_date)
    assert res2["status"] == "ok"
    assert res2 == res1
    assert mock_get.call_count == 1


def test_event_specific_coordinates_resolution():
    # Amber Fort event coordinates
    amber_lat, amber_lon = 26.9855, 75.8513
    coords = resolve_event_coordinates(amber_lat, amber_lon)
    assert coords == (26.9855, 75.8513)

    # Event without coords should fallback to school coords
    coords_default = resolve_event_coordinates(None, None)
    assert coords_default == (26.9124, 75.7873)


# ==========================================
# Location Tools Tests
# ==========================================

@patch("httpx.Client.get")
def test_geocode_location_success(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json={
            "results": [
                {
                    "name": "Amber Fort",
                    "latitude": 26.9855,
                    "longitude": 75.8513,
                    "admin1": "Rajasthan",
                    "country": "India",
                }
            ]
        },
        request=httpx.Request("GET", "http://test"),
    )

    result = geocode_location("Amber Fort")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["name"] == "Amber Fort"
    assert data["lat"] == 26.9855
    assert data["lon"] == 75.8513


@patch("httpx.Client.get")
def test_geocode_location_not_found(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json={"results": []},
        request=httpx.Request("GET", "http://test"),
    )

    result = geocode_location("Unknown Place 12345")
    assert result["status"] == "data_unavailable"
    assert "no geocoding results" in result["reason"].lower()


@patch("httpx.Client.get")
def test_geocode_location_cache_hits(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json={"results": [{"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873}]},
        request=httpx.Request("GET", "http://test"),
    )

    res1 = geocode_location("Jaipur")
    assert res1["status"] == "ok"
    assert mock_get.call_count == 1

    res2 = geocode_location("Jaipur")
    assert res2["status"] == "ok"
    assert mock_get.call_count == 1


@patch("httpx.Client.get")
def test_get_pin_details_success(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json=[
            {
                "Status": "Success",
                "Message": "Number of pincode found: 1",
                "PostOffice": [
                    {
                        "Name": "Mansarovar",
                        "District": "Jaipur",
                        "State": "Rajasthan",
                        "Pincode": "302020",
                    }
                ],
            }
        ],
        request=httpx.Request("GET", "http://test"),
    )

    result = get_pin_details("302020")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["pin"] == "302020"
    assert data["district"] == "Jaipur"
    assert "Mansarovar" in data["post_offices"]


def test_get_pin_details_invalid_format():
    result = get_pin_details("invalid_pin")
    assert result["status"] == "data_unavailable"
    assert "invalid indian pin" in result["reason"].lower()


@patch("httpx.Client.get")
def test_get_pin_details_cache_hits(mock_get):
    mock_get.return_value = httpx.Response(
        200,
        json=[
            {
                "Status": "Success",
                "Message": "1 found",
                "PostOffice": [{"Name": "Jaipur GPO", "District": "Jaipur", "State": "Rajasthan"}],
            }
        ],
        request=httpx.Request("GET", "http://test"),
    )

    res1 = get_pin_details("302001")
    assert res1["status"] == "ok"
    assert mock_get.call_count == 1

    res2 = get_pin_details("302001")
    assert res2["status"] == "ok"
    assert mock_get.call_count == 1
