"""
Train and compare delivery-failure classification models.

Dataset:
    app/data/delivery_data.csv

Target:
    delivery_failure

Candidate models:
    1. Logistic Regression
    2. Random Forest
    3. Gradient Boosting

The best model is selected using:
    1. F1 score
    2. Recall
    3. ROC-AUC

The winning preprocessing + model pipeline is saved as:
    app/ml/delivery_model.pkl
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.utils.feature_engineering import MODEL_FEATURES


# ============================================================
# PATHS
# ============================================================

# train_model.py is inside app/ml/
# parents[1] = app/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = PROJECT_ROOT / "data" / "delivery_data.csv"
MODEL_PATH = PROJECT_ROOT / "ml" / "delivery_model.pkl"
RESULTS_PATH = PROJECT_ROOT / "ml" / "model_comparison.csv"
RF_IMPORTANCE_PATH = (
    PROJECT_ROOT / "ml" / "random_forest_feature_importance.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_COLUMN = "delivery_failure"

TEST_SIZE = 0.20
RANDOM_STATE = 42
CV_FOLDS = 5


# ============================================================
# FEATURE GROUPS
# ============================================================

CATEGORICAL_FEATURES = [
    "payment_method",
    "weather",
    "traffic_level",
    "route_status",
    "vehicle_status",
]

NUMERICAL_FEATURES = [
    feature
    for feature in MODEL_FEATURES
    if feature not in CATEGORICAL_FEATURES
]


# ============================================================
# PREPROCESSOR
# ============================================================

def build_preprocessor() -> ColumnTransformer:
    """
    Shared preprocessing for all candidate models.

    Numerical:
        missing values -> median

    Categorical:
        missing values -> most frequent
        strings -> one-hot encoded
    """

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERICAL_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


# ============================================================
# MODEL DEFINITIONS
# ============================================================

def build_models() -> dict[str, Pipeline]:
    """
    Create the three candidate ML pipelines.

    Every model receives the exact same features and preprocessing.
    """

    return {
        "logistic_regression": Pipeline(
            steps=[
                (
                    "preprocessor",
                    build_preprocessor(),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "random_forest": Pipeline(
            steps=[
                (
                    "preprocessor",
                    build_preprocessor(),
                ),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=12,
                        min_samples_split=5,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),

        "gradient_boosting": Pipeline(
            steps=[
                (
                    "preprocessor",
                    build_preprocessor(),
                ),
                (
                    "model",
                    GradientBoostingClassifier(
                        n_estimators=200,
                        learning_rate=0.05,
                        max_depth=3,
                        min_samples_split=10,
                        min_samples_leaf=5,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


# ============================================================
# DATASET
# ============================================================

def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    print("=" * 70)
    print("DELIVERY FAILURE MODEL TRAINING")
    print("=" * 70)

    print(f"\n[INFO] Dataset: {DATA_PATH}")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    print(f"[INFO] Dataset shape: {df.shape}")

    # --------------------------------------------------------
    # Target validation
    # --------------------------------------------------------

    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' "
            f"not found in dataset."
        )

    # --------------------------------------------------------
    # Feature validation
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in MODEL_FEATURES
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            "Dataset is missing required model features:\n"
            + "\n".join(
                f"  - {feature}"
                for feature in missing_features
            )
        )

    X = df[MODEL_FEATURES].copy()
    y = df[TARGET_COLUMN].copy()

    # --------------------------------------------------------
    # Target validation
    # --------------------------------------------------------

    if y.isnull().any():
        raise ValueError(
            "Target column contains missing values."
        )

    unique_targets = set(
        y.astype(int).unique()
    )

    if not unique_targets.issubset({0, 1}):
        raise ValueError(
            f"Target must contain only 0 and 1. "
            f"Found: {unique_targets}"
        )

    # --------------------------------------------------------
    # Numerical values
    # --------------------------------------------------------

    for column in NUMERICAL_FEATURES:
        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Categorical values
    # --------------------------------------------------------

    for column in CATEGORICAL_FEATURES:
        X[column] = (
            X[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    print("\n[INFO] Target distribution:")
    print(y.value_counts())

    print("\n[INFO] Target proportion:")
    print(
        y.value_counts(
            normalize=True
        ).round(4)
    )

    print("\n[INFO] Categorical features:")
    for feature in CATEGORICAL_FEATURES:
        print(f"  - {feature}")

    print("\n[INFO] Numerical features:")
    for feature in NUMERICAL_FEATURES:
        print(f"  - {feature}")

    return X, y


# ============================================================
# TEST SET EVALUATION
# ============================================================

def evaluate_model(
    model_name: str,
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    """
    Evaluate a trained model on the held-out test data.
    """

    y_pred = pipeline.predict(X_test)
    y_probability = pipeline.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(
        y_test,
        y_pred,
    )

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        y_test,
        y_probability,
    )

    print("\n" + "-" * 70)
    print(f"MODEL: {model_name.upper()}")
    print("-" * 70)

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            zero_division=0,
        )
    )

    print("Confusion Matrix:")
    print(
        confusion_matrix(
            y_test,
            y_pred,
        )
    )

    return {
        "model": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
    }


# ============================================================
# CROSS VALIDATION
# ============================================================

def calculate_cross_validation(
    model_name: str,
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
) -> tuple[float, float]:
    """
    Five-fold stratified CV using F1 score.

    F1 is used because this project cares about correctly
    identifying delivery failures, not only overall accuracy.
    """

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    scores = cross_val_score(
        pipeline,
        X,
        y,
        cv=cv,
        scoring="f1",
        n_jobs=1,
    )

    mean_score = float(scores.mean())
    std_score = float(scores.std())

    print(
        f"[CV] {model_name}: "
        f"F1 = {mean_score:.4f} "
        f"+/- {std_score:.4f}"
    )

    return mean_score, std_score


# ============================================================
# BEST MODEL
# ============================================================

def select_best_model(results: list[dict]) -> dict:
    """
    Select the winner.

    Priority:
        1. Test F1
        2. Test Recall
        3. ROC-AUC
    """

    return max(
        results,
        key=lambda row: (
            row["f1"],
            row["recall"],
            row["roc_auc"],
        ),
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    X, y = load_dataset()

    # --------------------------------------------------------
    # Train/test split
    # --------------------------------------------------------

    print("\n[INFO] Creating stratified train/test split...")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(
        f"[INFO] Training rows: {len(X_train)}"
    )

    print(
        f"[INFO] Testing rows : {len(X_test)}"
    )

    # --------------------------------------------------------
    # Candidate models
    # --------------------------------------------------------

    models = build_models()

    fitted_models: dict[str, Pipeline] = {}
    results: list[dict] = []

    # --------------------------------------------------------
    # Train / evaluate every model
    # --------------------------------------------------------

    for model_name, pipeline in models.items():

        print("\n" + "=" * 70)
        print(
            f"TRAINING {model_name.upper()}"
        )
        print("=" * 70)

        pipeline.fit(
            X_train,
            y_train,
        )

        test_results = evaluate_model(
            model_name=model_name,
            pipeline=pipeline,
            X_test=X_test,
            y_test=y_test,
        )

        cv_mean, cv_std = calculate_cross_validation(
            model_name=model_name,
            pipeline=pipeline,
            X=X,
            y=y,
        )

        test_results["cv_f1_mean"] = cv_mean
        test_results["cv_f1_std"] = cv_std

        results.append(test_results)
        fitted_models[model_name] = pipeline

    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df = results_df[
        [
            "model",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "cv_f1_mean",
            "cv_f1_std",
        ]
    ]

    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    print(
        results_df.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}",
        )
    )

    # --------------------------------------------------------
    # Select final model
    # --------------------------------------------------------

    best_result = select_best_model(
        results
    )

    best_model_name = best_result["model"]
    best_pipeline = fitted_models[
        best_model_name
    ]

    print("\n" + "=" * 70)
    print("FINAL MODEL SELECTION")
    print("=" * 70)

    print(
        f"Selected model : {best_model_name}"
    )

    print(
        f"Test F1        : "
        f"{best_result['f1']:.4f}"
    )

    print(
        f"Test Recall    : "
        f"{best_result['recall']:.4f}"
    )

    print(
        f"Test Precision : "
        f"{best_result['precision']:.4f}"
    )

    print(
        f"Test ROC-AUC   : "
        f"{best_result['roc_auc']:.4f}"
    )

    print(
        f"CV F1          : "
        f"{best_result['cv_f1_mean']:.4f}"
    )

    # --------------------------------------------------------
    # Save winning model
    # --------------------------------------------------------

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        best_pipeline,
        MODEL_PATH,
    )

    print("\n[INFO] Winning model saved:")
    print(MODEL_PATH)

    # --------------------------------------------------------
    # Save comparison results
    # --------------------------------------------------------

    results_df.to_csv(
        RESULTS_PATH,
        index=False,
    )

    print(
        "[INFO] Model comparison saved:"
    )
    print(RESULTS_PATH)

    # --------------------------------------------------------
    # Random Forest feature importance
    # --------------------------------------------------------

    if "random_forest" in fitted_models:

        rf_pipeline = fitted_models[
            "random_forest"
        ]

        rf_model = (
            rf_pipeline
            .named_steps["model"]
        )

        rf_preprocessor = (
            rf_pipeline
            .named_steps["preprocessor"]
        )

        try:
            feature_names = (
                rf_preprocessor
                .get_feature_names_out()
            )

            importance_df = pd.DataFrame(
                {
                    "feature": feature_names,
                    "importance": (
                        rf_model
                        .feature_importances_
                    ),
                }
            ).sort_values(
                by="importance",
                ascending=False,
            )

            importance_df.to_csv(
                RF_IMPORTANCE_PATH,
                index=False,
            )

            print(
                "\n[INFO] Random Forest feature "
                "importance saved:"
            )
            print(RF_IMPORTANCE_PATH)

            print(
                "\nTop 15 Random Forest features:"
            )

            print(
                importance_df
                .head(15)
                .to_string(index=False)
            )

        except Exception as exc:
            print(
                "\n[WARNING] Could not calculate "
                f"Random Forest feature importance: {exc}"
            )

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()