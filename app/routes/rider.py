from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import User, Rider, Delivery, Order, Customer, DeliveryLocation, Prediction, RiderAreaPerformance
from app.utils.dependencies import get_db, get_current_rider, get_current_user
from app.utils.security import verify_password, create_access_token, get_password_hash
from app.services.delivery_service import (
    STATUS_ASSIGNED,
    STATUS_PICKED_UP,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_UNREACHABLE,
    start_delivery,
    mark_out_for_delivery,
    complete_delivery,
    fail_delivery,
    rider_success_rate,
    get_rider_area_performance,
    _infer_delivery_area,
)

router = APIRouter(prefix="/rider", tags=["Rider Operations"])


# ============================================================
# SCHEMAS
# ============================================================

class RiderLoginRequest(BaseModel):
    phone: str
    password: str


class RiderFailRequest(BaseModel):
    reason_code: str = Field(..., description="Standardized failure reason code")
    notes: Optional[str] = Field(None, description="Detailed operational notes")


VALID_FAILURE_REASONS = {
    "CUSTOMER_UNAVAILABLE": {
        "label": "Customer Unavailable",
        "unreachable": True,
        "requires_notes": False,
    },
    "PHONE_UNREACHABLE": {
        "label": "Phone Unreachable / Switched Off",
        "unreachable": True,
        "requires_notes": False,
    },
    "CUSTOMER_REQUESTED_RESCHEDULE": {
        "label": "Customer Requested Reschedule",
        "unreachable": True,
        "requires_notes": False,
    },
    "CUSTOMER_REFUSED": {
        "label": "Customer Refused Delivery",
        "unreachable": False,
        "requires_notes": True,
    },
    "WRONG_ADDRESS": {
        "label": "Wrong Address / Incomplete",
        "unreachable": False,
        "requires_notes": True,
    },
    "ADDRESS_NOT_FOUND": {
        "label": "Address Not Found / Inaccessible Location",
        "unreachable": False,
        "requires_notes": False,
    },
    "ROAD_INACCESSIBLE": {
        "label": "Road Inaccessible / Blocked",
        "unreachable": False,
        "requires_notes": True,
    },
    "VEHICLE_OR_BIKE_ISSUE": {
        "label": "Vehicle Breakdown / Issue",
        "unreachable": False,
        "requires_notes": False,
    },
    "WEATHER_OR_ROAD_CONDITION": {
        "label": "Severe Weather / Road Hazard",
        "unreachable": False,
        "requires_notes": False,
    },
    "PACKAGE_DAMAGED": {
        "label": "Package Damaged in Transit",
        "unreachable": False,
        "requires_notes": True,
    },
    "PAYMENT_ISSUE": {
        "label": "Payment Issue / Customer Cannot Pay",
        "unreachable": False,
        "requires_notes": False,
    },
    "OTHER": {
        "label": "Other Reason",
        "unreachable": False,
        "requires_notes": True,
    },
}


# ============================================================
# AUTHENTICATION
# ============================================================

@router.post("/login")
def rider_login(
    data: Optional[RiderLoginRequest] = None,
    phone: Optional[str] = None,
    password: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Authenticate a fleet rider and return a JWT bearer token.
    Supports both JSON body and form/query parameters.
    """
    req_phone = data.phone if data else phone
    req_password = data.password if data else password

    if not req_phone or not req_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number and password are required.",
        )

    clean_phone = req_phone.strip()
    rider = db.query(Rider).filter(Rider.phone == clean_phone).first()

    if not rider:
        # Check by name or ID if matching format
        rider = db.query(Rider).filter(Rider.name.ilike(clean_phone)).first()

    if not rider:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Rider phone not registered.",
        )

    if not rider.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rider account is inactive. Please contact administrator.",
        )

    # Check or create User auth record for rider
    user = db.query(User).filter(User.username == rider.phone, User.role == "rider").first()
    if user:
        if not verify_password(req_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )
    else:
        # Allow default rider passwords for pre-seeded fleet (e.g., rider123, password, adminpassword)
        if req_password not in {"rider123", "password", "adminpassword", "123456"}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )
        # Register user record
        user = User(
            username=rider.phone,
            password=get_password_hash(req_password),
            role="rider",
            is_active=True,
        )
        db.add(user)
        db.commit()

    token = create_access_token({
        "sub": str(rider.id),
        "role": "rider",
        "phone": rider.phone,
        "name": rider.name,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "rider": {
            "id": rider.id,
            "name": rider.name,
            "phone": rider.phone,
            "area": rider.area,
        },
    }


# ============================================================
# RIDER PROFILE & KPI
# ============================================================

@router.get("/profile")
def get_rider_profile(
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Return operational profile, current workload, capacity, and performance statistics for the authenticated rider.
    """
    area_perf = None
    if rider.area:
        area_history = get_rider_area_performance(db=db, rider=rider, area=rider.area)
        area_perf = {
            "area": rider.area,
            "success_rate": area_history.get("success_rate", 0.85),
            "total_deliveries": area_history.get("total_deliveries", 0),
        }

    return {
        "id": rider.id,
        "name": rider.name,
        "phone": rider.phone,
        "area": rider.area or "Kathmandu Valley",
        "is_active": rider.is_active,
        "current_order_count": rider.current_order_count or 0,
        "max_orders_per_day": rider.max_orders_per_day or 20,
        "remaining_capacity": max(0, (rider.max_orders_per_day or 20) - (rider.current_order_count or 0)),
        "completed_orders": rider.completed_orders or 0,
        "failed_deliveries": rider.failed_deliveries or 0,
        "overall_success_rate": round(rider_success_rate(rider), 4),
        "area_performance": area_perf,
        "current_latitude": rider.current_latitude or 27.6710,
        "current_longitude": rider.current_longitude or 85.3380,
    }


# ============================================================
# RIDER DELIVERIES LIST
# ============================================================

@router.get("/deliveries")
def get_rider_deliveries(
    status: Optional[str] = Query(None, description="Filter by status: assigned, picked_up, out_for_delivery, delivered, failed, unreachable"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None, description="Search by order ID, customer phone, area, address, item"),
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Return paginated deliveries assigned strictly to the authenticated rider.
    Ordered with active deliveries first, high-risk first, then oldest assigned first.
    """
    query = db.query(Delivery).filter(Delivery.rider_id == rider.id)

    if status and status != "all":
        st = status.lower().strip()
        if st == "active":
            query = query.filter(Delivery.status.in_([STATUS_ASSIGNED, STATUS_PICKED_UP, STATUS_OUT_FOR_DELIVERY]))
        elif st == "failed":
            query = query.filter(Delivery.status.in_([STATUS_FAILED, STATUS_UNREACHABLE]))
        else:
            query = query.filter(Delivery.status == st)

    deliveries = query.all()
    results = []

    for d in deliveries:
        order = d.order
        if not order:
            continue

        risk_val = str(order.risk_level or "LOW").upper()
        prob_val = order.risk_score

        if order.predictions:
            latest_p = sorted(
                order.predictions,
                key=lambda p: p.created_at or datetime.min,
                reverse=True,
            )[0]
            if latest_p.risk:
                risk_val = str(latest_p.risk).upper()
            if latest_p.probability is not None:
                prob_val = latest_p.probability

        area = "Kathmandu"
        for district in ("lalitpur", "kathmandu", "bhaktapur"):
            if district in (order.address or "").lower():
                area = district.capitalize()
                break

        results.append({
            "delivery_id": d.id,
            "order_id": order.id,
            "status": d.status,
            "attempt_count": d.attempt_count or 0,
            "failure_reason": d.failure_reason,
            "item_name": order.item.name if order.item else "Package",
            "quantity": order.quantity,
            "total_price": order.total_price,
            "is_cod": order.is_cod,
            "payment_method": "cod" if order.is_cod else "prepaid",
            "prepaid_amount": order.prepaid_amount,
            "customer_phone": order.customer.phone if order.customer else "—",
            "address": order.address,
            "area": area,
            "latitude": order.latitude,
            "longitude": order.longitude,
            "risk": risk_val,
            "probability": prob_val,
            "distance_km": d.distance_km,
            "estimated_duration": d.estimated_duration,
            "assigned_at": d.assigned_at.isoformat() if d.assigned_at else None,
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    # Search filter
    if search:
        q = search.strip().lower()
        results = [
            r for r in results
            if (
                q in str(r["order_id"]).lower()
                or q in str(r["customer_phone"]).lower()
                or q in str(r["area"]).lower()
                or q in str(r["address"]).lower()
                or q in str(r["item_name"]).lower()
            )
        ]

    # Custom multi-criteria sorting:
    # 1. Active statuses first (assigned: 0, picked_up: 1, out_for_delivery: 2, other: 3)
    # 2. Risk (HIGH: 0, MEDIUM: 1, LOW: 2)
    # 3. Oldest assigned first
    status_priority = {
        STATUS_ASSIGNED: 0,
        STATUS_PICKED_UP: 1,
        STATUS_OUT_FOR_DELIVERY: 2,
        STATUS_UNREACHABLE: 3,
        STATUS_FAILED: 4,
        STATUS_DELIVERED: 5,
    }
    risk_priority = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    results.sort(
        key=lambda r: (
            status_priority.get(r["status"], 99),
            risk_priority.get(r["risk"], 99),
            r["assigned_at"] or r["created_at"] or "",
        )
    )

    total_items = len(results)
    total_pages = max(1, (total_items + limit - 1) // limit)
    offset = (page - 1) * limit
    paginated_items = results[offset : offset + limit]

    return {
        "items": paginated_items,
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


# ============================================================
# RIDER DELIVERY DETAIL
# ============================================================

@router.get("/deliveries/{delivery_id}")
def get_rider_delivery_detail(
    delivery_id: int,
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Return delivery detail for an order owned by the authenticated rider.
    Enforces that Rider A cannot inspect Rider B's deliveries.
    """
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )

    if delivery.rider_id != rider.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found or not assigned to you.",
        )

    order = delivery.order
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found for this delivery.",
        )

    # ML & Risk info
    risk_val = str(order.risk_level or "LOW").upper()
    prob_val = order.risk_score
    reasons = []
    shap_factors = []

    if order.predictions:
        latest_p = sorted(
            order.predictions,
            key=lambda p: p.created_at or datetime.min,
            reverse=True,
        )[0]
        if latest_p.risk:
            risk_val = str(latest_p.risk).upper()
        prob_val = latest_p.probability
        if latest_p.input_data and isinstance(latest_p.input_data, dict):
            reasons = latest_p.input_data.get("reasons", [])
            shap_factors = latest_p.input_data.get("shap_factors", [])

    area = _infer_delivery_area(order=order, delivery_location=order.location) or "Kathmandu Valley"

    return {
        "delivery_id": delivery.id,
        "status": delivery.status,
        "attempt_count": delivery.attempt_count or 0,
        "failure_reason": delivery.failure_reason,
        "assigned_at": delivery.assigned_at.isoformat() if delivery.assigned_at else None,
        "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
        "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
        "distance_km": delivery.distance_km or 5.0,
        "estimated_duration": delivery.estimated_duration or 20.0,
        "order": {
            "id": order.id,
            "item_name": order.item.name if order.item else "Package",
            "quantity": order.quantity,
            "total_price": order.total_price,
            "is_cod": order.is_cod,
            "payment_method": "cod" if order.is_cod else "prepaid",
            "prepaid_amount": order.prepaid_amount,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        },
        "customer": {
            "phone": order.customer.phone if order.customer else "—",
            "total_orders": order.customer.total_orders if order.customer else 1,
        },
        "location": {
            "address": order.address,
            "area": area,
            "latitude": order.latitude or 27.6744,
            "longitude": order.longitude or 85.3123,
            "pickup_address": "Balkumari Hub, Lalitpur, Nepal",
            "pickup_latitude": 27.6710,
            "pickup_longitude": 85.3380,
        },
        "risk": {
            "level": risk_val,
            "probability": prob_val,
            "reasons": reasons,
            "shap_factors": shap_factors,
        },
        "rider": {
            "id": rider.id,
            "name": rider.name,
            "phone": rider.phone,
            "current_order_count": rider.current_order_count or 0,
            "max_orders_per_day": rider.max_orders_per_day or 20,
        },
    }


# ============================================================
# RIDER LIFECYCLE ACTION: PICK UP PACKAGE
# ============================================================

@router.post("/deliveries/{delivery_id}/pickup")
def rider_pickup_delivery(
    delivery_id: int,
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Rider acknowledges and picks up the assigned package from the hub.
    Transitions: assigned -> picked_up.
    """
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )

    if delivery.rider_id != rider.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found or not assigned to you.",
        )

    if delivery.status != STATUS_ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pick up delivery in status '{delivery.status}'. Must be '{STATUS_ASSIGNED}'.",
        )

    try:
        res = start_delivery(db=db, delivery_id=delivery_id)
        return {
            "message": "Package successfully picked up from hub.",
            "delivery_id": delivery_id,
            "status": STATUS_PICKED_UP,
            "attempt_count": res.get("attempt_count", 1),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# RIDER LIFECYCLE ACTION: START DELIVERY (OUT FOR DELIVERY)
# ============================================================

@router.post("/deliveries/{delivery_id}/start")
def rider_start_delivery(
    delivery_id: int,
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Rider starts journey toward customer destination.
    Transitions: picked_up -> out_for_delivery.
    """
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )

    if delivery.rider_id != rider.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found or not assigned to you.",
        )

    if delivery.status != STATUS_PICKED_UP:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start delivery from status '{delivery.status}'. Package must be in '{STATUS_PICKED_UP}' status.",
        )

    try:
        res = mark_out_for_delivery(db=db, delivery_id=delivery_id)
        return {
            "message": "Delivery is now out for delivery.",
            "delivery_id": delivery_id,
            "status": STATUS_OUT_FOR_DELIVERY,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# RIDER LIFECYCLE ACTION: MARK DELIVERED (COMPLETE)
# ============================================================

@router.post("/deliveries/{delivery_id}/complete")
def rider_complete_delivery(
    delivery_id: int,
    actual_duration: Optional[float] = Query(None, description="Actual transit duration in minutes"),
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Rider reaches customer and hands over package.
    Transitions: out_for_delivery -> delivered.
    Releases rider workload and updates statistics transactionally.
    """
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )

    if delivery.rider_id != rider.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found or not assigned to you.",
        )

    if delivery.status != STATUS_OUT_FOR_DELIVERY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete delivery from status '{delivery.status}'. Delivery must be '{STATUS_OUT_FOR_DELIVERY}'.",
        )

    try:
        res = complete_delivery(db=db, delivery_id=delivery_id, actual_duration=actual_duration)
        return {
            "message": "Delivery completed successfully!",
            "delivery_id": delivery_id,
            "status": STATUS_DELIVERED,
            "delivered_at": res.get("delivered_at"),
            "rider_workload": rider.current_order_count,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# RIDER LIFECYCLE ACTION: REPORT PROBLEM / FAIL DELIVERY
# ============================================================

@router.post("/deliveries/{delivery_id}/fail")
def rider_fail_delivery(
    delivery_id: int,
    payload: RiderFailRequest,
    rider: Rider = Depends(get_current_rider),
    db: Session = Depends(get_db),
):
    """
    Rider reports a delivery issue with a standardized reason code and operational notes.
    Transitions: picked_up / out_for_delivery -> failed / unreachable.
    Releases rider active workload safely.
    """
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )

    if delivery.rider_id != rider.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found or not assigned to you.",
        )

    if delivery.status not in {STATUS_PICKED_UP, STATUS_OUT_FOR_DELIVERY}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot report failure for delivery in status '{delivery.status}'. Must be active ({STATUS_PICKED_UP} or {STATUS_OUT_FOR_DELIVERY}).",
        )

    code = payload.reason_code.strip().upper()
    if code not in VALID_FAILURE_REASONS:
        valid_keys = list(VALID_FAILURE_REASONS.keys())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid failure reason code '{code}'. Valid options: {valid_keys}",
        )

    reason_info = VALID_FAILURE_REASONS[code]
    notes_clean = (payload.notes or "").strip()

    if reason_info.get("requires_notes") and not notes_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Operational notes are required when reporting '{code}'.",
        )

    formatted_reason = f"{code}: {notes_clean}" if notes_clean else code
    is_unreachable = reason_info.get("unreachable", False)

    try:
        res = fail_delivery(
            db=db,
            delivery_id=delivery_id,
            failure_reason=formatted_reason,
            unreachable=is_unreachable,
        )
        return {
            "message": f"Delivery reported as {res.get('status')}.",
            "delivery_id": delivery_id,
            "status": res.get("status"),
            "failure_reason": formatted_reason,
            "rider_workload": rider.current_order_count,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/failure-reasons")
def get_failure_reasons():
    """
    Return controlled list of valid failure reasons and metadata for rider UI dropdown.
    """
    return [
        {
            "code": code,
            "label": info["label"],
            "unreachable": info["unreachable"],
            "requires_notes": info["requires_notes"],
        }
        for code, info in VALID_FAILURE_REASONS.items()
    ]
