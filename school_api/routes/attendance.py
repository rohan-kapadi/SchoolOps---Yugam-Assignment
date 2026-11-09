from datetime import date

from fastapi import APIRouter, HTTPException, Query

from school_api.data_loader import get_school_data, parse_date, resolve_class
from school_api.schemas import AttendanceDay

router = APIRouter(tags=["attendance"])


@router.get("/attendance", response_model=list[AttendanceDay])
def list_attendance(
    student_id: str | None = None,
    class_name: str | None = Query(default=None, alias="class"),
    day: str | None = Query(default=None, alias="date"),
) -> list[AttendanceDay]:
    """Return recorded school days.

    A student or class filter keeps every school day and only narrows the
    absent and late id lists. An empty list for that day means those students
    were present. Sundays are missing from the file, so they are not returned.
    """
    data = get_school_data()
    on_date = _known_date(day) if day is not None else None
    canonical_class = _known_class(class_name) if class_name is not None else None
    if student_id is not None and student_id not in data.students_by_id:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    days = data.attendance
    if on_date is not None:
        days = [record for record in days if record.date == on_date]

    allowed = _allowed_ids(student_id, canonical_class)
    if allowed is None:
        return days
    return [_narrow(record, allowed) for record in days]


def _known_class(class_name: str) -> str:
    try:
        return resolve_class(class_name)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _known_date(value: str) -> date:
    try:
        return parse_date(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _allowed_ids(student_id: str | None, class_name: str | None) -> set[str] | None:
    if student_id is None and class_name is None:
        return None
    data = get_school_data()
    if class_name is None:
        return {student_id} if student_id is not None else None
    ids = {student.id for student in data.students if student.class_name == class_name}
    if student_id is not None:
        return ids & {student_id}
    return ids


def _narrow(record: AttendanceDay, allowed: set[str]) -> AttendanceDay:
    return AttendanceDay(
        date=record.date,
        absent=[student_id for student_id in record.absent if student_id in allowed],
        late=[student_id for student_id in record.late if student_id in allowed],
    )
