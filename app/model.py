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
            "prediction": int(prediction),
            "probability": float(probability),
            "risk": risk,
            "reasons": reasons
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def generate_explanation(input_data):
    reasons = []

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

    return reasons


def get_feature_importance():
    try:
        # Check if model is a pipeline
        if hasattr(model, "named_steps"):
            model_step = model.named_steps["model"]
            preprocessor = model.named_steps["preprocessor"]

            cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out()
            num_features = numerical_cols

            all_features = list(cat_features) + list(num_features)
            importances = model_step.feature_importances_

        else:
            # Fallback if not a pipeline
            all_features = model.feature_names_in_
            importances = model.feature_importances_

        feature_importance = [
            {"feature": name, "importance": float(score)}
            for name, score in zip(all_features, importances)
        ]

        # Sort descending
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)

        return feature_importance

    except Exception as e:
        return {
            "error": str(e)
        }