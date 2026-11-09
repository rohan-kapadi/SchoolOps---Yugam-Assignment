"""Unit tests for attendance service and consecutive absence streak calculations."""

from fastapi.testclient import TestClient
import pytest

from agent_api.services.attendance_service import (
    consecutive_absences,
    get_consecutive_absent_students,
)
from school_api.main import app


# ==========================================
# Unit Tests with Synthetic Data
# ==========================================

def test_consecutive_absences_counts_sequential_days():
    records = [
        {"date": "2026-11-02", "absent": ["S1", "S2"], "late": []},
        {"date": "2026-11-03", "absent": ["S1"], "late": ["S2"]},
        {"date": "2026-11-04", "absent": ["S1"], "late": []},
        {"date": "2026-11-05", "absent": ["S1"], "late": []},
    ]

    # S1 was absent 4 consecutive days (>= 3)
    # S2 was absent only 1 day before being late
    res = consecutive_absences(records, min_streak=3)
    assert res == {"S1": 4}


def test_consecutive_absences_skips_weekends_naturally():
    # Friday 2026-11-06 then Monday 2026-11-09 (Sunday 2026-11-08 is absent from data)
    records = [
        {"date": "2026-11-05", "absent": ["S10"], "late": []},
        {"date": "2026-11-06", "absent": ["S10"], "late": []},  # Friday
        {"date": "2026-11-09", "absent": ["S10"], "late": []},  # Monday
    ]

    res = consecutive_absences(records, min_streak=3)
    assert res == {"S10": 3}


def test_presence_or_late_resets_streak():
    records = [
        {"date": "2026-11-02", "absent": ["S1"], "late": []},
        {"date": "2026-11-03", "absent": ["S1"], "late": []},
        {"date": "2026-11-04", "absent": [], "late": ["S1"]},  # Late, not absent
        {"date": "2026-11-05", "absent": ["S1"], "late": []},
        {"date": "2026-11-06", "absent": ["S1"], "late": []},
    ]

    # Max streak was 2 before reset, and 2 after reset. min_streak=3 -> no results
    assert consecutive_absences(records, min_streak=3) == {}
    assert consecutive_absences(records, min_streak=2) == {"S1": 2}


# ==========================================
# Gate 2 Real Data Test via School API
# ==========================================

def test_consecutive_absences_on_real_data():
    """Gate requirement 2: Attendance on real data returns exactly:

    - Reyansh Rathore (6A, Pratap Nagar, 4)
    - Arjun Goyal (6B, Malviya Nagar, 4)
    - Vivaan Agarwal (8A, Sodala, 4)
    """
    client = TestClient(app)

    att_resp = client.get("/school/attendance")
    assert att_resp.status_code == 200
    records = att_resp.json()

    stu_resp = client.get("/school/students")
    assert stu_resp.status_code == 200
    students = stu_resp.json()

    results = get_consecutive_absent_students(records, students, min_streak=3)

    # Format into (name, class, area, streak)
    tuples = [(r["name"], r["class_name"], r["home_area"], r["streak"]) for r in results]

    expected = {
        ("Reyansh Rathore", "6A", "Pratap Nagar", 4),
        ("Arjun Goyal", "6B", "Malviya Nagar", 4),
        ("Vivaan Agarwal", "8A", "Sodala", 4),
    }

    assert len(tuples) == 3
    assert set(tuples) == expected

