from fastapi import APIRouter, HTTPException, Query

from school_api.data_loader import get_school_data, resolve_class
from school_api.schemas import Student

router = APIRouter(tags=["students"])


@router.get("/students", response_model=list[Student])
def list_students(
    name: str | None = None,
    class_name: str | None = Query(default=None, alias="class"),
) -> list[Student]:
    """Search students by exact name and/or class. Name match is case-insensitive."""
    data = get_school_data()
    students = data.students
    if class_name is not None:
        students = [student for student in students if student.class_name == _known_class(class_name)]
    if name is not None and name.strip():
        query = name.strip().casefold()
        students = [student for student in students if student.name.casefold() == query]
    return students


@router.get("/students/{student_id}", response_model=Student)
def get_student(student_id: str) -> Student:
    student = get_school_data().students_by_id.get(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return student


def _known_class(class_name: str) -> str:
    try:
        return resolve_class(class_name)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
