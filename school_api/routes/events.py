from fastapi import APIRouter

from school_api.data_loader import get_school_data
from school_api.schemas import Event

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[Event])
def list_events() -> list[Event]:
    return get_school_data().events
