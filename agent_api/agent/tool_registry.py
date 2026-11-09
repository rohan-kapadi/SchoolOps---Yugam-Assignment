"""Tool definitions, registration, and dispatch for LLM agent function calling."""

from typing import Any, Callable
from google.genai import types

from agent_api.services.attendance_service import fetch_and_evaluate_absences
from agent_api.services.policy_engine import evaluate_weather_policy as run_weather_policy
from agent_api.tools.location_tools import geocode_location as run_geocode, get_pin_details as run_pin
from agent_api.tools.school_tools import (
    get_attendance as run_get_attendance,
    get_events as run_get_events,
    get_policy as run_get_policy,
    get_route as run_get_route,
    get_student as run_get_student,
    get_students as run_get_students,
)
from agent_api.tools.weather_tools import (
    get_air_quality as run_get_air_quality,
    get_forecast as run_get_forecast,
)


# ==========================================
# Tool Implementations
# ==========================================

def tool_get_events() -> dict[str, Any]:
    """Fetch all upcoming school events."""
    res = run_get_events()
    if res.get("status") == "ok":
        return {
            "status": "ok",
            "untrusted_data": res.get("data", []),
            "source": "School API: /school/events",
        }
    return res


def tool_find_student(
    name: str | None = None,
    class_name: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    """Search for students by name, class, or student ID."""
    if student_id:
        res = run_get_student(student_id)
        if res.get("status") == "ok":
            s = res.get("data", {})
            sanitized = {
                "id": s.get("id"),
                "name": s.get("name"),
                "class": s.get("class") or s.get("class_name"),
                "bus_route_id": s.get("busRouteId") or s.get("bus_route_id"),
                "bus_stop": s.get("busStop") or s.get("bus_stop"),
                "home_area": s.get("homeArea") or s.get("home_area"),
            }
            return {
                "status": "ok",
                "untrusted_data": [sanitized],
                "count": 1,
                "is_ambiguous": False,
                "source": f"School API: /school/students/{student_id}",
            }
        return res

    res = run_get_students(name=name, class_name=class_name)
    if res.get("status") == "ok":
        raw_list = res.get("data", [])
        sanitized_list = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "class": s.get("class") or s.get("class_name"),
                "bus_route_id": s.get("busRouteId") or s.get("bus_route_id"),
                "bus_stop": s.get("busStop") or s.get("bus_stop"),
                "home_area": s.get("homeArea") or s.get("home_area"),
            }
            for s in raw_list
        ]
        is_ambiguous = len(sanitized_list) > 1
        return {
            "status": "ok",
            "untrusted_data": sanitized_list,
            "count": len(sanitized_list),
            "is_ambiguous": is_ambiguous,
            "source": "School API: /school/students",
        }
    return res


def tool_get_route(route_id: str) -> dict[str, Any]:
    """Fetch bus route details and stop stops."""
    res = run_get_route(route_id)
    if res.get("status") == "ok":
        return {
            "status": "ok",
            "untrusted_data": res.get("data"),
            "source": f"School API: /school/routes/{route_id}",
        }
    return res


def tool_get_attendance(
    student_id: str | None = None,
    class_name: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Fetch school attendance records."""
    res = run_get_attendance(student_id=student_id, class_name=class_name, date=date)
    if res.get("status") == "ok":
        return {
            "status": "ok",
            "untrusted_data": res.get("data"),
            "source": "School API: /school/attendance",
        }
    return res


def tool_get_policy() -> dict[str, Any]:
    """Fetch the official written school policy text."""
    res = run_get_policy()
    if res.get("status") == "ok":
        return {
            "status": "ok",
            "untrusted_data": res.get("data", {}).get("policy", ""),
            "source": "School Policy Document",
        }
    return res


def tool_get_forecast(lat: float, lon: float, date: str) -> dict[str, Any]:
    """Fetch weather forecast for a latitude, longitude, and date."""
    res = run_get_forecast(lat=lat, lon=lon, date=date)
    if res.get("status") == "ok":
        res["source"] = "Open-Meteo Forecast API"
    return res


def tool_get_air_quality(lat: float, lon: float, date: str) -> dict[str, Any]:
    """Fetch air quality forecast (US AQI and PM2.5) for a location and date."""
    res = run_get_air_quality(lat=lat, lon=lon, date=date)
    if res.get("status") == "ok":
        res["source"] = "Open-Meteo Air Quality API"
    return res


def tool_geocode_location(name: str) -> dict[str, Any]:
    """Geocode a place or landmark name to geographic coordinates."""
    res = run_geocode(name=name)
    if res.get("status") == "ok":
        res["source"] = "Open-Meteo Geocoding API"
    return res


def tool_get_pin_details(pin: str) -> dict[str, Any]:
    """Lookup Indian postal PIN code information."""
    res = run_pin(pin=pin)
    if res.get("status") == "ok":
        res["source"] = "India Post PIN API"
    return res


def tool_evaluate_weather_policy(
    weather: dict[str, Any] | None = None,
    air_quality: dict[str, Any] | None = None,
    route_rain: float | None = None,
) -> dict[str, Any]:
    """Evaluate weather and air quality against school policy rules."""
    res = run_weather_policy(weather=weather, air_quality=air_quality, route_rain=route_rain)
    res["source"] = "School Environmental Safety Policy Engine"
    return res


def tool_get_consecutive_absences(min_streak: int = 3) -> dict[str, Any]:
    """Calculate students with consecutive school-day absences (3 or more days)."""
    res = fetch_and_evaluate_absences(min_streak=min_streak)
    if res.get("status") == "ok":
        return {
            "status": "ok",
            "untrusted_data": res.get("data", []),
            "count": len(res.get("data", [])),
            "source": "School Attendance Analysis Service",
        }
    return res


# Tool Dispatch Map
TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "get_events": tool_get_events,
    "find_student": tool_find_student,
    "get_route": tool_get_route,
    "get_attendance": tool_get_attendance,
    "get_policy": tool_get_policy,
    "get_forecast": tool_get_forecast,
    "get_air_quality": tool_get_air_quality,
    "geocode_location": tool_geocode_location,
    "get_pin_details": tool_get_pin_details,
    "evaluate_weather_policy": tool_evaluate_weather_policy,
    "get_consecutive_absences": tool_get_consecutive_absences,
}


# ==========================================
# Google GenAI Function Declarations
# ==========================================

FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_events",
        description="Fetch all upcoming school events, schedules, locations, and attendance classes.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="find_student",
        description="Search for students by full name, class (e.g. '6A', '7A', '7B' to see students or class size count), or student ID (e.g. 'S004').",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "name": types.Schema(type="STRING", description="Student full or partial name (e.g. 'Riya Sharma')"),
                "class_name": types.Schema(type="STRING", description="Class name to list or count students (e.g. '6A', '7A', '7B')"),
                "student_id": types.Schema(type="STRING", description="Student ID (e.g. 'S004')"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_route",
        description="Fetch details for a specific bus route by ID (e.g. 'R1', 'R2', 'R3', 'R4').",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "route_id": types.Schema(type="STRING", description="Bus route ID (e.g. 'R1')"),
            },
            required=["route_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_attendance",
        description="Fetch raw attendance records with optional filters for student ID, class, or date.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "student_id": types.Schema(type="STRING", description="Student ID to filter"),
                "class_name": types.Schema(type="STRING", description="Class name to filter (e.g. '6A')"),
                "date": types.Schema(type="STRING", description="Date in YYYY-MM-DD format"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_policy",
        description="Fetch the official written school policy text regarding weather, attendance, and safety.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="get_forecast",
        description="Fetch weather forecast (max temp, precipitation probability, daily rain) for coordinates and date.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "lat": types.Schema(type="NUMBER", description="Latitude coordinate"),
                "lon": types.Schema(type="NUMBER", description="Longitude coordinate"),
                "date": types.Schema(type="STRING", description="Target forecast date (YYYY-MM-DD)"),
            },
            required=["lat", "lon", "date"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_air_quality",
        description="Fetch air quality forecast (US AQI and PM2.5) for coordinates and date (up to 7 days ahead).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "lat": types.Schema(type="NUMBER", description="Latitude coordinate"),
                "lon": types.Schema(type="NUMBER", description="Longitude coordinate"),
                "date": types.Schema(type="STRING", description="Target date (YYYY-MM-DD)"),
            },
            required=["lat", "lon", "date"],
        ),
    ),
    types.FunctionDeclaration(
        name="geocode_location",
        description="Geocode a location or landmark name into coordinates (e.g. 'Amber Fort, Jaipur').",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "name": types.Schema(type="STRING", description="Place name or landmark to search"),
            },
            required=["name"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_pin_details",
        description="Lookup Indian postal PIN code details (district, state, post offices).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "pin": types.Schema(type="STRING", description="6-digit Indian PIN code"),
            },
            required=["pin"],
        ),
    ),
    types.FunctionDeclaration(
        name="evaluate_weather_policy",
        description="Deterministically evaluate weather and AQI metrics against school policy thresholds.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "weather": types.Schema(type="OBJECT", description="Weather forecast data dictionary"),
                "air_quality": types.Schema(type="OBJECT", description="Air quality data dictionary"),
                "route_rain": types.Schema(type="NUMBER", description="Maximum rainfall at route stops in mm"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_consecutive_absences",
        description="Compute students with consecutive recorded school-day absences (default 3 or more days).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "min_streak": types.Schema(type="INTEGER", description="Minimum consecutive absences (default 3)"),
            },
        ),
    ),
]

GENAI_TOOL_DEFINITION = types.Tool(function_declarations=FUNCTION_DECLARATIONS)
