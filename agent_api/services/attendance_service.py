"""Attendance service for calculating consecutive absence streaks.

Deterministic Python calculation - zero LLM or heuristics.
"""

from typing import Any
import httpx

from agent_api.tools.school_tools import get_attendance, get_students


def consecutive_absences(
    records: list[dict[str, Any] | Any],
    min_streak: int = 3,
) -> dict[str, int]:
    """Calculate maximum consecutive absence streak for students across recorded school days.

    Counting is based strictly on sequential recorded school days. Sundays (and any
    school holidays) are absent from the dataset and are therefore naturally skipped,
    meaning a Friday absence followed by a Monday absence counts as two consecutive
    school-day absences.

    Parameters:
        records: List of attendance day dictionaries or Pydantic models.
        min_streak: Minimum streak threshold to include in the output (default 3).

    Returns:
        Dict mapping student_id -> consecutive absence count for streaks >= min_streak.
    """
    if not records:
        return {}

    # Sort records chronologically by date
    def _extract_date(r: dict[str, Any] | Any) -> str:
        d = r.get("date") if isinstance(r, dict) else getattr(r, "date", "")
        return str(d)

    sorted_records = sorted(records, key=_extract_date)

    # Collect all student IDs appearing in any attendance record
    all_students: set[str] = set()
    for r in sorted_records:
        absent = r.get("absent", []) if isinstance(r, dict) else getattr(r, "absent", [])
        late = r.get("late", []) if isinstance(r, dict) else getattr(r, "late", [])
        all_students.update(absent)
        all_students.update(late)

    current_streaks: dict[str, int] = {sid: 0 for sid in all_students}
    max_streaks: dict[str, int] = {sid: 0 for sid in all_students}

    for r in sorted_records:
        absent_list = r.get("absent", []) if isinstance(r, dict) else getattr(r, "absent", [])
        absent_set = set(absent_list)

        for sid in all_students:
            if sid in absent_set:
                current_streaks[sid] += 1
                if current_streaks[sid] > max_streaks[sid]:
                    max_streaks[sid] = current_streaks[sid]
            else:
                # Present or late resets the absence streak
                current_streaks[sid] = 0

    return {sid: streak for sid, streak in max_streaks.items() if streak >= min_streak}


def get_consecutive_absent_students(
    records: list[dict[str, Any] | Any],
    students: list[dict[str, Any] | Any],
    min_streak: int = 3,
) -> list[dict[str, Any]]:
    """Enrich consecutive absence records with student metadata.

    Returns a list of dicts with student details and their absence streak.
    """
    streaks = consecutive_absences(records, min_streak=min_streak)
    if not streaks:
        return []

    # Map student metadata by ID
    student_map: dict[str, dict[str, Any]] = {}
    for s in students:
        if isinstance(s, dict):
            sid = s.get("id", "")
            student_map[sid] = {
                "id": sid,
                "name": s.get("name", ""),
                "class_name": s.get("class") or s.get("class_name", ""),
                "home_area": s.get("homeArea") or s.get("home_area", ""),
            }
        else:
            sid = getattr(s, "id", "")
            student_map[sid] = {
                "id": sid,
                "name": getattr(s, "name", ""),
                "class_name": getattr(s, "class_name", ""),
                "home_area": getattr(s, "home_area", ""),
            }

    results = []
    for sid, streak in streaks.items():
        meta = student_map.get(sid, {"id": sid, "name": sid, "class_name": "Unknown", "home_area": "Unknown"})
        results.append({
            "student_id": sid,
            "name": meta["name"],
            "class_name": meta["class_name"],
            "home_area": meta["home_area"],
            "streak": streak,
        })

    # Sort results predictably by streak descending, then by name
    return sorted(results, key=lambda x: (-x["streak"], x["name"]))


def fetch_and_evaluate_absences(
    min_streak: int = 3,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch records from School API via school_tools and compute consecutive absences."""
    att_res = get_attendance(client=client)
    if att_res.get("status") != "ok":
        return att_res

    stu_res = get_students(client=client)
    if stu_res.get("status") != "ok":
        return stu_res

    records = att_res.get("data", [])
    students = stu_res.get("data", [])

    data = get_consecutive_absent_students(records, students, min_streak=min_streak)
    return {"status": "ok", "data": data}
