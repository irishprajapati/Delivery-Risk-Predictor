from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.model import Customer, Delivery


# ============================================================
# CUSTOMER PROFILE HELPERS
# ============================================================

def _get_customer(
    db: Session,
    customer_id: int | None = None,
    phone_number: str | None = None,
) -> Optional[Customer]:
    """
    Find a customer by ID or phone number.

    At least one identifier must be supplied.
    """

    if customer_id is None and not phone_number:
        raise ValueError(
            "customer_id or phone_number is required"
        )

    query = db.query(Customer)

    if customer_id is not None:
        return (
            query
            .filter(Customer.id == customer_id)
            .first()
        )

    return (
        query
        .filter(Customer.phone == phone_number)
        .first()
    )


def _recalculate_customer_history(
    customer: Customer,
) -> None:
    """
    Recalculate derived customer history fields.

    failure_rate is always calculated from actual failed
    deliveries divided by total orders.

    This function never changes total_orders by itself.
    """

    customer.total_orders = int(
        customer.total_orders or 0
    )

    customer.successful_deliveries = int(
        customer.successful_deliveries or 0
    )

    customer.failed_deliveries = int(
        customer.failed_deliveries or 0
    )

    customer.unreachable_count = int(
        customer.unreachable_count or 0
    )

    # Keep the historical counters internally consistent.
    known_outcomes = (
        customer.successful_deliveries
        + customer.failed_deliveries
    )

    # A delivery that is still pending/unassigned does not
    # belong in either successful or failed outcomes.
    #
    # Therefore we do NOT force:
    #
    # total_orders == successful + failed
    #
    # because an order can still be in progress.

    if customer.total_orders > 0:
        customer_failure_rate = (
            customer.failed_deliveries
            / customer.total_orders
        )
    else:
        customer_failure_rate = 0.0

    # No failure_rate column exists on your Customer model,
    # so this value is intentionally not stored here.
    #
    # Feature engineering calculates it from:
    #
    # failed_deliveries / total_orders
    #
    # `known_outcomes` is intentionally calculated above
    # for diagnostics/future use.
    _ = known_outcomes
    _ = customer_failure_rate


# ============================================================
# ORDER CREATED
# ============================================================

def record_order_created(
    db: Session,
    customer_id: int,
) -> Customer:
    """
    Record that a new order has been created.

    IMPORTANT:
    Your current /place-order route already increments
    total_orders.

    Therefore this function should NOT be called from
    the current route_api.py unless that increment is
    moved here.

    It exists as the canonical customer-history operation
    for future refactoring.
    """

    customer = _get_customer(
        db=db,
        customer_id=customer_id,
    )

    if customer is None:
        raise ValueError(
            f"Customer {customer_id} not found"
        )

    customer.total_orders = int(
        customer.total_orders or 0
    ) + 1

    _recalculate_customer_history(
        customer
    )

    return customer


# ============================================================
# DELIVERY SUCCESS
# ============================================================

def record_successful_delivery(
    db: Session,
    delivery: Delivery,
) -> Customer:
    """
    Record an actually completed delivery.

    This must be called only after the delivery is genuinely
    completed, not when the ML model predicts success.
    """

    if delivery is None:
        raise ValueError(
            "delivery is required"
        )

    order = delivery.order

    if order is None:
        raise ValueError(
            "Delivery is not associated with an order"
        )

    customer = order.customer

    if customer is None:
        raise ValueError(
            "Order is not associated with a customer"
        )

    customer.successful_deliveries = int(
        customer.successful_deliveries or 0
    ) + 1

    customer.last_successful_delivery = (
        delivery.delivered_at
    )

    _recalculate_customer_history(
        customer
    )

    return customer


# ============================================================
# DELIVERY FAILURE
# ============================================================

def record_failed_delivery(
    db: Session,
    delivery: Delivery,
) -> Customer:
    """
    Record an actually failed delivery.

    A failure must come from the real delivery lifecycle,
    such as an unsuccessful delivery attempt/final failure.

    It must NOT be triggered by:
        prediction == 1
        probability > 0.7
        risk == HIGH
    """

    if delivery is None:
        raise ValueError(
            "delivery is required"
        )

    order = delivery.order

    if order is None:
        raise ValueError(
            "Delivery is not associated with an order"
        )

    customer = order.customer

    if customer is None:
        raise ValueError(
            "Order is not associated with a customer"
        )

    customer.failed_deliveries = int(
        customer.failed_deliveries or 0
    ) + 1

    _recalculate_customer_history(
        customer
    )

    return customer


# ============================================================
# CUSTOMER UNREACHABLE
# ============================================================

def record_unreachable_customer(
    db: Session,
    delivery: Delivery,
) -> Customer:
    """
    Record an actual customer-unreachable outcome.

    Examples:
        customer did not answer
        phone unreachable
        customer unavailable at delivery location

    This is an actual operational outcome, not an ML prediction.
    """

    if delivery is None:
        raise ValueError(
            "delivery is required"
        )

    order = delivery.order

    if order is None:
        raise ValueError(
            "Delivery is not associated with an order"
        )

    customer = order.customer

    if customer is None:
        raise ValueError(
            "Order is not associated with a customer"
        )

    customer.unreachable_count = int(
        customer.unreachable_count or 0
    ) + 1

    _recalculate_customer_history(
        customer
    )

    return customer


# ============================================================
# COMMIT HELPER
# ============================================================

def save_customer_history(
    db: Session,
    customer: Customer,
) -> Customer:
    """
    Persist a customer-history update.

    Kept separate so outcome handlers can control transaction
    boundaries cleanly.
    """

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    return customer


# ============================================================
# IMPORTANT: NO ML PREDICTION FUNCTION HERE
# ============================================================

def update_customer_profile(
    db: Session,
    phone_number: str,
    prediction: int,
    probability: float,
):
    """
    DEPRECATED.

    Customer history must NEVER be updated from ML predictions.

    This function is intentionally retained temporarily so
    existing imports fail loudly instead of silently corrupting
    customer history.
    """

    raise RuntimeError(
        "update_customer_profile() is deprecated. "
        "Customer history must be updated from actual delivery "
        "outcomes using record_successful_delivery(), "
        "record_failed_delivery(), or "
        "record_unreachable_customer(). "
        "ML predictions must never be stored as delivery outcomes."
    )