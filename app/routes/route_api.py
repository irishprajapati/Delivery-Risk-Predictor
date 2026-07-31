from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import Prediction, User
from app.utils.dependencies import get_current_user
from app.services.ors_service import LocationValidationError, ORSServiceError
from app.utils.location import compute_route_info

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_route_response(prediction: Prediction) -> dict:
    input_data = prediction.input_data or {}
    pickup_address = input_data.get("pickup_address", "")
    delivery_address = input_data.get("delivery_address", "")
    phone_number = input_data.get("phone_number", "")

    # Always re-fetch route from ORS using stored addresses for accuracy
    try:
        route_info = compute_route_info(pickup_address, delivery_address)
    except (LocationValidationError, ORSServiceError):
        # Fall back to stored route info if live re-fetch fails
        route_info = input_data.get("route_info")
        if not route_info:
            raise

    return {
        "prediction_id": prediction.id,
        "phone_number": phone_number,
        "pickup_address": pickup_address,
        "delivery_address": delivery_address,
        "risk": prediction.risk,
        "prediction": prediction.prediction,
        "probability": prediction.probability,
        "estimated_distance_km": route_info["estimated_distance_km"],
        "estimated_duration_min": route_info.get("estimated_duration_min"),
        "route_polyline": route_info.get("route_polyline", []),
        "route_source": route_info.get("route_source", "openrouteservice"),
        "pickup_coordinates": route_info["pickup_coordinates"],
        "delivery_coordinates": route_info["delivery_coordinates"],
        "pickup_district": route_info["pickup_district"],
        "delivery_district": route_info["delivery_district"],
        "pickup_area": route_info.get("pickup_area"),
        "delivery_area": route_info.get("delivery_area"),
        "created_at": prediction.created_at,
    }


@router.get("/route/prediction/{prediction_id}")
def get_route_by_prediction_id(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    try:
        return _build_route_response(prediction)
    except LocationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ORSServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/route/{phone_number}")
def get_route_by_phone(
    phone_number: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Legacy endpoint — returns latest prediction for a phone number."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    predictions = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    prediction = None
    for item in predictions:
        stored_phone = (item.input_data or {}).get("phone_number")
        if stored_phone == phone_number:
            prediction = item
            break

    if not prediction:
        raise HTTPException(status_code=404, detail="No prediction found for this phone number")

    try:
        return _build_route_response(prediction)
    except LocationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ORSServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
