"""
Model prediction and explainability service.

Loads the trained delivery-failure pipeline and performs inference
using the exact 41-feature representation used during training.

Responsibilities:
- Load delivery_model.pkl once.
- Validate the complete 41-feature contract.
- Convert one feature dictionary into one DataFrame row.
- Predict delivery failure.
- Return probability of delivery failure.
- Classify probability into LOW / MEDIUM / HIGH.
- Generate SHAP explanations using the same transformed features.

This module does NOT:
- call ORS
- call weather APIs
- access the database
- create orders
- assign riders
- block orders
- calculate a second hand-written risk score
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.services.feature_engineering import MODEL_FEATURES

logger = logging.getLogger(__name__)


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "delivery_model.pkl"
)

PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

DATASET_PATH = (
    PROJECT_ROOT
    / "app"
    / "data"
    / "delivery_data.csv"
)


# ============================================================
# MODEL LOADING
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_PATH}. "
        "Train the model before starting the application."
    )

model = joblib.load(
    MODEL_PATH
)

logger.info(
    "Delivery failure model loaded from %s",
    MODEL_PATH,
)


# ============================================================
# PIPELINE COMPONENTS
# ============================================================

if not hasattr(
    model,
    "named_steps",
):
    raise RuntimeError(
        "delivery_model.pkl is expected to contain "
        "a scikit-learn Pipeline."
    )

preprocessor = model.named_steps.get(
    "preprocessor"
)

model_step = model.named_steps.get(
    "model"
)

if preprocessor is None:
    raise RuntimeError(
        "Trained pipeline does not contain "
        "a 'preprocessor' step."
    )

if model_step is None:
    raise RuntimeError(
        "Trained pipeline does not contain "
        "a final 'model' step."
    )


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(
    probability: float,
) -> str:
    """
    Convert predicted failure probability into a policy risk level.

        probability >= 0.70 -> HIGH
        probability >= 0.40 -> MEDIUM
        otherwise            -> LOW
    """

    probability = max(
        0.0,
        min(
            float(probability),
            1.0,
        ),
    )

    if probability >= 0.70:
        return "HIGH"

    if probability >= 0.40:
        return "MEDIUM"

    return "LOW"


# ============================================================
# FEATURE VALIDATION
# ============================================================

def validate_features(
    features: dict[str, Any],
) -> None:
    """
    Strictly validate the frozen 41-feature contract.
    """

    if not isinstance(
        features,
        dict,
    ):
        raise TypeError(
            "Prediction input must be a dictionary."
        )

    expected = set(
        MODEL_FEATURES
    )

    actual = set(
        features.keys()
    )

    missing_features = sorted(
        expected - actual
    )

    unexpected_features = sorted(
        actual - expected
    )

    if missing_features:
        raise ValueError(
            "Missing model features:\n"
            + "\n".join(
                f"  - {feature}"
                for feature in missing_features
            )
        )

    if unexpected_features:
        raise ValueError(
            "Unexpected model features:\n"
            + "\n".join(
                f"  - {feature}"
                for feature in unexpected_features
            )
        )


# ============================================================
# DATAFRAME CONVERSION
# ============================================================

def features_to_dataframe(
    features: dict[str, Any],
) -> pd.DataFrame:
    """
    Convert exactly one validated feature dictionary into one
    DataFrame row using the frozen feature order.
    """

    validate_features(
        features
    )

    row = {
        feature: features[feature]
        for feature in MODEL_FEATURES
    }

    return pd.DataFrame(
        [row],
        columns=MODEL_FEATURES,
    )


# ============================================================
# MODEL CLASS HANDLING
# ============================================================

def _get_model_classes() -> list[Any]:
    """
    Retrieve class labels from the trained classifier.
    """

    classes = getattr(
        model,
        "classes_",
        None,
    )

    if classes is not None:
        return list(classes)

    classes = getattr(
        model_step,
        "classes_",
        None,
    )

    if classes is None:
        raise RuntimeError(
            "Unable to determine trained model classes."
        )

    return list(classes)


def _get_failure_probability(
    probabilities,
) -> float:
    """
    Extract probability for class 1 = delivery failure.
    """

    classes = _get_model_classes()

    try:
        failure_index = classes.index(
            1
        )
    except ValueError as exc:
        raise RuntimeError(
            "The trained model does not contain "
            "class 1 for delivery failure."
        ) from exc

    return float(
        probabilities[
            failure_index
        ]
    )


# ============================================================
# PREDICTION
# ============================================================

def predict(
    features: dict[str, Any],
) -> dict[str, Any]:
    """
    Predict whether a delivery will fail.

    Input:
        All 41 MODEL_FEATURES.

    Output:
        success
        prediction
        probability
        risk
        processed_features
    """

    try:

        df = features_to_dataframe(
            features
        )

        prediction = int(
            model.predict(df)[0]
        )

        probabilities = model.predict_proba(
            df
        )[0]

        probability = _get_failure_probability(
            probabilities
        )

        risk = classify_risk(
            probability
        )

        logger.info(
            "Delivery prediction generated | "
            "prediction=%s | probability=%.4f | risk=%s",
            prediction,
            probability,
            risk,
        )

        return {
            "success": True,
            "prediction": prediction,
            "probability": round(
                probability,
                4,
            ),
            "risk": risk,
            "processed_features": (
                df.iloc[0].to_dict()
            ),
        }

    except Exception as exc:

        logger.exception(
            "Delivery failure prediction failed"
        )

        return {
            "success": False,
            "error": "prediction_failed",
            "detail": str(exc),
        }


# ============================================================
# SHAP BACKGROUND DATA
# ============================================================

def _load_shap_background(
    max_rows: int = 250,
) -> pd.DataFrame:
    """
    Load a deterministic sample of the training data for SHAP.

    This is used only for explainability.

    The prediction endpoint does NOT need to load the CSV.
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found for SHAP: "
            f"{DATASET_PATH}"
        )

    dataset = pd.read_csv(
        DATASET_PATH
    )

    validate_columns = set(
        MODEL_FEATURES
    )

    missing = sorted(
        validate_columns
        - set(dataset.columns)
    )

    if missing:
        raise ValueError(
            "Training dataset is missing "
            "features required for SHAP:\n"
            + "\n".join(
                f"  - {feature}"
                for feature in missing
            )
        )

    dataset = dataset[
        MODEL_FEATURES
    ]

    if dataset.empty:
        raise ValueError(
            "Training dataset is empty."
        )

    sample_size = min(
        max_rows,
        len(dataset),
    )

    return dataset.sample(
        n=sample_size,
        random_state=42,
    )


# ============================================================
# SHAP HELPERS
# ============================================================

def _extract_shap_values(
    shap_output,
) -> Any:
    """
    Normalize SHAP output across SHAP versions and classifier types.
    """

    # Older SHAP API:
    #     list[array] for binary classifiers
    if isinstance(
        shap_output,
        list,
    ):

        if len(shap_output) > 1:
            shap_output = shap_output[1]

        elif len(shap_output) == 1:
            shap_output = shap_output[0]

        else:
            raise ValueError(
                "SHAP returned no values."
            )

    # Newer SHAP Explanation object:
    if hasattr(
        shap_output,
        "values",
    ):
        shap_output = (
            shap_output.values
        )

    return shap_output


def _get_shap_feature_names() -> list[str]:
    """
    Get transformed feature names from the exact training
    preprocessor.
    """

    try:
        return list(
            preprocessor.get_feature_names_out()
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to obtain transformed feature names "
            "from the model preprocessor."
        ) from exc
def _group_shap_feature(
    transformed_feature: str,
    impact: float,
) -> dict[str, Any]:
    """
    Convert a transformed sklearn feature name into a readable
    explanation object.

    Examples:

        numeric__distance_km
        cat__payment_method_prepaid
    """

    cleaned_name = (
        transformed_feature
    )

    if "__" in cleaned_name:
        cleaned_name = (
            cleaned_name.split(
                "__",
                1,
            )[1]
        )

    categorical_prefixes = (
        "payment_method_",
        "day_type_",
        "time_period_",
        "weather_",
        "traffic_level_",
        "route_status_",
        "vehicle_status_",
    )

    for prefix in categorical_prefixes:

        if cleaned_name.startswith(
            prefix
        ):

            feature_name = (
                prefix.rstrip("_")
            )

            category_value = (
                cleaned_name[
                    len(prefix):
                ]
            )

            return {
                "feature": feature_name,
                "value": category_value,
                "impact": round(
                    float(impact),
                    4,
                ),
                "effect": (
                    "increase"
                    if impact > 0
                    else "decrease"
                ),
            }

    return {
        "feature": cleaned_name,
        "value": None,
        "impact": round(
            float(impact),
            4,
        ),
        "effect": (
            "increase"
            if impact > 0
            else "decrease"
        ),
    }

# ============================================================
# SHAP EXPLANATION
# ============================================================

def get_shap_explanation(
    features: dict[str, Any],
    max_explanations: int = 6,
) -> list[dict[str, Any]]:
    """
    Generate SHAP explanations for one prediction.

    The SHAP calculation follows the exact preprocessing pipeline
    used during model training.

    Logistic Regression pipeline:

        raw features
            ↓
        preprocessor
            ↓
        StandardScaler
            ↓
        LogisticRegression

    Tree models:

        raw features
            ↓
        preprocessor
            ↓
        tree model

    SHAP impact values represent contribution in the model's
    explanation space. They are NOT probability percentages.

    Returns the strongest contributors together with the actual
    feature values supplied to the model.
    """

    try:
        import shap

        # ----------------------------------------------------
        # Validate and build input dataframe
        # ----------------------------------------------------

        df = features_to_dataframe(
            features
        )

        # ----------------------------------------------------
        # Load transformed background
        # ----------------------------------------------------

        background_df = (
            _load_shap_background()
        )

        # ----------------------------------------------------
        # First transformation stage:
        # raw features -> fitted preprocessor
        # ----------------------------------------------------

        transformed_input = (
            preprocessor.transform(
                df
            )
        )

        transformed_background = (
            preprocessor.transform(
                background_df
            )
        )

        # ----------------------------------------------------
        # Determine whether the trained pipeline contains
        # an additional scaler.
        # ----------------------------------------------------

        scaler = model.named_steps.get(
            "scaler"
        )

        # ----------------------------------------------------
        # Logistic Regression
        # ----------------------------------------------------

        if hasattr(
            model_step,
            "coef_",
        ):

            # The training pipeline applies StandardScaler
            # after the ColumnTransformer.
            if scaler is not None:

                transformed_background = (
                    scaler.transform(
                        transformed_background
                    )
                )

                transformed_input = (
                    scaler.transform(
                        transformed_input
                    )
                )

            explainer = shap.LinearExplainer(
                model_step,
                transformed_background,
            )

            shap_output = (
                explainer.shap_values(
                    transformed_input
                )
            )

        # ----------------------------------------------------
        # Tree model
        # ----------------------------------------------------

        elif hasattr(
            model_step,
            "feature_importances_",
        ):

            explainer = shap.TreeExplainer(
                model_step
            )

            shap_output = (
                explainer.shap_values(
                    transformed_input
                )
            )

        # ----------------------------------------------------
        # Generic fallback
        # ----------------------------------------------------

        else:

            # For an unknown estimator we explain the estimator
            # using the transformed feature matrix.
            explainer = shap.Explainer(
                model_step,
                transformed_background,
            )

            shap_output = (
                explainer.shap_values(
                    transformed_input
                )
            )

        # ----------------------------------------------------
        # Normalize SHAP output
        # ----------------------------------------------------

        shap_values = _extract_shap_values(
            shap_output
        )

        if hasattr(
            shap_values,
            "toarray",
        ):
            shap_values = (
                shap_values.toarray()
            )

        shap_values = (
            pd.DataFrame(
                shap_values
            ).to_numpy()
        )

        if shap_values.ndim == 1:

            values = shap_values

        elif shap_values.ndim == 2:

            values = shap_values[0]

        else:

            raise ValueError(
                "Unexpected SHAP value dimensions: "
                f"{shap_values.shape}"
            )

        # ----------------------------------------------------
        # Get transformed feature names
        # ----------------------------------------------------

        feature_names = (
            _get_shap_feature_names()
        )

        if len(values) != len(
            feature_names
        ):
            raise ValueError(
                "SHAP value count does not match "
                "transformed feature count. "
                f"SHAP={len(values)} "
                f"features={len(feature_names)}"
            )

        # ----------------------------------------------------
        # Build readable explanations
        # ----------------------------------------------------

        explanations = []

        for feature_name, impact in zip(
            feature_names,
            values,
        ):

            impact = float(
                impact
            )

            # Ignore negligible contributions.
            if abs(impact) < 0.01:
                continue

            grouped = (
                _group_shap_feature(
                    transformed_feature=(
                        feature_name
                    ),
                    impact=impact,
                )
            )

            # ------------------------------------------------
            # Recover actual raw feature value
            # ------------------------------------------------

            raw_feature_name = (
                grouped["feature"]
            )

            # One-hot categorical feature:
            #
            # Example:
            # cat__payment_method_prepaid
            #
            # _group_shap_feature() converts that to:
            #
            # feature = payment_method
            # value   = prepaid
            #
            if (
                grouped.get("value")
                is not None
            ):

                actual_value = (
                    grouped["value"]
                )

            else:

                actual_value = (
                    features.get(
                        raw_feature_name
                    )
                )

            grouped[
                "actual_value"
            ] = actual_value

            # Explicitly tell the API consumer what the
            # SHAP impact represents.
            grouped[
                "impact_type"
            ] = "model_log_odds_contribution"

            grouped[
                "direction"
            ] = (
                "increases_failure_probability"
                if impact > 0
                else "decreases_failure_probability"
            )

            explanations.append(
                grouped
            )

        # ----------------------------------------------------
        # Sort by absolute impact
        # ----------------------------------------------------

        explanations.sort(
            key=lambda item: abs(
                float(
                    item["impact"]
                )
            ),
            reverse=True,
        )

        return explanations[
            :max_explanations
        ]

    except Exception as exc:

        logger.exception(
            "SHAP explanation failed"
        )

        return [
            {
                "error": str(exc)
            }
        ]

# ============================================================
# SIMPLE HUMAN-READABLE REASONS
# ============================================================

def generate_explanation_reasons(
    features: dict[str, Any],
    probability: float,
    max_reasons: int = 4,
) -> list[str]:
    """
    Generate deterministic human-readable context alongside SHAP.

    These are descriptive explanations, not a second prediction model.
    """

    reasons: list[str] = []

    if probability >= 0.70:
        reasons.append(
            "The model predicts a high probability of delivery failure."
        )

    elif probability >= 0.40:
        reasons.append(
            "The model predicts a moderate probability of delivery failure."
        )

    else:
        reasons.append(
            "The model predicts a relatively low probability of delivery failure."
        )

    if features.get(
        "failure_rate",
        0,
    ) >= 0.40:

        reasons.append(
            "Customer history shows a relatively high previous delivery failure rate."
        )

    if features.get(
        "unreachable_rate",
        0,
    ) >= 0.25:

        reasons.append(
            "The customer's historical unreachable rate is relatively high."
        )

    if features.get(
        "traffic_level"
    ) in {
        "HIGH",
        "SEVERE",
    }:

        reasons.append(
            "The route has elevated estimated traffic conditions."
        )

    if features.get(
        "traffic_delay_ratio",
        0,
    ) >= 0.30:

        reasons.append(
            "Estimated traffic delay is significant relative to baseline travel time."
        )

    if features.get(
        "is_long_distance"
    ):

        reasons.append(
            "The delivery route is classified as long distance."
        )

    if features.get(
        "is_raining"
    ):

        reasons.append(
            "Rain is present along the sampled delivery route."
        )

    if features.get(
        "is_severe_weather"
    ):

        reasons.append(
            "Severe weather conditions are present."
        )

    if features.get(
        "high_traffic"
    ):

        reasons.append(
            "Traffic is classified as high or severe."
        )

    if features.get(
        "route_status"
    ) == "DELAYED":

        reasons.append(
            "The route is currently marked as delayed."
        )

    elif features.get(
        "route_status"
    ) == "BLOCKED":

        reasons.append(
            "The route is currently marked as blocked."
        )

    if features.get(
        "hub_delay_minutes",
        0,
    ) >= 30:

        reasons.append(
            "The dispatch hub has a significant pre-dispatch delay."
        )

    return reasons[
        :max_reasons
    ]