from fastapi import APIRouter, HTTPException

from school_api.data_loader import get_school_data
from school_api.schemas import BusRoute

router = APIRouter(tags=["routes"])


@router.get("/routes", response_model=list[BusRoute])
def list_routes() -> list[BusRoute]:
    return get_school_data().routes


@router.get("/routes/{route_id}", response_model=BusRoute)
def get_route(route_id: str) -> BusRoute:
    route = get_school_data().routes_by_id.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
    return route
