import pandas as pd
import numpy as np
import random

np.random.seed(42)
random.seed(42)

N = 2000
data = []

columns = [
    "delivery_time",
    "address_clarity",
    "address_length",
    "contact_valid",
    "payment_method",
    "order_value",
    "area_density",
    "accessibility",
    "weather_condition",
    "traffic_level",
    "distance_proxy",
    "customer_type",
    "area_risk_level",
    "congestion_risk",

    "delivery_failure"
]

for _ in range(N):
    delivery_time = random.choice(["morning", "afternoon", "evening"])
    address_clarity = random.choice(["clear", "unclear"])
    address_length = np.random.randint(10, 100)
    contact_valid = random.choice([0, 1])
    payment_method = random.choice(["COD", "prepaid"])
    order_value = random.choice(["low", "medium", "high"])
    area_density = random.choice(["high", "medium", "low"])
    accessibility = random.choice(["easy", "difficult"])
    weather_condition = random.choice(["normal", "rain", "extreme"])
    traffic_level = random.choice(["low", "medium", "high"])

    distance_proxy = random.choice(["core", "suburban", "outer"])
    customer_type = random.choice(["new", "returning"])
    risk = 0

    # Base rules
    if contact_valid == 0:
        risk += 3

    if address_clarity == "unclear":
        risk += 2

    if payment_method == "COD":
        risk += 1

    if accessibility == "difficult":
        risk += 2

    if weather_condition == "extreme":
        risk += 3

    if traffic_level == "high":
        risk += 1

    if order_value == "high":
        risk += 1

    if delivery_time == "evening":
        risk += 1

    if distance_proxy == "suburban":
        risk += 1
    elif distance_proxy == "outer":
        risk += 3
        risk += 1 if accessibility == "difficult" else 0

    if customer_type == "new":
        risk += 2
        if random.random() < 0.3:
            address_clarity = "unclear"
        if random.random() < 0.2:
            contact_valid = 0

    area_risk_level = "low"

    if distance_proxy == "core":
        area_risk_level = "low"
    elif distance_proxy == "suburban":
        area_risk_level = "medium"
    else:
        area_risk_level = "high"

    if area_risk_level == "high":
        risk += 2

    congestion_risk = "low"

    if traffic_level == "high" or delivery_time == "evening":
        congestion_risk = "high"
    elif traffic_level == "medium":
        congestion_risk = "medium"

    if congestion_risk == "high":
        risk += 1
    failure_probability = min(risk / 12, 0.95)
    delivery_failure = 1 if random.random() < failure_probability else 0

    data.append([
        delivery_time,
        address_clarity,
        address_length,
        contact_valid,
        payment_method,
        order_value,
        area_density,
        accessibility,
        weather_condition,
        traffic_level,

        distance_proxy,
        customer_type,
        area_risk_level,
        congestion_risk,

        delivery_failure
    ])

df = pd.DataFrame(data, columns=columns)

df.to_csv("logistics_dataset_kathmandu.csv", index=False)

print("Dataset generated successfully (REALISTIC VERSION)")
print(df.head())