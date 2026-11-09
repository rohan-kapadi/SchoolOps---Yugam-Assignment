"""Load school-data.json once.

This is the only module allowed to open that file. Agent code calls the
School API over HTTP instead.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from school_api.schemas import (
    AttendanceDay,
    BusRoute,
    Event,
    School,
    SchoolFile,
    Student,
)

_DATA_PATH = Path(__file__).resolve().parent.parent / "school-data.json"
_DATE_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class SchoolData:
    school: School
    policy: str
    classes: list[str]
    students: list[Student]
    routes: list[BusRoute]
    events: list[Event]
    attendance: list[AttendanceDay]
    students_by_id: dict[str, Student]
    routes_by_id: dict[str, BusRoute]


_cached: SchoolData | None = None


def get_school_data() -> SchoolData:
    global _cached
    if _cached is None:
        _cached = _load(_DATA_PATH)
    return _cached


def _load(path: Path) -> SchoolData:
    if not path.is_file():
        raise FileNotFoundError(f"School data file not found: {path}")
    parsed = SchoolFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    students_by_id = {student.id: student for student in parsed.students}
    routes_by_id = {route.id: route for route in parsed.routes}
    if len(students_by_id) != len(parsed.students):
        raise ValueError("Duplicate student ids in school-data.json")
    if len(routes_by_id) != len(parsed.routes):
        raise ValueError("Duplicate route ids in school-data.json")
    return SchoolData(
        school=parsed.school,
        policy=parsed.policy,
        classes=parsed.classes,
        students=parsed.students,
        routes=parsed.routes,
        events=parsed.events,
        attendance=parsed.attendance,
        students_by_id=students_by_id,
        routes_by_id=routes_by_id,
    )


def resolve_class(class_name: str) -> str:
    """Return the class name as stored, matching without case sensitivity."""
    query = class_name.strip().casefold()
    for name in get_school_data().classes:
        if name.casefold() == query:
            return name
    valid = ", ".join(get_school_data().classes)
    raise KeyError(f"Unknown class '{class_name}'. Valid classes: {valid}")


def parse_date(value: str) -> date:
    """Accept only a real calendar date written as YYYY-MM-DD."""
    if _DATE_TEXT.fullmatch(value) is None:
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Use a real calendar date in YYYY-MM-DD.") from None
