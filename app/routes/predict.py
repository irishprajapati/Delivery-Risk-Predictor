import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import Prediction, CustomerProfile
from app.ml.predictor import predict
from app.schemas import PredictionInput
from app.utils.dependencies import get_current_user
from app.utils.feature_engineering import process_input
from app.services.ors_service import LocationValidationError, ORSServiceError, VALLEY_ONLY_MESSAGE
from app.services.weather_service import WeatherServiceError, fetch_route_weather
from app.utils.location import apply_distance_risk, compute_route_info
from app.services.action_engine import generate_actions
from app.services.customer_profile import update_customer_profile

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def predict_route(
    data: PredictionInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        route_info = compute_route_info(data.pickup_address, data.delivery_address)
    except LocationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ORSServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        weather_info = fetch_route_weather(route_info)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    raw_input = data.model_dump()
    raw_input["route_info"] = route_info
    raw_input["weather_info"] = weather_info

    logger.info("Received raw input: %s", raw_input)

    processed_features = process_input(raw_input)
    logger.info("Transformed features: %s", processed_features)

    result = predict(raw_input)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("detail", "Prediction failed"))

    boosted_probability, boosted_risk = apply_distance_risk(
        result["probability"],
        result["risk"],
        route_info["estimated_distance_km"],
    )
    result["probability"] = boosted_probability
    result["risk"] = boosted_risk

    actions = generate_actions(
        input_data={**raw_input, **processed_features},
        prediction=result["prediction"],
        probability=result["probability"],
    )

    if route_info["estimated_distance_km"] > 15.0:
        actions.append(
            f"Long route ({route_info['estimated_distance_km']} km) — consider priority dispatch"
        )

    if weather_info["weather_risk"] == "HIGH":
        actions.append(weather_info["weather_risk_message"])
    elif weather_info["weather_risk"] == "MEDIUM":
        actions.append(weather_info["weather_risk_message"])

    new_prediction = Prediction(
        user_id=current_user.id,
        input_data=raw_input,
        prediction=result["prediction"],
        probability=result["probability"],
        risk=result["risk"],
    )
    db.add(new_prediction)
    db.commit()
    db.refresh(new_prediction)

    update_customer_profile(
        db=db,
        phone_number=data.phone_number,
        prediction=result["prediction"],
        probability=result["probability"],
    )

    profile = db.query(CustomerProfile).filter_by(
        phone_number=data.phone_number
    ).first()

    if profile:
        result["customer_stats"] = {
            "total_orders": profile.total_orders,
            "failed_deliveries": profile.failed_deliveries,
            "failure_rate": round(profile.failure_rate, 2),
        }

        if profile.total_orders >= 5 and profile.failure_rate > 0.6:
            result["customer_risk"] = "HIGH"
            actions.append("Force prepaid for this customer")
            actions.append("Flag customer for manual review")
        else:
            result["customer_risk"] = "LOW"

    result["actions"] = actions
    result["phone_number"] = data.phone_number

    return {
        "prediction": result["prediction"],
        "risk": result["risk"],
        "phone_number": result["phone_number"],
        "probability": result["probability"],
        "processed_features": result["processed_features"],
        "actions": result["actions"],
        "customer_stats": result.get("customer_stats"),
        "customer_risk": result.get("customer_risk"),
        "reasons": result.get("reasons", []),
        "prediction_id": new_prediction.id,
        "estimated_distance_km": route_info["estimated_distance_km"],
        "estimated_duration_min": route_info.get("estimated_duration_min"),
        "pickup_district": route_info["pickup_district"],
        "delivery_district": route_info["delivery_district"],
        "pickup_coordinates": route_info["pickup_coordinates"],
        "delivery_coordinates": route_info["delivery_coordinates"],
        "route_source": route_info.get("route_source"),
        "pickup_weather": weather_info["pickup_weather"],
        "midpoint_weather": weather_info["midpoint_weather"],
        "delivery_weather": weather_info["delivery_weather"],
        "weather_risk": weather_info["weather_risk"],
        "weather_risk_message": weather_info["weather_risk_message"],
    }
