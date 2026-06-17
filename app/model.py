import joblib
import pandas as pd
import re

# Load model
model = joblib.load("delivery_model.pkl")

# Expected numerical columns (must match training)
numerical_cols = [
    "address_length",
    "contact_valid"
]


def is_valid_phone(phone: str) -> int:
    pattern = r"^(\+977)?(98[0-9]{8}|97[0-9]{8}|01[0-9]{7})$"
    return 1 if re.match(pattern, phone) else 0

def predict(data):
    try:
        input_dict = data.model_dump()

        input_dict["contact_valid"] = is_valid_phone(input_dict["phone_number"])
        del input_dict["phone_number"]

        df = pd.DataFrame([input_dict])

        prediction = model.predict(df)[0]
        probability = model.predict_proba(df)[0][1]

        if probability > 0.7:
            risk = "HIGH"
        elif probability > 0.4:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        reasons = generate_explanation(input_dict)

        return {
            "success": True,
            "prediction": int(prediction),
            "probability": float(probability),
            "risk": risk,
            "reasons": reasons
        }

    except Exception as e:
        return {
            "success": False,
            "error": "prediction_failed",
            "detail": str(e)
        }

def generate_explanation(input_data):
    reasons = []

    try:
        if input_data["contact_valid"] == 0:
            reasons.append("Invalid phone number")

        if input_data["address_clarity"] == "unclear":
            reasons.append("Address is unclear")

        if input_data["weather_condition"] == "extreme":
            reasons.append("Extreme weather conditions")

        if input_data["traffic_level"] == "high":
            reasons.append("High traffic congestion")

        if input_data["accessibility"] == "difficult":
            reasons.append("Difficult delivery location")

        if input_data["payment_method"] == "COD":
            reasons.append("Cash on Delivery increases risk")

        if input_data["delivery_time"] == "evening":
            reasons.append("Evening deliveries have higher failure chance")

    except Exception:
        reasons.append("Explanation generation failed")

    return reasons

def get_feature_importance():
    try:
        preprocessor = model.named_steps["preprocessor"]
        model_step = model.named_steps["model"]

        cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out()
        num_features = numerical_cols

        all_features = list(cat_features) + list(num_features)

        importances = model_step.feature_importances_

        result = [
            {
                "feature": name,
                "importance": round(float(score), 4)
            }
            for name, score in zip(all_features, importances)
        ]

        result.sort(key=lambda x: x["importance"], reverse=True)

        return result   # ✅ ONLY RAW DATA

    except Exception:
        return None