from app.model import Order
from datetime import datetime, timedelta
def generate_actions(input_data: dict, prediction: int, probability: float):
    actions = []

    if probability >= 0.4:
        actions.append("Call customer before dispatch")

        if input_data.get("payment_method") == "COD":
            actions.append("Switch to prepaid if possible")

        if input_data.get("address_clarity") == "low":
            actions.append("Ask for clearer address or map pin")

        if input_data.get("area_density") == "high":
            actions.append("Assign rider familiar with dense urban routes")

        if probability > 0.75:
            actions.append("Assign experienced delivery rider")
    else:
        actions.append("Proceed with standard delivery flow")
        actions.append("Send automated delivery notification to customer")

    return actions

def calculate_address_score(address):
    score = 0

    if len(address) > 20:
        score += 0.3

    if any(word in address.lower() for word in ["road", "street", "ward", "area"]):
        score += 0.3

    if any(char.isdigit() for char in address):
        score += 0.2

    return min(score, 1.0)

def calculate_risk(
    db,
    customer,
    item,
    quantity,
    total_price,
    is_cod,
    address_text
):
    failed = customer.failed_deliveries or 0
    unreachable = getattr(customer, "unreachable_count", 0) or 0

    risk = 0

    if quantity > 20:
        risk += 0.15
    elif quantity > 10:
        risk += 0.10
    elif quantity > 5:
        risk += 0.05

    if total_price > 50000:
        risk += 0.2
    elif total_price > 10000:
        risk += 0.1
    elif total_price > 3000:
        risk += 0.05

    if item.price > 50000:
        risk += 0.1

    # Category Risk (NEW SYSTEM)
    if item.category and item.category.risk_score:
        risk += item.category.risk_score

    if getattr(customer, "total_orders", 0) == 0:
        risk += 0.1

    current_hour = datetime.utcnow().hour
    if 2 <= current_hour <= 5:
        risk += 0.05

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    recent_orders = db.query(Order).filter(
        Order.customer_id == customer.id,
        Order.created_at >= one_hour_ago
    ).count()

    if recent_orders > 6:
        risk += 0.15
    elif recent_orders > 3:
        risk += 0.1

    if failed > 5:
        risk += 0.2
    elif failed > 2:
        risk += 0.1
    if is_cod:
        if failed > 2:
            risk += 0.1
        else:
            risk += 0.05

    address_score = calculate_address_score(address_text)

    if address_score < 0.3:
        risk += 0.1
    elif address_score < 0.6:
        risk += 0.05

    if unreachable > 5:
        risk += 0.1
    elif unreachable > 2:
        risk += 0.05

    print({
        "customer": customer.id,
        "risk": risk,
        "price": total_price,
        "quantity": quantity,
        "recent_orders": recent_orders,
        "category": item.category.name if item.category else None
    })

    return round(min(risk, 1.0), 2)