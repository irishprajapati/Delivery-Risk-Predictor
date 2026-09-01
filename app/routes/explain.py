"""
Delivery prediction explainability endpoint.

Flow:

    Request
      ↓
    Same /predict orchestration
      ↓
    Same validated 41-feature vector
      ↓
    Same trained ML model
      ↓
    Prediction result
      ↓
    SHAP explanation
      ↓
    Human-readable reasons

This endpoint does NOT implement a second prediction pipeline.
It reuses the exact /predict flow so prediction and explanation
cannot silently diverge.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.ml.predictor import (
    generate_explanation_reasons,
    get_shap_explanation,
)
from app.routes.predict import predict_delivery
from app.schemas import PredictionInput
from app.utils.dependencies import get_current_user


router = APIRouter()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# AUTHORIZATION
# ============================================================

def _is_admin_user(
    current_user,
) -> bool:
    """
    Support both dictionary-based and SQLAlchemy user objects.
    """

    if isinstance(
        current_user,
        dict,
    ):
        return (
            current_user.get(
                "role"
            )
            == "admin"
        )

    return (
        getattr(
            current_user,
            "role",
            None,
        )
        == "admin"
    )


# ============================================================
# EXPLANATION ENDPOINT
# ============================================================

@router.post(
    "/predict/explain"
)
def explain_prediction(
    data: PredictionInput,
    db: Session = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    ),
):
    """
    Return the normal prediction response plus SHAP explanations.
    """

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    if not _is_admin_user(
        current_user
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    # ========================================================
    # REUSE /PREDICT PIPELINE
    # ========================================================

    try:

        prediction_result = (
            predict_delivery(
                data=data,
                db=db,
                current_user=current_user,
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Prediction pipeline failed: "
                f"{exc}"
            ),
        ) from exc

    # ========================================================
    # EXTRACT EXACT 41 FEATURES
    # ========================================================

    features = (
        prediction_result.get(
            "features"
        )
    )

    if not isinstance(
        features,
        dict,
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Prediction response did not "
                "contain the model features."
            ),
        )

    # ========================================================
    # SHAP
    # ========================================================

    shap_explanation = (
        get_shap_explanation(
            features
        )
    )

    if (
        isinstance(
            shap_explanation,
            list,
        )
        and shap_explanation
        and isinstance(
            shap_explanation[0],
            dict,
        )
        and "error"
        in shap_explanation[0]
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "SHAP explanation failed: "
                f"{shap_explanation[0]['error']}"
            ),
        )

    # ========================================================
    # HUMAN-READABLE REASONS
    # ========================================================

    reasons = (
        generate_explanation_reasons(
            features=features,
            probability=prediction_result[
                "probability"
            ],
        )
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        **prediction_result,

        "explanations": {
            "shap": (
                shap_explanation
            ),
            "reasons": reasons,
        },
    }