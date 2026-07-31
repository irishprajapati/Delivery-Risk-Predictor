from fastapi import APIRouter, Depends, HTTPException

from app.schemas import PredictionInput
from app.ml.predictor import predict, get_shap_explanation, raw_to_model_dataframe
from app.utils.dependencies import get_current_user
from app.services.ors_service import LocationValidationError, ORSServiceError
from app.services.weather_service import WeatherServiceError, fetch_route_weather
from app.utils.location import compute_route_info

router = APIRouter()


@router.post("/predict/explain")
def explain_prediction(
    data: PredictionInput,
    current_user=Depends(get_current_user),
):
    try:
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

        df = raw_to_model_dataframe(raw_input)
        result = predict(raw_input)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result)

        shap_explanation = get_shap_explanation(df)

        if isinstance(shap_explanation, list) and shap_explanation and "error" in shap_explanation[0]:
            raise HTTPException(
                status_code=500,
                detail=f"SHAP failed: {shap_explanation[0]['error']}",
            )

        return {
            **result,
            "shap_explanations": shap_explanation,
            "pickup_weather": weather_info["pickup_weather"],
            "midpoint_weather": weather_info["midpoint_weather"],
            "delivery_weather": weather_info["delivery_weather"],
            "weather_risk": weather_info["weather_risk"],
            "weather_risk_message": weather_info["weather_risk_message"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
