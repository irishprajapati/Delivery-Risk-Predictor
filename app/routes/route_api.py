from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import Prediction
from app.utils.dependencies import get_current_user
from app.services.google_directions import enrich_route_info
from app.utils.location import compute_route_info

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _find_latest_prediction(db: Session, phone_number: str) -> Prediction | None:
    predictions = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    for prediction in predictions:
        stored_phone = (prediction.input_data or {}).get("phone_number")
        if stored_phone == phone_number:
            return prediction
    return None


@router.get("/route/{phone_number}")
def get_route_by_phone(
    phone_number: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    prediction = _find_latest_prediction(db, phone_number)
    if not prediction:
        raise HTTPException(status_code=404, detail="No prediction found for this phone number")

    input_data = prediction.input_data or {}
    pickup_address = input_data.get("pickup_address", "")
    delivery_address = input_data.get("delivery_address", "")

    route_info = input_data.get("route_info")
    if not route_info:
        route_info = compute_route_info(pickup_address, delivery_address)

    route_info = enrich_route_info(route_info)

    return {
        "phone_number": phone_number,
        "pickup_address": pickup_address,
        "delivery_address": delivery_address,
        "risk": prediction.risk,
        "prediction": prediction.prediction,
        "probability": prediction.probability,
        "estimated_distance_km": route_info["estimated_distance_km"],
        "estimated_duration_min": route_info.get("estimated_duration_min"),
        "route_polyline": route_info.get("route_polyline", []),
        "route_source": route_info.get("route_source", "straight_line"),
        "pickup_coordinates": route_info["pickup_coordinates"],
        "delivery_coordinates": route_info["delivery_coordinates"],
        "pickup_district": route_info["pickup_district"],
        "delivery_district": route_info["delivery_district"],
        "pickup_area": route_info.get("pickup_area"),
        "delivery_area": route_info.get("delivery_area"),
        "created_at": prediction.created_at,
    }
