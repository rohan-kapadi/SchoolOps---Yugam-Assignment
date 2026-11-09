from fastapi import APIRouter

from school_api.data_loader import get_school_data
from school_api.schemas import PolicyResponse

router = APIRouter(tags=["policy"])


@router.get("/policy", response_model=PolicyResponse)
def get_policy() -> PolicyResponse:
    return PolicyResponse(policy=get_school_data().policy)
