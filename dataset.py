import pandas as pd
import numpy as np
import random

np.random.seed(42)
random.seed(42)

N = 2000
data = []

columns = [
    'delivery_time',
    'address_clarity',
    'address_length',
    'contact_valid',
    'payment_method',
    'order_value',
    'area_density',
    'accessibility',
    'weather_condition',
    'traffic_level',
    'delivery_failure'
]

for _ in range(N):

    delivery_time = random.choice(['morning', 'afternoon', 'evening'])
    address_clarity = random.choice(['clear', 'unclear'])
    address_length = np.random.randint(10, 100)
    contact_valid = random.choice([0, 1])
    payment_method = random.choice(['COD', 'prepaid'])
    order_value = random.choice(['low', 'medium', 'high'])
    area_density = random.choice(['high', 'medium', 'low'])
    accessibility = random.choice(['easy', 'difficult'])
    weather_condition = random.choice(['normal', 'rain', 'extreme'])
    traffic_level = random.choice(['low', 'medium', 'high'])

    # ----------------------------
    # IMPROVED PROBABILITY LOGIC
    # ----------------------------
    risk = 0

    if contact_valid == 0:
        risk += 3
    if address_clarity == 'unclear':
        risk += 2
    if payment_method == 'COD':
        risk += 1
    if accessibility == 'difficult':
        risk += 2
    if weather_condition == 'extreme':
        risk += 3
    if traffic_level == 'high':
        risk += 1
    if order_value == 'high':
        risk += 1
    if delivery_time == 'evening':
        risk += 1

    # Convert risk to probability
    failure = 1 if random.random() < (risk / 10) else 0

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
        failure
    ])

df = pd.DataFrame(data, columns=columns)

df.to_csv('logistics_dataset_kathmandu.csv', index=False)

print("Dataset generated successfully!")
print(df.head())