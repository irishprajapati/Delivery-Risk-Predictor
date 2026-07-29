from fastapi import APIRouter
from app.services.route_service import get_route_data

router = APIRouter()

@router.get("/route")
def route(pickup: str, delivery: str):
    return get_route_data(pickup, delivery)