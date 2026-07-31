import logging
import pandas as pd
import joblib
import shap
from pathlib import Path
from typing import Dict, Any, List

from app.utils.feature_engineering import (
    MODEL_FEATURE_COLUMNS,
    process_input,
)

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent / "delivery_model.pkl"

model = joblib.load(MODEL_PATH)
preprocessor = model.named_steps["preprocessor"]
model_step = model.named_steps["model"]

explainer = shap.TreeExplainer(
    model_step,
    feature_perturbation="tree_path_dependent",
)

ALLOWED_VALUES = {
    "address_clarity": ["low", "high"],
    "area_density": ["low", "medium", "high"],
    "order_value_category": ["low", "medium", "high"],
    "weather_condition": ["normal", "rain", "extreme"],
    "payment_method": ["COD", "prepaid"],
}

FEATURE_NAME_MAP = {
    "cat__payment_method_COD": ("payment_method", "COD"),
    "cat__payment_method_prepaid": ("payment_method", "prepaid"),
    "cat__order_value_category_low": ("order_value_category", "low"),
    "cat__order_value_category_medium": ("order_value_category", "medium"),
    "cat__order_value_category_high": ("order_value_category", "high"),
    "cat__area_density_low": ("area_density", "low"),
    "cat__area_density_medium": ("area_density", "medium"),
    "cat__area_density_high": ("area_density", "high"),
    "cat__address_clarity_low": ("address_clarity", "low"),
    "cat__address_clarity_high": ("address_clarity", "high"),
    "cat__weather_condition_normal": ("weather_condition", "normal"),
    "cat__weather_condition_rain": ("weather_condition", "rain"),
    "cat__weather_condition_extreme": ("weather_condition", "extreme"),
}

MAX_REASONS = 3


def validate_processed_features(processed: Dict[str, Any]) -> None:
    for col, allowed in ALLOWED_VALUES.items():
        if col not in processed:
            raise ValueError(f"Missing field: {col}")
        if processed[col] not in allowed:
            raise ValueError(f"Invalid value '{processed[col]}' for {col}")


def raw_to_model_dataframe(raw_input: Dict[str, Any]) -> pd.DataFrame:
    processed = process_input(raw_input)
    validate_processed_features(processed)

    logger.info("Transformed features: %s", processed)
    logger.info("Prediction input columns: %s", MODEL_FEATURE_COLUMNS)

    df = pd.DataFrame([processed])
    return df[MODEL_FEATURE_COLUMNS]


def classify_risk(probability: float) -> str:
    if probability >= 0.7:
        return "HIGH"
    if probability > 0.4:
        return "MEDIUM"
    return "LOW"


def generate_explanation(
    processed_data: Dict[str, Any], probability: float, risk: str
) -> List[str]:
    reasons = []

    try:
        if probability > 0.85:
            reasons.append("Very high predicted failure probability")
        elif probability > 0.65:
            reasons.append("Elevated delivery risk detected")

        if processed_data.get("address_clarity") == "low":
            reasons.append("Delivery address is too short or unclear")

        if processed_data.get("area_density") == "high":
            reasons.append("High-density delivery area")

        if processed_data.get("weather_condition") == "extreme":
            reasons.append("Extreme weather conditions")

        if processed_data.get("payment_method") == "COD":
            reasons.append("Cash on Delivery orders have higher failure rates")

        if processed_data.get("order_value_category") == "high":
            reasons.append("High-value order increases delivery risk")

        if risk == "LOW":
            return ["Low predicted risk based on stable delivery conditions"]

        return reasons[:MAX_REASONS] if reasons else [
            "Risk detected but no dominant factor identified"
        ]

    except Exception:
        return ["Explanation generation failed"]


def get_shap_explanation(df: pd.DataFrame):
    try:
        transformed = preprocessor.transform(df)
        shap_values = explainer.shap_values(transformed)

        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        values = shap_values[0] if len(shap_values.shape) == 2 else shap_values
        values = values.flatten()

        feature_names = preprocessor.get_feature_names_out()
        grouped_features = {}

        for feature, val in zip(feature_names, values):
            if abs(val) < 0.02:
                continue

            if feature in FEATURE_NAME_MAP:
                base_feature, actual_value = FEATURE_NAME_MAP[feature]
                entry = {
                    "feature": base_feature,
                    "value": actual_value,
                    "impact": round(float(val), 4),
                    "effect": "increase" if val > 0 else "decrease",
                }
                if (
                    base_feature not in grouped_features
                    or abs(val) > abs(grouped_features[base_feature]["impact"])
                ):
                    grouped_features[base_feature] = entry

        cleaned_explanation = list(grouped_features.values())
        cleaned_explanation.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return cleaned_explanation[:4]

    except Exception as e:
        return [{"error": str(e)}]


def predict(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        df = raw_to_model_dataframe(raw_input)
        processed_data = df.iloc[0].to_dict()

        prediction = int(model.predict(df)[0])
        probability = float(model.predict_proba(df)[0][1])
        risk = classify_risk(probability)
        reasons = generate_explanation(processed_data, probability, risk)
        shap_explanation = get_shap_explanation(df)

        return {
            "success": True,
            "prediction": prediction,
            "probability": probability,
            "risk": risk,
            "phone_number": raw_input["phone_number"],
            "processed_features": processed_data,
            "reasons": reasons,
            "shap_explanations": shap_explanation,
        }

    except Exception as e:
        logger.exception("Prediction failed")
        return {
            "success": False,
            "error": "prediction_failed",
            "detail": str(e),
        }


def get_feature_importance():
    try:
        cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out()
        importances = model_step.feature_importances_

        result = [
            {"feature": name, "importance": round(float(score), 4)}
            for name, score in zip(cat_features, importances)
        ]
        result.sort(key=lambda x: x["importance"], reverse=True)

        return {"success": True, "features": result}

    except Exception as e:
        return {
            "success": False,
            "error": "feature_importance_failed",
            "detail": str(e),
        }
