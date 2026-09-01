import re
def normalize_name(name: str):
    name = name.lower()
    name = re.sub(r'[^a-z0-9]', '', name)  # remove spaces, hyphens, etc.
    return name

def explain_risk(data):
    reasons = []

    if data.contact_valid == 0:
        reasons.append("Customer unreachable")

    if data.weather_condition == "extreme":
        reasons.append("Extreme weather")

    if data.accessibility == "difficult":
        reasons.append("Difficult location access")

    return reasons