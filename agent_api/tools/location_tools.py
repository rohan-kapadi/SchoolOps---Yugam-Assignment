"""Location tools for geocoding and India Post PIN lookups."""

from typing import Any
import httpx

from agent_api.config import (
    CACHE_TTL_LOCATION,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_SCHOOL_LAT,
    DEFAULT_SCHOOL_LON,
    INDIA_POST_PIN_URL,
    OPEN_METEO_GEOCODING_URL,
)
from agent_api.tools.cache import ttl_cache


@ttl_cache(ttl_seconds=CACHE_TTL_LOCATION)
def geocode_location(
    name: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Geocode a place or landmark name to coordinates using Open-Meteo Geocoding API."""
    query = name.strip() if name else ""
    if not query:
        return {"status": "data_unavailable", "reason": "Location name cannot be empty"}

    params = {"name": query, "count": 5, "language": "en", "format": "json"}

    try:
        if client is not None:
            resp = client.get(OPEN_METEO_GEOCODING_URL, params=params, timeout=DEFAULT_HTTP_TIMEOUT)
            return _parse_geocoding_response(resp, query)

        with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT) as default_client:
            resp = default_client.get(OPEN_METEO_GEOCODING_URL, params=params)
            return _parse_geocoding_response(resp, query)
    except httpx.TimeoutException as exc:
        return {"status": "data_unavailable", "reason": f"Geocoding request timed out: {exc}"}
    except httpx.HTTPError as exc:
        return {"status": "data_unavailable", "reason": f"Geocoding connection error: {exc}"}
    except Exception as exc:
        return {"status": "data_unavailable", "reason": f"Unexpected geocoding error: {exc}"}


def _parse_geocoding_response(resp: httpx.Response, query: str) -> dict[str, Any]:
    """Parse geocoding JSON results into standardized coordinates dict."""
    if resp.status_code != 200:
        return {"status": "data_unavailable", "reason": f"Geocoding API returned HTTP {resp.status_code}: {resp.text}"}

    payload = resp.json()
    results = payload.get("results") if isinstance(payload, dict) else None

    if not results:
        return {"status": "data_unavailable", "reason": f"No geocoding results found for '{query}'"}

    top = results[0]
    lat = top.get("latitude")
    lon = top.get("longitude")

    return {
        "status": "ok",
        "data": {
            "name": top.get("name", query),
            "lat": lat,
            "lon": lon,
            "latitude": lat,
            "longitude": lon,
            "admin1": top.get("admin1"),
            "country": top.get("country"),
        },
    }


@ttl_cache(ttl_seconds=CACHE_TTL_LOCATION)
def get_pin_details(
    pin: str | int,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Look up postal PIN details via India Post API."""
    pin_str = str(pin).strip()
    if not pin_str or not pin_str.isdigit() or len(pin_str) != 6:
        return {"status": "data_unavailable", "reason": f"Invalid Indian PIN code '{pin}'. Expected 6 digits."}

    url = f"{INDIA_POST_PIN_URL}/{pin_str}"

    try:
        if client is not None:
            resp = client.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
            return _parse_pin_response(resp, pin_str)

        with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT) as default_client:
            resp = default_client.get(url)
            return _parse_pin_response(resp, pin_str)
    except httpx.TimeoutException as exc:
        return {"status": "data_unavailable", "reason": f"PIN API request timed out: {exc}"}
    except httpx.HTTPError as exc:
        return {"status": "data_unavailable", "reason": f"PIN API connection error: {exc}"}
    except Exception as exc:
        return {"status": "data_unavailable", "reason": f"Unexpected PIN API error: {exc}"}


def _parse_pin_response(resp: httpx.Response, pin_str: str) -> dict[str, Any]:
    """Parse India Post PIN API response."""
    if resp.status_code != 200:
        return {"status": "data_unavailable", "reason": f"PIN API returned HTTP {resp.status_code}: {resp.text}"}

    payload = resp.json()
    if not isinstance(payload, list) or len(payload) == 0:
        return {"status": "data_unavailable", "reason": f"No records found for PIN '{pin_str}'"}

    item = payload[0]
    if item.get("Status") != "Success" or not item.get("PostOffice"):
        msg = item.get("Message", "No records found")
        return {"status": "data_unavailable", "reason": f"PIN '{pin_str}' lookup failed: {msg}"}

    offices = item.get("PostOffice", [])
    first = offices[0] if offices else {}

    return {
        "status": "ok",
        "data": {
            "pin": pin_str,
            "district": first.get("District"),
            "state": first.get("State"),
            "post_offices": [o.get("Name") for o in offices if o.get("Name")],
            "raw_offices": offices,
        },
    }


def resolve_event_coordinates(
    event_lat: float | None,
    event_lon: float | None,
    fallback_lat: float = DEFAULT_SCHOOL_LAT,
    fallback_lon: float = DEFAULT_SCHOOL_LON,
) -> tuple[float, float]:
    """Return event-specific coordinates if available, otherwise school coordinates."""
    if event_lat is not None and event_lon is not None:
        return event_lat, event_lon
    return fallback_lat, fallback_lon

