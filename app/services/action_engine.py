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
    risk = 0

    # ✅ Normalize bad DB values
    failed = customer.failed_deliveries or 0
    unreachable = getattr(customer, "unreachable_count", 0) or 0

    # Quantity
    if quantity > 5:
        risk += 0.15
    if quantity > 10:
        risk += 0.25

    # Price
    if total_price > 1000:
        risk += 0.2
    if total_price > 5000:
        risk += 0.3

    # Recent orders
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_orders = db.query(Order).filter(
        Order.customer_id == customer.id,
        Order.created_at >= one_hour_ago
    ).count()

    if recent_orders > 3:
        risk += 0.15
    if recent_orders > 6:
        risk += 0.25

    # Failed deliveries
    if failed > 2:
        risk += 0.2
    if failed > 5:
        risk += 0.35

    # COD risk
    if is_cod:
        risk += 0.15
        if failed > 2:
            risk += 0.25

    # Address risk
    address_score = calculate_address_score(address_text)
    if address_score < 0.5:
        risk += 0.2

    # Unreachable risk
    if unreachable > 2:
        risk += 0.2

    return min(risk, 1.0)