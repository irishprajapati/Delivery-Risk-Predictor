from fastapi import APIRouter, Depends, HTTPException
from app.schemas import PredictionInput
from app.ml.predictor import predict, get_shap_explanation, preprocess_input
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.post("/predict/explain")
def explain_prediction(
    data: PredictionInput,
    current_user=Depends(get_current_user)
):
    try:
        # Convert request to dict
        input_dict = data.model_dump()

        # Preprocess input → dataframe
        df = preprocess_input(input_dict)

        # Run prediction
        result = predict(data)
        
        #checking the security
        if not current_user.role or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        # Stop early if prediction failed
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result)

        # Get SHAP explanation (this is where your real fix matters)
        shap_explanation = get_shap_explanation(df)

        # If SHAP failed, expose clearly (don’t silently pass garbage)
        if isinstance(shap_explanation, list) and "error" in shap_explanation[0]:
            raise HTTPException(
                status_code=500,
                detail=f"SHAP failed: {shap_explanation[0]['error']}"
            )

        return {
            **result,
            "shap_explanations": shap_explanation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))