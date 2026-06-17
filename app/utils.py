def explain_risk(data):
    reasons = []

    if data.contact_valid == 0:
        reasons.append("Customer unreachable")

    if data.weather_condition == "extreme":
        reasons.append("Extreme weather")

    if data.accessibility == "difficult":
        reasons.append("Difficult location access")

    return reasons