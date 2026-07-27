def generate_actions(input_data: dict, prediction: int, probability: float):
    actions = []

    # 🔥 HIGH + MEDIUM RISK ACTIONS
    if probability >= 0.4:

        actions.append("Call customer before dispatch")

        if input_data.get("payment_method") == "COD":
            actions.append("Switch to prepaid if possible")

        if input_data.get("traffic_level") == "high":
            actions.append("Avoid peak traffic time")

        if input_data.get("address_clarity") in ["unclear", "bad"]:
            actions.append("Ask for clearer address or map pin")

        if probability > 0.75:
            actions.append("Assign experienced delivery rider")

    # 🔥 LOW RISK → BASIC OPTIMIZATION (NEW)
    else:
        actions.append("Proceed with standard delivery flow")
        actions.append("Send automated delivery notification to customer")

    return actions