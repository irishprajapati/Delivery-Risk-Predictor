from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import (
    Category,
    Customer,
    Delivery,
    DeliveryLocation,
    Item,
    Order,
    Prediction,
    Rider,
    RiderAreaPerformance,
    User,
)
from app.schemas import (
    AdminToggleCustomerStatusRequest,
    ChangePasswordRequest,
    CustomerUpdateProfileRequest,
    OrderCreate,
)
from app.utils.security import get_password_hash, verify_password
from app.services.ors_service import (
    LocationValidationError,
    ORSServiceError,
    geocode_address,
    reverse_geocode,
)
from app.services.delivery_service import (
    assign_delivery,
    auto_dispatch_order,
    cancel_delivery,
    complete_delivery,
    fail_delivery,
    get_delivery,
    get_delivery_summary,
    mark_out_for_delivery,
    rank_riders,
    reassign_failed_delivery,
    start_delivery,
)
from app.utils.dependencies import (
    get_current_admin,
    get_current_customer,
    get_current_user,
)

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
# PREDICTION ROUTE RESPONSE
# ============================================================

def _build_route_response(
    prediction: Prediction,
) -> dict:
    """
    Build route information from stored prediction data.

    The prediction service already stores route information
    when a Prediction record exists.
    """

    input_data = prediction.input_data or {}
    route_info = input_data.get("route_info") or {}

    return {
        "prediction_id": prediction.id,

        "phone_number": input_data.get(
            "phone_number",
            "",
        ),

        "pickup_address": input_data.get(
            "pickup_address",
            "",
        ),

        "delivery_address": input_data.get(
            "delivery_address",
            "",
        ),

        "risk": prediction.risk,
        "prediction": prediction.prediction,
        "probability": prediction.probability,

        "estimated_distance_km": route_info.get(
            "estimated_distance_km"
        ),

        "estimated_duration_min": route_info.get(
            "estimated_duration_min"
        ),

        "route_polyline": route_info.get(
            "route_polyline",
            [],
        ),

        "route_source": route_info.get(
            "route_source",
            "heigit_openrouteservice",
        ),

        "pickup_coordinates": route_info.get(
            "pickup_coordinates"
        ),

        "delivery_coordinates": route_info.get(
            "delivery_coordinates"
        ),

        "pickup_district": route_info.get(
            "pickup_district"
        ),

        "delivery_district": route_info.get(
            "delivery_district"
        ),

        "pickup_area": route_info.get(
            "pickup_area"
        ),

        "delivery_area": route_info.get(
            "delivery_area"
        ),

        "created_at": prediction.created_at,
    }


# ============================================================
# LATEST PREDICTION
# ============================================================

def _get_latest_prediction_for_order(
    db: Session,
    order_id: int,
) -> Prediction | None:
    """
    Return the newest persisted prediction for an order.

    Important:
    /predict currently does not persist predictions, so this
    may legitimately return None.
    """

    return (
        db.query(Prediction)
        .filter(
            Prediction.order_id == order_id
        )
        .order_by(
            Prediction.created_at.desc()
        )
        .first()
    )


def _resolve_risk_level(
    db: Session,
    order: Order,
    requested_risk: str | None = None,
) -> str:
    """
    Resolve the risk level used by the dispatch algorithm.

    Priority:

        1. Explicit risk supplied by caller
        2. Latest persisted ML prediction
        3. Order.risk_level if available
        4. MEDIUM neutral fallback

    We deliberately do NOT default to LOW because that would
    make the dispatch engine assume the order is safe when no
    ML result is actually available.
    """

    if requested_risk:
        risk = requested_risk.strip().upper()

        if risk in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            return risk

        raise ValueError(
            "risk_level must be LOW, MEDIUM, or HIGH"
        )

    prediction = _get_latest_prediction_for_order(
        db=db,
        order_id=order.id,
    )

    if prediction and prediction.risk:
        risk = str(
            prediction.risk
        ).strip().upper()

        if risk in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            return risk

    stored_order_risk = getattr(
        order,
        "risk_level",
        None,
    )

    if stored_order_risk:
        risk = str(
            stored_order_risk
        ).strip().upper()

        if risk in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            return risk

    return "MEDIUM"


# ============================================================
# ADMIN ROUTE HISTORY
# ============================================================

@router.get(
    "/route/prediction/{prediction_id}"
)
def get_route_by_prediction_id(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return route information associated with a prediction.

    Admin only.
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    prediction = (
        db.query(Prediction)
        .filter(
            Prediction.id == prediction_id
        )
        .first()
    )

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found",
        )

    return _build_route_response(
        prediction
    )


# ============================================================
# CUSTOMER PROFILE & ORDERS
# ============================================================

def _calculate_customer_rates(
    total_orders: int | None,
    successful_deliveries: int | None,
    failed_deliveries: int | None,
) -> tuple[float, float]:
    """Calculate rounded success and failure percentages."""
    total = int(total_orders or 0)
    success = int(successful_deliveries or 0)
    failed = int(failed_deliveries or 0)

    if total > 0:
        success_rate = round((success / total) * 100.0, 1)
        failure_rate = round((failed / total) * 100.0, 1)
    else:
        success_rate = 100.0 if failed == 0 else 0.0
        failure_rate = 0.0

    return success_rate, failure_rate


def _format_customer_profile(customer: Customer) -> dict:
    """Format full customer profile including system-calculated statistics."""
    success_rate, failure_rate = _calculate_customer_rates(
        customer.total_orders,
        customer.successful_deliveries,
        customer.failed_deliveries,
    )
    return {
        "id": customer.id,
        "phone": customer.phone,
        "is_verified": customer.is_verified,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "total_orders": customer.total_orders or 0,
        "successful_deliveries": customer.successful_deliveries or 0,
        "failed_deliveries": customer.failed_deliveries or 0,
        "unreachable_count": customer.unreachable_count or 0,
        "cancellation_count": customer.cancellation_count or 0,
        "last_successful_delivery": (
            customer.last_successful_delivery.isoformat()
            if customer.last_successful_delivery
            else None
        ),
        "success_rate": success_rate,
        "failure_rate": failure_rate,
    }


def _format_customer_order(order: Order) -> dict:
    delivery = order.delivery
    rider = delivery.rider if delivery else None
    item = order.item
    delivery_status = delivery.status if delivery else (order.status or "placed")

    return {
        "id": order.id,
        "order_id": order.id,
        "item_id": order.item_id,
        "item_name": item.name if item else "Order Item",
        "item_price": item.price if item else order.total_price,
        "quantity": order.quantity,
        "total_price": order.total_price,
        "is_cod": order.is_cod,
        "payment_method": "cod" if order.is_cod else "prepaid",
        "prepaid_amount": order.prepaid_amount,
        "address": order.address,
        "latitude": order.latitude,
        "longitude": order.longitude,
        "order_status": order.status,
        "delivery_status": delivery_status,
        "risk_level": order.risk_level,
        "rider_name": rider.name if rider else None,
        "rider_phone": rider.phone if rider else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.get("/customer/profile")
def customer_profile(
    customer=Depends(get_current_customer),
):
    return _format_customer_profile(customer)


@router.put("/customer/profile")
def update_customer_profile(
    data: CustomerUpdateProfileRequest,
    db: Session = Depends(get_db),
    customer=Depends(get_current_customer),
):
    """
    Update allowed customer account info (e.g. phone).
    Delivery statistics remain strictly system-calculated.
    """
    if data.phone and data.phone != customer.phone:
        existing = (
            db.query(Customer)
            .filter(Customer.phone == data.phone, Customer.id != customer.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This phone number is already registered to another account",
            )
        customer.phone = data.phone
        db.commit()
        db.refresh(customer)

    return {
        "message": "Profile updated successfully",
        "profile": _format_customer_profile(customer),
    }


@router.post("/customer/change-password")
def customer_change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    customer=Depends(get_current_customer),
):
    """
    Secure password change for the authenticated customer.
    """
    if not verify_password(data.current_password, customer.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )

    customer.password_hash = get_password_hash(data.new_password)
    db.commit()

    return {
        "message": "Password changed successfully",
    }


@router.get("/admin/profile")
def admin_profile(
    admin=Depends(get_current_admin),
):
    """
    Return authenticated admin profile details.
    """
    return {
        "id": admin.id,
        "username": admin.username,
        "role": admin.role,
        "is_active": admin.is_active,
    }


@router.post("/admin/change-password")
def admin_change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Secure password change for the authenticated admin.
    """
    if not verify_password(data.current_password, admin.password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )

    admin.password = get_password_hash(data.new_password)
    db.commit()

    return {
        "message": "Admin password changed successfully",
    }


@router.get("/customer/orders")
def get_customer_orders(
    db: Session = Depends(get_db),
    customer=Depends(get_current_customer),
):
    """
    Return all orders placed by the currently logged-in customer.
    """
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return [_format_customer_order(order) for order in orders]


@router.get("/customer/orders/{order_id}")
def get_customer_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    customer=Depends(get_current_customer),
):
    """
    Return specific order detail and delivery status for the customer.
    """
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.customer_id == customer.id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return _format_customer_order(order)


# ============================================================
# ADMIN DASHBOARD & OPERATIONS
# ============================================================

@router.get("/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).all()
    riders = db.query(Rider).order_by(Rider.is_active.desc(), Rider.id).all()

    today = datetime.utcnow().date()
    today_orders_count = sum(1 for o in orders if o.created_at and o.created_at.date() == today)
    if today_orders_count == 0 and len(orders) > 0:
        today_orders_count = len(orders)

    total_orders_count = len(orders)
    total_deliveries_count = len(deliveries)

    unassigned_count = sum(1 for d in deliveries if d.status == "unassigned")
    assigned_count = sum(1 for d in deliveries if d.status == "assigned")
    picked_up_count = sum(1 for d in deliveries if d.status == "picked_up")
    out_for_delivery_count = sum(1 for d in deliveries if d.status == "out_for_delivery")
    delivered_count = sum(1 for d in deliveries if d.status == "delivered")
    failed_unreachable_count = sum(
        1 for d in deliveries if d.status in {"failed", "unreachable", "returned", "cancelled"}
    )
    active_deliveries_count = sum(
        1 for d in deliveries if d.status in {"assigned", "picked_up", "out_for_delivery"}
    )

    high_risk_count = sum(
        1
        for o in orders
        if str(o.risk_level).upper() == "HIGH"
        or (o.predictions and any(str(p.risk).upper() == "HIGH" for p in o.predictions))
    )
    completed_today_count = sum(
        1
        for d in deliveries
        if d.status == "delivered"
        and (
            (d.delivered_at and d.delivered_at.date() == today)
            or (d.created_at and d.created_at.date() == today)
        )
    )
    if completed_today_count == 0:
        completed_today_count = delivered_count

    available_riders_count = sum(
        1 for r in riders if r.is_active and (r.current_order_count or 0) < (r.max_orders_per_day or 20)
    )

    active_ops = []
    for d in deliveries:
        order = d.order
        if not order:
            continue

        area = "Kathmandu"
        for district in ("lalitpur", "kathmandu", "bhaktapur"):
            if district in (order.address or "").lower():
                area = district.capitalize()
                break

        risk = order.risk_level or "LOW"
        probability = None
        reasons = []
        if order.predictions:
            latest_p = sorted(
                order.predictions,
                key=lambda p: p.created_at or datetime.min,
                reverse=True,
            )[0]
            if latest_p.risk:
                risk = str(latest_p.risk).upper()
            probability = latest_p.probability
            if latest_p.input_data and isinstance(latest_p.input_data, dict):
                reasons = latest_p.input_data.get("reasons", [])

        active_ops.append(
            {
                "delivery_id": d.id,
                "order_id": order.id,
                "customer_phone": order.customer.phone if order.customer else "—",
                "area": area,
                "risk": risk,
                "probability": probability,
                "reasons": reasons,
                "rider": d.rider.name if d.rider else None,
                "rider_id": d.rider_id,
                "rider_phone": d.rider.phone if d.rider else None,
                "rider_load": d.rider.current_order_count if d.rider else None,
                "rider_capacity": d.rider.max_orders_per_day if d.rider else None,
                "status": d.status,
                "item_name": order.item.name if order.item else "Package",
                "quantity": order.quantity,
                "total_price": order.total_price,
                "is_cod": order.is_cod,
                "payment_method": "cod" if order.is_cod else "prepaid",
                "address": order.address,
                "assigned_at": d.assigned_at.isoformat() if d.assigned_at else None,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "failure_reason": d.failure_reason,
                "created_at": (
                    d.created_at.isoformat()
                    if d.created_at
                    else (order.created_at.isoformat() if order.created_at else None)
                ),
            }
        )

    riders_summary = [
        {
            "id": r.id,
            "name": r.name,
            "phone": r.phone,
            "area": r.area,
            "is_active": r.is_active,
            "current_order_count": r.current_order_count or 0,
            "max_orders_per_day": r.max_orders_per_day or 20,
            "capacity_remaining": max(0, (r.max_orders_per_day or 20) - (r.current_order_count or 0)),
            "completed_orders": r.completed_orders or 0,
            "failed_deliveries": r.failed_deliveries or 0,
            "is_available": bool(r.is_active and (r.current_order_count or 0) < (r.max_orders_per_day or 20)),
        }
        for r in riders
    ]

    return {
        "message": "Welcome Admin",
        "total_orders": total_orders_count,
        "total_deliveries": total_deliveries_count,
        "today_orders": today_orders_count,
        "new_orders": today_orders_count,
        "unassigned": unassigned_count,
        "assigned": assigned_count,
        "picked_up": picked_up_count,
        "out_for_delivery": out_for_delivery_count,
        "delivered": delivered_count,
        "failed_unreachable": failed_unreachable_count,
        "active_deliveries": active_deliveries_count,
        "high_risk": high_risk_count,
        "completed_today": completed_today_count,
        "available_riders": available_riders_count,
        "total_riders": len(riders),
        "operations": active_ops,
        "riders": riders_summary,
    }


@router.get("/admin/deliveries")
def get_admin_deliveries(
    page: int | None = None,
    limit: int | None = None,
    status: str | None = None,
    risk: str | None = None,
    rider_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Return deliveries with full order details, area, risk, and status.
    Supports optional server-side filtering and pagination.
    """
    deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).all()
    results = []

    for d in deliveries:
        order = d.order
        if not order:
            continue

        area = "Kathmandu"
        for district in ("lalitpur", "kathmandu", "bhaktapur"):
            if district in (order.address or "").lower():
                area = district.capitalize()
                break

        risk_val = order.risk_level or "LOW"
        probability = None
        if order.predictions:
            latest_p = sorted(
                order.predictions,
                key=lambda p: p.created_at or datetime.min,
                reverse=True,
            )[0]
            if latest_p.risk:
                risk_val = str(latest_p.risk).upper()
            probability = latest_p.probability

        results.append(
            {
                "delivery_id": d.id,
                "order_id": order.id,
                "customer_phone": order.customer.phone if order.customer else "—",
                "area": area,
                "address": order.address,
                "latitude": order.latitude,
                "longitude": order.longitude,
                "risk": risk_val,
                "probability": probability,
                "rider_id": d.rider_id,
                "rider_name": d.rider.name if d.rider else None,
                "rider_phone": d.rider.phone if d.rider else None,
                "rider_load": d.rider.current_order_count if d.rider else None,
                "rider_capacity": d.rider.max_orders_per_day if d.rider else None,
                "status": d.status,
                "item_name": order.item.name if order.item else "Package",
                "quantity": order.quantity,
                "total_price": order.total_price,
                "is_cod": order.is_cod,
                "payment_method": "cod" if order.is_cod else "prepaid",
                "prepaid_amount": order.prepaid_amount,
                "assigned_at": d.assigned_at.isoformat() if d.assigned_at else None,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "failure_reason": d.failure_reason,
                "created_at": (
                    d.created_at.isoformat()
                    if d.created_at
                    else (order.created_at.isoformat() if order.created_at else None)
                ),
            }
        )

    # Filtering
    if status and status != "all":
        st = status.lower()
        if st == "active":
            results = [r for r in results if r["status"] in {"assigned", "picked_up", "out_for_delivery"}]
        elif st == "failed":
            results = [r for r in results if r["status"] in {"failed", "unreachable", "returned", "cancelled"}]
        else:
            results = [r for r in results if r["status"] == st]

    if risk and risk != "all":
        rk = risk.upper()
        results = [r for r in results if str(r["risk"]).upper() == rk]

    if rider_id:
        results = [r for r in results if r["rider_id"] == rider_id]

    if search:
        q = search.strip().lower()
        results = [
            r for r in results
            if (
                q in str(r["order_id"]).lower()
                or q in str(r["customer_phone"]).lower()
                or q in str(r["area"]).lower()
                or q in str(r["address"]).lower()
                or q in str(r["rider_name"] or "").lower()
                or q in str(r["item_name"]).lower()
            )
        ]

    # If pagination parameters requested
    if page is not None or limit is not None:
        page_num = max(1, page or 1)
        limit_num = max(1, min(100, limit or 20))
        total_items = len(results)
        total_pages = max(1, (total_items + limit_num - 1) // limit_num)
        offset = (page_num - 1) * limit_num
        paginated_items = results[offset : offset + limit_num]

        return {
            "items": paginated_items,
            "total": total_items,
            "page": page_num,
            "limit": limit_num,
            "total_pages": total_pages,
        }

    return results


@router.get("/admin/riders/{rider_id}")
def get_admin_rider_detail(
    rider_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    area_perfs = (
        db.query(RiderAreaPerformance)
        .filter(RiderAreaPerformance.rider_id == rider_id)
        .all()
    )
    area_list = [
        {
            "area": ap.area,
            "total_deliveries": ap.total_deliveries,
            "successful_deliveries": ap.successful_deliveries,
            "failed_deliveries": ap.failed_deliveries,
            "success_rate": round(ap.success_rate, 4),
        }
        for ap in area_perfs
    ]

    active_deliveries = [
        {
            "delivery_id": d.id,
            "order_id": d.order_id,
            "status": d.status,
            "address": d.order.address if d.order else "",
            "item_name": d.order.item.name if (d.order and d.order.item) else "Package",
        }
        for d in rider.deliveries
        if d.status in {"assigned", "picked_up", "out_for_delivery"}
    ]

    total_completed = (rider.completed_orders or 0) + (rider.failed_deliveries or 0)
    success_rate = (
        rider.completed_orders / total_completed
        if total_completed > 0
        else 0.50
    )

    return {
        "id": rider.id,
        "name": rider.name,
        "phone": rider.phone,
        "area": rider.area,
        "is_active": rider.is_active,
        "max_orders_per_day": rider.max_orders_per_day or 20,
        "current_order_count": rider.current_order_count or 0,
        "completed_orders": rider.completed_orders or 0,
        "failed_deliveries": rider.failed_deliveries or 0,
        "overall_success_rate": round(success_rate, 4),
        "current_latitude": rider.current_latitude,
        "current_longitude": rider.current_longitude,
        "last_location_update": (
            rider.last_location_update.isoformat()
            if rider.last_location_update
            else None
        ),
        "area_performances": area_list,
        "active_deliveries": active_deliveries,
    }


@router.get("/admin/customers")
def get_admin_customers(
    search: str | None = None,
    is_verified: bool | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    query = db.query(Customer)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Customer.phone.ilike(s))

    if is_verified is not None:
        query = query.filter(Customer.is_verified == is_verified)

    customers = query.order_by(Customer.id.asc()).all()
    return [_format_customer_profile(c) for c in customers]


@router.get("/admin/customers/{customer_id}")
def get_admin_customer_detail(
    customer_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    formatted_orders = [_format_customer_order(order) for order in orders]
    profile_data = _format_customer_profile(customer)
    profile_data["orders"] = formatted_orders

    return profile_data


@router.patch("/admin/customers/{customer_id}/status")
def update_admin_customer_status(
    customer_id: int,
    data: AdminToggleCustomerStatusRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    customer.is_verified = data.is_verified
    db.commit()
    db.refresh(customer)

    status_str = "activated" if customer.is_verified else "deactivated"
    return {
        "message": f"Customer account {status_str} successfully",
        "customer": _format_customer_profile(customer),
    }


# ============================================================
# CATEGORIES
# ============================================================

@router.get(
    "/categories"
)
def get_categories(
    db: Session = Depends(get_db),
):
    return (
        db.query(Category)
        .order_by(Category.id)
        .all()
    )


# ============================================================
# ITEMS BY CATEGORY
# ============================================================

@router.get(
    "/items/{category_id}"
)
def get_items_by_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Item)
        .filter(
            Item.category_id == category_id
        )
        .order_by(Item.id)
        .all()
    )


# ============================================================
# ALL ITEMS
# ============================================================

@router.get(
    "/items"
)
def get_all_items(
    db: Session = Depends(get_db),
):
    items = (
        db.query(Item)
        .order_by(Item.id)
        .all()
    )

    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "category_id": item.category_id,
            "category": (
                item.category.name
                if item.category
                else None
            ),
        }
        for item in items
    ]


# ============================================================
# ORDER LOCATION RESOLUTION
# ============================================================

def _resolve_order_location(
    address: str,
    latitude: float | None,
    longitude: float | None,
) -> dict:
    """
    Resolve an order location.

    Preferred:
        map coordinates supplied by frontend

    Fallback:
        address geocoding

    The customer does NOT need to know latitude/longitude.
    The frontend/map supplies them.
    """

    # --------------------------------------------------------
    # MAP PIN
    # --------------------------------------------------------

    if (
        latitude is not None
        and longitude is not None
    ):
        try:
            location = reverse_geocode(
                latitude=float(latitude),
                longitude=float(longitude),
            )

        except LocationValidationError:
            raise

        except ORSServiceError:
            # Fallback to local district inference if external OSM Nominatim is down or rate-limited
            district = "Kathmandu"
            addr_lower = (address or "").lower()
            if "lalitpur" in addr_lower:
                district = "Lalitpur"
            elif "bhaktapur" in addr_lower:
                district = "Bhaktapur"

            location = {
                "lat": float(latitude),
                "lng": float(longitude),
                "district": district,
                "matched_area": district,
                "label": address or f"Location ({latitude}, {longitude})",
                "confidence": 0.8,
            }

        return {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "district": location["district"],
            "area": location.get(
                "matched_area"
            ),
            "label": location.get(
                "label"
            ),
            "confidence": location.get(
                "confidence"
            ),
            "location_source": "map_pin",
            "input_address": address,
        }

    # --------------------------------------------------------
    # ADDRESS GEOCODING
    # --------------------------------------------------------

    if not address:
        raise LocationValidationError(
            "Delivery address is required "
            "when map coordinates are not provided."
        )

    try:
        location = geocode_address(
            address
        )

    except LocationValidationError:
        raise

    except ORSServiceError:
        raise

    return {
        "latitude": location["lat"],
        "longitude": location["lng"],
        "district": location["district"],
        "area": location.get(
            "matched_area"
        ),
        "label": location.get(
            "label"
        ),
        "confidence": location.get(
            "confidence"
        ),
        "location_source": "address_geocoding",
        "input_address": address,
    }


# ============================================================
# PLACE ORDER
# ============================================================

@router.post(
    "/place-order"
)
def place_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_customer),
):
    """
    Create a customer order and its initial delivery records.

    Flow:

        Request
            ↓
        Pydantic validation
            ↓
        Item validation
            ↓
        Payment validation
            ↓
        Location resolution
            ↓
        Order creation
            ↓
        DeliveryLocation creation
            ↓
        Delivery creation
            ↓
        Customer order-count update
            ↓
        Atomic commit

    This endpoint does NOT:

        - calculate the ML prediction
        - calculate a second risk score
        - assign a rider
        - mark delivery successful
        - mark delivery failed
    """

    # ========================================================
    # ITEM
    # ========================================================

    item = (
        db.query(Item)
        .filter(
            Item.id == data.item_id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )

    # ========================================================
    # QUANTITY
    # ========================================================

    quantity = int(
        data.quantity
    )

    if quantity <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "Quantity must be greater "
                "than zero"
            ),
        )

    # ========================================================
    # TOTAL PRICE
    # ========================================================

    total_price = round(
        float(item.price)
        * quantity,
        2,
    )

    if total_price <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "Calculated order value "
                "must be greater than zero"
            ),
        )

    # ========================================================
    # PAYMENT
    # ========================================================

    payment_method = (
        data.payment_method
        .strip()
        .lower()
    )

    is_cod = (
        payment_method == "cod"
    )

    prepaid_amount = round(
        float(
            data.prepaid_amount
        ),
        2,
    )

    if prepaid_amount < 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "prepaid_amount cannot "
                "be negative"
            ),
        )

    if prepaid_amount > total_price:
        raise HTTPException(
            status_code=422,
            detail=(
                "prepaid_amount cannot "
                "exceed order value"
            ),
        )

    if (
        is_cod
        and prepaid_amount > 0
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "COD orders cannot have "
                "a prepaid amount"
            ),
        )

    if (
        not is_cod
        and prepaid_amount <= 0
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Prepaid orders must have "
                "a prepaid amount greater "
                "than zero"
            ),
        )

    # ========================================================
    # ADDRESS
    # ========================================================

    address = (
        data.address or ""
    ).strip()

    if not address:
        raise HTTPException(
            status_code=422,
            detail="Address must not be empty",
        )

    # ========================================================
    # LOCATION
    # ========================================================

    try:
        location = _resolve_order_location(
            address=address,
            latitude=data.latitude,
            longitude=data.longitude,
        )

    except LocationValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ORSServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    resolved_latitude = float(
        location["latitude"]
    )

    resolved_longitude = float(
        location["longitude"]
    )

    resolved_label = location.get(
        "label"
    )

    resolved_district = location.get(
        "district"
    )

    location_source = location[
        "location_source"
    ]

    # ========================================================
    # ORDER
    # ========================================================

    order = Order(
        customer_id=current.id,
        item_id=item.id,
        quantity=quantity,
        total_price=total_price,
        is_cod=is_cod,
        prepaid_amount=prepaid_amount,
        address=address,
        latitude=resolved_latitude,
        longitude=resolved_longitude,
        risk_score=None,
        risk_level=None,
        status="placed",
    )

    db.add(order)
    db.flush()

    # ========================================================
    # DELIVERY LOCATION
    # ========================================================

    delivery_location = DeliveryLocation(
        order_id=order.id,

        address=(
            resolved_label
            or address
        ),

        latitude=resolved_latitude,
        longitude=resolved_longitude,

        address_quality=None,
        distance_km=None,
        estimated_duration=None,
        location_success_rate=None,
    )

    db.add(
        delivery_location
    )

    # ========================================================
    # DELIVERY
    # ========================================================

    delivery = Delivery(
        order_id=order.id,
        rider_id=None,
        status="unassigned",
        attempt_count=0,
        failure_reason=None,
        distance_km=None,
        estimated_duration=None,
        actual_duration=None,
        assigned_at=None,
        delivered_at=None,
    )

    db.add(
        delivery
    )

    # ========================================================
    # CUSTOMER HISTORY
    # ========================================================

    db_customer = db.query(Customer).filter(Customer.id == current.id).first()
    if db_customer:
        db_customer.total_orders = int(db_customer.total_orders or 0) + 1
    else:
        current.total_orders = int(current.total_orders or 0) + 1
        db.add(current)

    # Do NOT update success/failure counters here.
    # The delivery has not happened yet.

    # ========================================================
    # COMMIT PHASE 1 (ORDER & INITIAL DELIVERY RECORDS)
    # ========================================================

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    db.refresh(
        delivery_location
    )
    db.refresh(delivery)

    # ========================================================
    # PHASE 2: AUTOMATIC ML PREDICTION & RIDER DISPATCH
    # ========================================================

    dispatch_result = auto_dispatch_order(
        db=db,
        order_id=order.id,
        delivery_id=delivery.id,
    )

    try:
        db.refresh(order)
        db.refresh(delivery)
    except Exception:
        pass

    return {
        "message": (
            "Order placed and automatically dispatched to rider."
            if delivery.status == "assigned"
            else "Order placed successfully. Awaiting available rider."
        ),

        "order_id": order.id,

        "delivery_id": delivery.id,

        "delivery_location_id": (
            delivery_location.id
        ),

        "customer_id": current.id,

        "item": {
            "id": item.id,
            "name": item.name,
            "price": item.price,
        },

        "quantity": order.quantity,

        "total_price": order.total_price,

        "payment_method": payment_method,

        "is_cod": order.is_cod,

        "prepaid_amount": (
            order.prepaid_amount
        ),

        "address": order.address,

        "coordinates": {
            "latitude": order.latitude,
            "longitude": order.longitude,
        },

        "location": {
            "source": location_source,
            "label": resolved_label,
            "district": resolved_district,
        },

        "order_status": order.status,

        "delivery_status": (
            delivery.status
        ),

        "assigned_rider_id": (
            delivery.rider_id
        ),

        "risk_level": (
            order.risk_level
        ),

        "risk_score": (
            order.risk_score
        ),

        "message_next_step": (
            f"Rider {delivery.rider_id} assigned automatically."
            if delivery.status == "assigned"
            else "Delivery will be assigned as soon as an eligible rider becomes available."
        ),
    }


# ============================================================
# RIDER OPTIONS
# ============================================================

@router.get(
    "/admin/deliveries/{delivery_id}/rider-options"
)
def get_delivery_rider_options(
    delivery_id: int,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Return ranked eligible riders.

    This does NOT assign anyone.

    It is intended for:
        - admin dashboard
        - debugging
        - explaining why one rider ranks above another
    """

    try:
        delivery = get_delivery(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if delivery.status not in {
        "unassigned",
        "failed",
        "unreachable",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Rider options are not available "
                f"for delivery status '{delivery.status}'."
            ),
        )

    if delivery.order is None:
        raise HTTPException(
            status_code=500,
            detail="Delivery is not linked to an order.",
        )

    try:
        resolved_risk = _resolve_risk_level(
            db=db,
            order=delivery.order,
            requested_risk=risk_level,
        )

        candidates = rank_riders(
            db=db,
            delivery_id=delivery.id,
            risk_level=resolved_risk,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to calculate rider candidates"
            ),
        )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "risk_level": resolved_risk,
        "assignment_algorithm": (
            "risk_aware_multi_criteria_ranking"
        ),
        "candidate_count": len(
            candidates
        ),
        "candidates": candidates,
    }


# ============================================================
# ASSIGN RIDER
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/assign"
)
def assign_delivery_rider(
    delivery_id: int,
    rider_id: int | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Assign a rider.

    rider_id omitted:
        automatic best-rider selection

    rider_id supplied:
        manual rider selection

    ML and dispatch remain separate:

        ML -> predicts failure risk
        Dispatch -> selects operational rider
    """

    try:
        delivery = get_delivery(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if delivery.order is None:
        raise HTTPException(
            status_code=500,
            detail="Delivery is not linked to an order.",
        )

    if delivery.status not in {
        "unassigned",
        "assigned",
        "failed",
        "unreachable",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Delivery cannot be assigned "
                f"from status '{delivery.status}'."
            ),
        )

    try:
        resolved_risk = _resolve_risk_level(
            db=db,
            order=delivery.order,
            requested_risk=risk_level,
        )

        result = assign_delivery(
            db=db,
            delivery_id=delivery.id,
            rider_id=rider_id,
            risk_level=resolved_risk,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Rider assignment service failed",
        )

    return {
        "message": (
            "Rider assigned successfully"
            if rider_id is None
            else "Rider manually assigned successfully"
        ),

        "delivery_id": delivery.id,

        "order_id": delivery.order_id,

        "risk_level": resolved_risk,

        "selection_mode": (
            "manual"
            if rider_id is not None
            else "automatic"
        ),

        "assignment": result,
    }


# ============================================================
# START DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/start"
)
def start_delivery_attempt(
    delivery_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    assigned -> picked_up
    """

    try:
        result = start_delivery(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to start delivery",
        )

    return result


# ============================================================
# OUT FOR DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/out-for-delivery"
)
def delivery_out_for_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    picked_up -> out_for_delivery
    """

    try:
        delivery = mark_out_for_delivery(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to mark delivery "
                "out for delivery"
            ),
        )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "rider_id": delivery.rider_id,
        "status": delivery.status,
        "message": (
            "Delivery is now out for delivery."
        ),
    }


# ============================================================
# COMPLETE DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/complete"
)
def complete_delivery_endpoint(
    delivery_id: int,
    actual_duration: float | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Complete a real successful delivery.

    This updates:

        rider completed count
        customer successful deliveries
        customer last successful delivery
        rider-area performance
        rider workload
        delivery timestamp
    """

    try:
        result = complete_delivery(
            db=db,
            delivery_id=delivery_id,
            actual_duration=actual_duration,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to complete delivery",
        )

    return result


# ============================================================
# FAIL DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/fail"
)
def fail_delivery_endpoint(
    delivery_id: int,
    failure_reason: str,
    unreachable: bool = False,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Record a real failed/unreachable delivery attempt.

    Example:

        unreachable=false
        failure_reason="Customer rejected package"

    or:

        unreachable=true
        failure_reason="Customer did not answer"
    """

    if not failure_reason.strip():
        raise HTTPException(
            status_code=422,
            detail="failure_reason is required",
        )

    try:
        result = fail_delivery(
            db=db,
            delivery_id=delivery_id,
            failure_reason=failure_reason,
            unreachable=unreachable,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to record delivery failure",
        )

    return result


# ============================================================
# REASSIGN FAILED DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/reassign"
)
def reassign_delivery_endpoint(
    delivery_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Reassign a failed/unreachable delivery.

    The previous rider is excluded from immediate
    automatic selection.
    """

    try:
        result = reassign_failed_delivery(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to reassign delivery",
        )

    return result


# ============================================================
# CANCEL DELIVERY
# ============================================================

@router.post(
    "/admin/deliveries/{delivery_id}/cancel"
)
def cancel_delivery_endpoint(
    delivery_id: int,
    reason: str = (
        "Cancelled by customer or operations"
    ),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Cancel a delivery.

    Rider workload is released by the delivery service.
    """

    try:
        delivery = cancel_delivery(
            db=db,
            delivery_id=delivery_id,
            reason=reason,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to cancel delivery",
        )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "status": delivery.status,
        "failure_reason": delivery.failure_reason,
        "message": (
            "Delivery cancelled successfully."
        ),
    }


# ============================================================
# DELIVERY SUMMARY
# ============================================================

@router.get(
    "/admin/deliveries/{delivery_id}"
)
def get_delivery_details(
    delivery_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Return complete delivery + rider + location information.

    Designed for the future admin dashboard.
    """

    try:
        return get_delivery_summary(
            db=db,
            delivery_id=delivery_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to load delivery summary",
        )


# ============================================================
# RIDER LIST
# ============================================================

@router.get(
    "/admin/riders"
)
def get_riders(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Return rider operational information for
    the admin dashboard.
    """

    riders = (
        db.query(Rider)
        .order_by(
            Rider.is_active.desc(),
            Rider.id,
        )
        .all()
    )

    result = []

    for rider in riders:

        max_orders = (
            rider.max_orders_per_day
            or 0
        )

        current_orders = (
            rider.current_order_count
            or 0
        )

        completed_orders = (
            rider.completed_orders
            or 0
        )

        failed_deliveries = (
            rider.failed_deliveries
            or 0
        )

        total_completed_attempts = (
            completed_orders
            + failed_deliveries
        )

        success_rate = (
            completed_orders
            / total_completed_attempts
            if total_completed_attempts > 0
            else 0.50
        )

        result.append(
            {
                "id": rider.id,
                "name": rider.name,
                "phone": rider.phone,
                "area": rider.area,

                "is_active": rider.is_active,

                "max_orders_per_day": (
                    max_orders
                ),

                "current_order_count": (
                    current_orders
                ),

                "capacity_remaining": max(
                    max_orders
                    - current_orders,
                    0,
                ),

                "completed_orders": (
                    completed_orders
                ),

                "failed_deliveries": (
                    failed_deliveries
                ),

                "overall_success_rate": round(
                    success_rate,
                    4,
                ),

                "current_latitude": getattr(
                    rider,
                    "current_latitude",
                    None,
                ),

                "current_longitude": getattr(
                    rider,
                    "current_longitude",
                    None,
                ),

                "last_location_update": getattr(
                    rider,
                    "last_location_update",
                    None,
                ),
            }
        )

    return result


# ============================================================
# CREATE ITEM
# ============================================================

@router.post(
    "/create-item"
)
def create_item(
    name: str,
    price: float,
    category_name: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Create an item.

    Admin only.
    """

    name = (
        name or ""
    ).strip()

    category_name = (
        category_name or ""
    ).strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail=(
                "Item name must not be empty"
            ),
        )

    if price <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "Item price must be greater "
                "than zero"
            ),
        )

    category = (
        db.query(Category)
        .filter(
            Category.name
            == category_name
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail="Invalid category",
        )

    item = Item(
        name=name,
        price=price,
        category_id=category.id,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Item created",
        "item_id": item.id,
        "category": category.name,
    }