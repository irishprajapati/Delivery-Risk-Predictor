from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.model import Prediction, CustomerProfile
from app.ml.predictor import predict
from app.schemas import PredictionInput
from app.utils.dependencies import get_current_user
from app.services.action_engine import generate_actions
from app.services.customer_profile import update_customer_profile
from fastapi import HTTPException
#groups the route
router = APIRouter()
#database dependency
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
    current_user=Depends(get_current_user)
):
    # Run ML prediction
    result = predict(data)

    if not result["success"]:
        return result

    input_dict = data.model_dump()
    #checking the security
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Generate base actions
    actions = generate_actions(
        input_data=input_dict,
        prediction=result["prediction"],
        probability=result["probability"]
    )

    # Save prediction
    new_prediction = Prediction(
        user_id=current_user.id,
        input_data=input_dict,
        prediction=result["prediction"],
        probability=result["probability"],
        risk=result["risk"]
    )
    db.add(new_prediction)
    db.commit()

    # 🔁 Update customer profile
    update_customer_profile(
    db=db,
    phone_number=data.phone_number,
    prediction=result["prediction"],
    probability=result["probability"]
    )

    # Fetch updated profile
    profile = db.query(CustomerProfile).filter_by(
        phone_number=data.phone_number
    ).first()
    # Customer intelligence layer (WITH THRESHOLD)
    if profile:
        result["customer_stats"] = {
            "total_orders": profile.total_orders,
            "failed_deliveries": profile.failed_deliveries,
            "failure_rate": round(profile.failure_rate, 2)
        }

        # 🔥 FIX: Apply threshold (minimum 3 orders)
        if profile.total_orders >= 5 and profile.failure_rate > 0.6:
            result["customer_risk"] = "HIGH"
            actions.append("Force prepaid for this customer")
            actions.append("Flag customer for manual review")
        else:
            result["customer_risk"] = "LOW"

    # 📤 Attach actions
    result["actions"] = actions

    return result