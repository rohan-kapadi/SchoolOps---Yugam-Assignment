from fastapi import APIRouter

from school_api.data_loader import get_school_data
from school_api.schemas import School

router = APIRouter(tags=["school"])


@router.get("", response_model=School)
def get_school() -> School:
    """School profile, including coordinates.

    Events on the school grounds do not carry lat/lon. Callers use this
    instead of opening school-data.json.
    """
    return get_school_data().school
