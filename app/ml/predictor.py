import joblib
import pandas as pd
import re
import shap
from pathlib import Path
from typing import Dict, Any, List

# ==============================
# CONFIG
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "delivery_model.pkl"
model = joblib.load(MODEL_PATH)

preprocessor = model.named_steps["preprocessor"]
model_step = model.named_steps["model"]
print("TRANSFORMERS STRUCTURE:")
print(preprocessor.transformers_)

print("ORDER CHECK:")
for name, transformer, cols in preprocessor.transformers_:
    print(name)
explainer = shap.TreeExplainer(model_step)

EXPECTED_COLUMNS = [
    "delivery_time",
    "address_clarity",
    "payment_method",
    "order_value",
    "area_density",
    "accessibility",
    "weather_condition",
    "traffic_level",
    "address_length",
    "contact_valid"
]

NUMERICAL_COLS = [
    "address_length",
    "contact_valid"
]

MAX_REASONS = 3

# ==============================
# LOAD MODEL
# ==============================

model = joblib.load(MODEL_PATH)

# Extract pipeline components ONCE (important for performance)
preprocessor = model.named_steps["preprocessor"]
model_step = model.named_steps["model"]

# ==============================
# UTIL FUNCTIONS
# ==============================

def is_valid_phone(phone: str) -> int:
    pattern = r"^(\+977)?(98[0-9]{8}|97[0-9]{8}|01[0-9]{7})$"
    return 1 if re.match(pattern, phone) else 0


def preprocess_input(data: Dict[str, Any]) -> pd.DataFrame:
    input_dict = data.copy()

    # Feature engineering
    input_dict["contact_valid"] = is_valid_phone(input_dict.get("phone_number", ""))
    input_dict.pop("phone_number", None)

    df = pd.DataFrame([input_dict])

    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")

    return df[EXPECTED_COLUMNS]


# ==============================
# RISK CLASSIFICATION
# ==============================

def classify_risk(probability: float) -> str:
    if probability >= 0.7:
        return "HIGH"
    elif probability > 0.4:
        return "MEDIUM"
    return "LOW"


# ==============================
# RULE-BASED EXPLANATION (HUMAN)
# ==============================

def generate_explanation(input_data: Dict[str, Any], probability: float, risk: str) -> List[str]:
    reasons = []

    try:
        if probability > 0.85:
            reasons.append("Very high predicted failure probability")
        elif probability > 0.65:
            reasons.append("Elevated delivery risk detected")

        if input_data.get("contact_valid") == 0:
            reasons.append("Invalid or unreachable phone number")

        if input_data.get("address_clarity") == "unclear":
            reasons.append("Unclear or incomplete address")

        if input_data.get("traffic_level") == "high":
            reasons.append("Heavy traffic may delay delivery")

        if input_data.get("weather_condition") == "extreme":
            reasons.append("Extreme weather conditions")

        if input_data.get("accessibility") == "difficult":
            reasons.append("Delivery location is hard to access")

        if input_data.get("payment_method") == "COD":
            reasons.append("Cash on Delivery orders have higher failure rates")

        if input_data.get("delivery_time") == "evening":
            reasons.append("Evening deliveries are less reliable")

        if risk == "LOW":
            return ["Low predicted risk based on stable delivery conditions"]

        return reasons[:MAX_REASONS] if reasons else ["Risk detected but no dominant factor identified"]

    except Exception:
        return ["Explanation generation failed"]


# ==============================
# SHAP EXPLANATION (REAL ML)
# ==============================
def get_shap_explanation(df: pd.DataFrame):
    try:
        # Step 1: Transform input
        transformed = preprocessor.transform(df)

        # Step 2: Use pre-created explainer (DO NOT recreate every call)
        shap_values = explainer.shap_values(transformed)

        # Step 3: Handle binary classification
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        # Step 4: Robust shape handling (this is where your bug was)
        values = shap_values

        if hasattr(values, "shape"):
            if len(values.shape) == 2:
                values = values[0]

        values = values.flatten()

        # Step 5: Get feature names safely (no manual stitching)
        feature_names = preprocessor.get_feature_names_out()

        # Step 6: Build explanation (no hacks like .item())
        explanation = []
        for feature, val in zip(feature_names, values):
            val = float(val)

            explanation.append({
                "feature": feature,
                "impact": round(val, 4),
                "effect": "increase" if val > 0 else "decrease"
            })

        # Step 7: Sort by importance
        explanation.sort(key=lambda x: abs(x["impact"]), reverse=True)

        return explanation[:5]

    except Exception as e:
        return [{"error": str(e)}]

# ==============================
# MAIN PREDICT FUNCTION
# ==============================

def predict(data) -> Dict[str, Any]:
    try:
        input_dict = data.model_dump()

        df = preprocess_input(input_dict)

        prediction = int(model.predict(df)[0])
        probability = float(model.predict_proba(df)[0][1])

        risk = classify_risk(probability)

        reasons = generate_explanation(input_dict, probability, risk)

        shap_explanation = get_shap_explanation(df)
        return {
        "success": True,
        "prediction": prediction,
        "probability": probability,
        "risk": risk,
        "reasons": reasons,
        "shap_explanations": shap_explanation
    }

    except Exception as e:
        return {
            "success": False,
            "error": "prediction_failed",
            "detail": str(e)
        }


# ==============================
# FEATURE IMPORTANCE (GLOBAL)
# ==============================

def get_feature_importance():
    try:
        cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out()
        all_features = list(cat_features) + list(NUMERICAL_COLS)

        importances = model_step.feature_importances_

        result = [
            {
                "feature": name,
                "importance": round(float(score), 4)
            }
            for name, score in zip(all_features, importances)
        ]

        result.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "success": True,
            "features": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": "feature_importance_failed",
            "detail": str(e)
        }
    
print(preprocessor.transformers_)