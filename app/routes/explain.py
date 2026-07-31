from fastapi import APIRouter, Depends, HTTPException

from app.schemas import PredictionInput
from app.ml.predictor import predict, get_shap_explanation, raw_to_model_dataframe
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.post("/predict/explain")
def explain_prediction(
    data: PredictionInput,
    current_user=Depends(get_current_user),
):
    try:
        if not current_user.role or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        raw_input = data.model_dump()
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
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
