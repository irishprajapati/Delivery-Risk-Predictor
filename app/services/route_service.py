import requests
import os
import pickle
import joblib
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ORS_API_KEY")

if not API_KEY:
    raise Exception("ORS_API_KEY not found in .env file")


# ✅ Load ML model ONCE (not per request)
MODEL_PATH = "app/ml/delivery_model.pkl"

if not os.path.exists(MODEL_PATH):
    raise Exception("ML model not found. Train and save model first.")

ml_model = joblib.load(MODEL_PATH)

# ✅ OPTIONAL fallback
KNOWN_LOCATIONS = {
    "lokanthali": [85.373, 27.673],
    "jawalakhel": [85.314, 27.673],
    "bhaktapur": [85.4298, 27.6710],
    "lalitpur": [85.3240, 27.6588]
}


# ---------------- ML LOGIC ---------------- #

def is_peak_hour(hour):
    return 1 if (8 <= hour <= 10 or 17 <= hour <= 19) else 0


def predict_ml_time(distance_km):
    now = datetime.now()
    hour = now.hour
    day = now.weekday()
    peak = is_peak_hour(hour)

    features = np.array([[distance_km, hour, day, peak]])
    prediction = ml_model.predict(features)[0]

    return round(prediction, 2)


# ---------------- GEO VALIDATION ---------------- #

def is_valid_coordinate(coords):
    lon, lat = coords

    if coords == [85.9, 27.15]:
        return False

    if not (80 < lon < 90 and 25 < lat < 31):
        return False

    return True


def is_routable(coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [coords, coords]
    }

    response = requests.post(url, json=body, headers=headers)
    return response.status_code == 200


# ---------------- GEOCODING ---------------- #

def geocode(address: str):
    address_clean = address.strip().lower()

    url = "https://api.openrouteservice.org/geocode/search"

    params = {
        "api_key": API_KEY,
        "text": address,
        "size": 5,
        "boundary.country": "NP"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()

        try:
            for feature in data["features"]:
                coords = feature["geometry"]["coordinates"]

                if not is_valid_coordinate(coords):
                    continue

                if is_routable(coords):
                    print(f"[INFO] API success → {address}: {coords}")
                    return coords

        except (KeyError, IndexError):
            pass

    if address_clean in KNOWN_LOCATIONS:
        print(f"[FALLBACK] Using known location for {address}")
        return KNOWN_LOCATIONS[address_clean]

    raise Exception(f"Invalid or unknown location: {address}")


# ---------------- MAIN FUNCTION ---------------- #
print("ROUTE FUNCTION HIT ")
def get_route_data(pickup: str, delivery: str) -> dict:
    pickup_coords = geocode(pickup)
    delivery_coords = geocode(delivery)

    print(f"[DEBUG] Pickup coords: {pickup_coords}")
    print(f"[DEBUG] Delivery coords: {delivery_coords}")

    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [pickup_coords, delivery_coords]
    }

    response = requests.post(url, json=body, headers=headers)

    print(f"[DEBUG] ORS status: {response.status_code}")

    if response.status_code != 200:
        print("[ERROR RESPONSE]", response.text)
        raise Exception(f"Route API error: {response.status_code}")

    data = response.json()

    # 🔴 DEBUG: Raw response (first 500 chars only)
    print("[DEBUG] RAW ORS RESPONSE (truncated):")
    print(str(data)[:500])

    try:
        summary = data["features"][0]["properties"]["summary"]

        distance_m = summary["distance"]
        duration_sec = summary["duration"]

        distance_km = round(distance_m / 1000, 2)
        api_duration = round(duration_sec / 60, 2)

        # 🔥 CRITICAL DEBUG (THIS IS WHAT YOU CARE ABOUT)
        speed_mps = distance_m / duration_sec if duration_sec > 0 else 0
        speed_kmph = speed_mps * 3.6

        print(f"[DEBUG] Distance (m): {distance_m}")
        print(f"[DEBUG] Duration (sec): {duration_sec}")
        print(f"[DEBUG] Speed (m/s): {round(speed_mps, 2)}")
        print(f"[DEBUG] Speed (km/h): {round(speed_kmph, 2)}")

        # 🔥 TRAFFIC CLASSIFICATION DEBUG
        if speed_mps < 5:
            traffic = "HIGH"
        elif speed_mps < 10:
            traffic = "MEDIUM"
        else:
            traffic = "LOW"

        print(f"[DEBUG] Derived traffic level: {traffic}")
        return {
        "distance_km": distance_km,
        "api_duration_min": api_duration,
        "debug_speed_kmph": round(speed_kmph, 2),
        "derived_traffic": traffic
        }

    except (KeyError, IndexError):
        raise Exception("Failed to parse route data")