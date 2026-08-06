from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import *
from app.schemas import *
from app.utils.dependencies import get_current_user, get_current_admin, get_current_customer
from app.services.ors_service import LocationValidationError, ORSServiceError
from app.utils.location import compute_route_info
from app.services.action_engine import calculate_risk
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

@router.get("/admin/dashboard")
def admin_dashboard(admin=Depends(get_current_admin)):
    return {"message": "Welcome Admin"}

@router.get("/customer/profile")
def customer_profile(customer=Depends(get_current_customer)):
    return {"phone": customer.phone}

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(OrderCategory).all()

@router.get("/items/{category_id}")
def get_items(category_id: int, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.category_id == category_id).all()

@router.post("/place-order")
def place_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_customer)
):
    item = db.query(Item).filter(Item.id == data.item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    total_price = item.price * data.quantity

    risk_score = calculate_risk(
        db=db,
        customer=current,
        item=item,
        quantity=data.quantity,
        total_price=total_price,
        is_cod=data.is_cod,
        address_text=data.address
    )

    if risk_score >= 0.8:
        status = "blocked"
    elif risk_score >= 0.5:
        status = "pending_review"
    else:
        status = "approved"

    order = Order(
        customer_id=current.id,
        item_id=item.id,
        quantity=data.quantity,
        total_price=total_price,
        status=status,
        risk_score=risk_score
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "Order placed",
        "order_id": order.id,
        "total_price": total_price,
        "status": status,
        "risk_score": risk_score
    }

@router.post("/create-item")
def create_item(
    name: str,
    price: float,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    item = Item(name=name, price=price)

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Item created",
        "item_id": item.id
    }

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price
        }
        for item in items
    ]