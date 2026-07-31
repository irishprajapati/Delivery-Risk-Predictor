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
