from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import Prediction, User
from app.utils.dependencies import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/history")
def get_history(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )


@router.get("/history/{prediction_id}")
def get_history_item(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction
