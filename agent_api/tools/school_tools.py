"""HTTP client wrappers for the read-only School API endpoints."""

from typing import Any
import httpx

from agent_api.config import DEFAULT_HTTP_TIMEOUT, SCHOOL_API_URL


def _school_request(
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Execute a GET request against the School API with standardized error handling."""
    url = f"{SCHOOL_API_URL}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    try:
        if client is not None:
            resp = client.get(url, params=clean_params, timeout=timeout)
            return _handle_response(resp)

        with httpx.Client(timeout=timeout) as internal_client:
            resp = internal_client.get(url, params=clean_params)
            return _handle_response(resp)
    except httpx.TimeoutException as exc:
        return {"status": "data_unavailable", "reason": f"School API request timed out: {exc}"}
    except httpx.HTTPError as exc:
        return {"status": "data_unavailable", "reason": f"School API connection error: {exc}"}
    except Exception as exc:
        return {"status": "data_unavailable", "reason": f"Unexpected error communicating with School API: {exc}"}


def _handle_response(resp: httpx.Response) -> dict[str, Any]:
    """Format HTTP response into standard {status, data/reason} schema."""
    if resp.status_code == 200:
        return {"status": "ok", "data": resp.json()}

    detail = resp.text
    try:
        data = resp.json()
        if isinstance(data, dict) and "detail" in data:
            detail = str(data["detail"])
    except Exception:
        pass

    return {
        "status": "data_unavailable",
        "reason": f"School API error ({resp.status_code}): {detail}",
    }


def get_school_profile(client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch school profile, including base coordinates and timings."""
    return _school_request("/school", client=client)


def get_students(
    name: str | None = None,
    class_name: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Search students by name (case-insensitive, all matches) and/or class."""
    params = {}
    if name is not None:
        params["name"] = name
    if class_name is not None:
        params["class"] = class_name
    return _school_request("/school/students", params=params, client=client)


def find_student(
    name: str | None = None,
    class_name: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Convenience alias for searching students."""
    return get_students(name=name, class_name=class_name, client=client)


def get_student(student_id: str, client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch a single student by ID."""
    return _school_request(f"/school/students/{student_id}", client=client)


def get_events(client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch all school events."""
    return _school_request("/school/events", client=client)


def get_routes(client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch all bus routes."""
    return _school_request("/school/routes", client=client)


def get_route(route_id: str, client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch details for a specific bus route."""
    return _school_request(f"/school/routes/{route_id}", client=client)


def get_attendance(
    student_id: str | None = None,
    class_name: str | None = None,
    date: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch attendance records with optional filtering."""
    params = {}
    if student_id is not None:
        params["student_id"] = student_id
    if class_name is not None:
        params["class"] = class_name
    if date is not None:
        params["date"] = date
    return _school_request("/school/attendance", params=params, client=client)


def get_policy(client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch official school policy document text."""
    return _school_request("/school/policy", client=client)

