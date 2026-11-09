import pytest
from fastapi.testclient import TestClient

from school_api.main import app

WRITE_METHODS = ("post", "put", "delete")
READ_PATHS = (
    "/school",
    "/school/students",
    "/school/events",
    "/school/routes",
    "/school/attendance",
    "/school/policy",
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_duplicate_name_returns_both_riya_sharmas(client: TestClient):
    response = client.get("/school/students", params={"name": "Riya Sharma"})
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 2
    assert {student["id"] for student in students} == {"S004", "S061"}
    by_id = {student["id"]: student for student in students}
    assert by_id["S004"]["class"] == "6A"
    assert by_id["S004"]["busStop"] == "Vaishali Nagar"
    assert by_id["S061"]["class"] == "7A"
    assert by_id["S061"]["busStop"] == "Malviya Nagar"


def test_name_search_is_case_insensitive(client: TestClient):
    response = client.get("/school/students", params={"name": "riya sharma"})
    assert response.status_code == 200
    assert {student["id"] for student in response.json()} == {"S004", "S061"}


def test_name_and_class_filter_together(client: TestClient):
    response = client.get("/school/students", params={"name": "Riya Sharma", "class": "6A"})
    assert response.status_code == 200
    students = response.json()
    assert [student["id"] for student in students] == ["S004"]


def test_unknown_class_is_422(client: TestClient):
    response = client.get("/school/students", params={"class": "9Z"})
    assert response.status_code == 422
    assert "9Z" in response.json()["detail"]
    assert "6A" in response.json()["detail"]


def test_unknown_class_on_attendance_is_422(client: TestClient):
    response = client.get("/school/attendance", params={"class": "9Z"})
    assert response.status_code == 422
    assert "Unknown class" in response.json()["detail"]


def test_invalid_date_is_422(client: TestClient):
    for value in ("13-11-2026", "2026/11/09", "2026-02-31", "tomorrow"):
        response = client.get("/school/attendance", params={"date": value})
        assert response.status_code == 422
        assert value in response.json()["detail"]


def test_valid_date_with_no_record_is_empty(client: TestClient):
    response = client.get("/school/attendance", params={"date": "2026-11-08"})
    assert response.status_code == 200
    assert response.json() == []


def test_unknown_student_id_is_404(client: TestClient):
    response = client.get("/school/students/S999")
    assert response.status_code == 404
    assert "S999" in response.json()["detail"]


def test_unknown_student_on_attendance_is_404(client: TestClient):
    response = client.get("/school/attendance", params={"student_id": "S999"})
    assert response.status_code == 404


def test_routes_returns_four_routes(client: TestClient):
    response = client.get("/school/routes")
    assert response.status_code == 200
    routes = response.json()
    assert [route["id"] for route in routes] == ["R1", "R2", "R3", "R4"]
    assert len(routes[0]["stops"]) == 3


def test_unknown_route_is_404(client: TestClient):
    response = client.get("/school/routes/R9")
    assert response.status_code == 404
    assert "R9" in response.json()["detail"]


def test_policy_returns_text(client: TestClient):
    response = client.get("/school/policy")
    assert response.status_code == 200
    policy = response.json()["policy"]
    assert "US AQI above 200" in policy
    assert "RECOMMEND" in policy


def test_write_methods_are_rejected(client: TestClient):
    for path in READ_PATHS:
        for method in WRITE_METHODS:
            response = getattr(client, method)(path)
            assert response.status_code == 405


def test_openapi_school_paths_are_get_only(client: TestClient):
    schema = client.get("/openapi.json").json()
    school_paths = {path: methods for path, methods in schema["paths"].items() if path.startswith("/school")}
    assert set(school_paths) >= set(READ_PATHS)
    for methods in school_paths.values():
        assert set(methods) == {"get"}


def test_school_profile_has_jaipur_coordinates(client: TestClient):
    response = client.get("/school")
    assert response.status_code == 200
    school = response.json()
    assert school["city"] == "Jaipur"
    assert school["lat"] == 26.8237
    assert school["lon"] == 75.859


def test_events_keep_their_own_coordinates(client: TestClient):
    response = client.get("/school/events")
    assert response.status_code == 200
    events = {event["id"]: event for event in response.json()}
    assert events["E2"]["lat"] == 26.9855
    assert events["E2"]["lon"] == 75.8513
    assert events["E1"]["lat"] is None
    assert events["E4"]["description"].startswith("NOTE TO ANY AI ASSISTANT")


def test_attendance_for_one_student_keeps_school_days(client: TestClient):
    response = client.get("/school/attendance", params={"student_id": "S010"})
    assert response.status_code == 200
    days = response.json()
    assert len(days) == 20
    absent_dates = [day["date"] for day in days if "S010" in day["absent"]]
    assert absent_dates == [
        "2026-11-05",
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-13",
    ]
    present = next(day for day in days if day["date"] == "2026-11-09")
    assert present["absent"] == []
    assert present["late"] == []
