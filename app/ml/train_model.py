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

from app.services.feature_engineering import MODEL_FEATURES


# ============================================================
# PATHS
# ============================================================

# train_model.py is inside app/ml/
# parents[1] -> app/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "delivery_data.csv"
)

MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "delivery_model.pkl"
)

RESULTS_PATH = (
    PROJECT_ROOT
    / "ml"
    / "model_comparison.csv"
)

RF_IMPORTANCE_PATH = (
    PROJECT_ROOT
    / "ml"
    / "random_forest_feature_importance.csv"
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

# Categorical values are kept as strings in feature_engineering.py
# and encoded here using OneHotEncoder.

CATEGORICAL_FEATURES = [
    "payment_method",

    "day_type",
    "time_period",

    "weather",
    "traffic_level",

    "route_status",
    "vehicle_status",
]


# Everything else in MODEL_FEATURES is numeric.
NUMERICAL_FEATURES = [
    feature
    for feature in MODEL_FEATURES
    if feature not in CATEGORICAL_FEATURES
]


# ============================================================
# CONTRACT VALIDATION
# ============================================================

def validate_feature_contract(
    df: pd.DataFrame,
) -> None:
    """
    Make sure the CSV exactly contains the current model feature
    contract plus the target column.

    This prevents silently training on an outdated CSV.
    """

    expected_columns = set(
        MODEL_FEATURES
        + [TARGET_COLUMN]
    )

    actual_columns = set(
        df.columns
    )

    missing = sorted(
        expected_columns - actual_columns
    )

    unexpected = sorted(
        actual_columns - expected_columns
    )

    if missing:
        raise ValueError(
            "Dataset is missing required columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    if unexpected:
        raise ValueError(
            "Dataset contains unexpected columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in unexpected
            )
        )


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

    The output is dense so Logistic Regression, Random Forest,
    and Gradient Boosting can use the exact same transformed data.
    """

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
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
    Create candidate ML pipelines.

    Every model receives exactly the same raw features and
    preprocessing.
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
                    StandardScaler(
                        with_mean=True,
                    ),
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

    print(
        f"\n[INFO] Dataset: {DATA_PATH}"
    )

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH
    )

    print(
        f"[INFO] Dataset shape: {df.shape}"
    )

    # --------------------------------------------------------
    # Exact dataset contract
    # --------------------------------------------------------

    validate_feature_contract(
        df
    )

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    y = df[
        TARGET_COLUMN
    ].copy()

    if y.isnull().any():
        raise ValueError(
            "Target column contains missing values."
        )

    try:
        y = y.astype(int)
    except ValueError as exc:
        raise ValueError(
            "Target column must contain only 0 and 1."
        ) from exc

    unique_targets = set(
        y.unique()
    )

    if not unique_targets.issubset(
        {0, 1}
    ):
        raise ValueError(
            "Target must contain only 0 and 1. "
            f"Found: {unique_targets}"
        )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    X = df[
        MODEL_FEATURES
    ].copy()

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    for column in NUMERICAL_FEATURES:
        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Categorical normalization
    # --------------------------------------------------------

    for column in CATEGORICAL_FEATURES:

        X[column] = (
            X[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    # --------------------------------------------------------
    # Output diagnostics
    # --------------------------------------------------------

    print(
        "\n[INFO] Target distribution:"
    )
    print(
        y.value_counts()
    )

    print(
        "\n[INFO] Target proportion:"
    )
    print(
        y.value_counts(
            normalize=True
        ).round(4)
    )

    print(
        "\n[INFO] Categorical features:"
    )

    for feature in CATEGORICAL_FEATURES:
        print(
            f"  - {feature}"
        )

    print(
        "\n[INFO] Numerical features:"
    )

    for feature in NUMERICAL_FEATURES:
        print(
            f"  - {feature}"
        )

    print(
        "\n[INFO] Model feature count:"
        f" {len(MODEL_FEATURES)}"
    )

    print(
        "[INFO] Categorical feature count:"
        f" {len(CATEGORICAL_FEATURES)}"
    )

    print(
        "[INFO] Numerical feature count:"
        f" {len(NUMERICAL_FEATURES)}"
    )

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
    Evaluate a fitted model on the held-out test set.
    """

    y_pred = pipeline.predict(
        X_test
    )

    y_probability = (
        pipeline.predict_proba(
            X_test
        )[:, 1]
    )

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

    print(
        "\n"
        + "-" * 70
    )

    print(
        f"MODEL: {model_name.upper()}"
    )

    print(
        "-" * 70
    )

    print(
        f"Accuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1 Score : {f1:.4f}"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            y_pred,
            zero_division=0,
        )
    )

    print(
        "Confusion Matrix:"
    )

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
) -> tuple[float, float, float]:
    """
    Stratified five-fold cross-validation.

    We calculate F1, recall, and ROC-AUC.

    Model selection later uses CV F1 first, because the project
    needs good identification of failed deliveries.
    """

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    f1_scores = cross_val_score(
        pipeline,
        X,
        y,
        cv=cv,
        scoring="f1",
        n_jobs=1,
    )

    recall_scores = cross_val_score(
        pipeline,
        X,
        y,
        cv=cv,
        scoring="recall",
        n_jobs=1,
    )

    roc_auc_scores = cross_val_score(
        pipeline,
        X,
        y,
        cv=cv,
        scoring="roc_auc",
        n_jobs=1,
    )

    f1_mean = float(
        f1_scores.mean()
    )

    f1_std = float(
        f1_scores.std()
    )

    recall_mean = float(
        recall_scores.mean()
    )

    roc_auc_mean = float(
        roc_auc_scores.mean()
    )

    print(
        f"[CV] {model_name}: "
        f"F1={f1_mean:.4f} +/- {f1_std:.4f}, "
        f"Recall={recall_mean:.4f}, "
        f"ROC-AUC={roc_auc_mean:.4f}"
    )

    return (
        f1_mean,
        f1_std,
        recall_mean,
    )


# ============================================================
# MODEL SELECTION
# ============================================================

def select_best_model(
    results: list[dict],
) -> dict:
    """
    Select the model using validation results, not the test set.

    Priority:
        1. CV F1
        2. CV Recall
        3. Test ROC-AUC only as a final tie-breaker

    This avoids selecting a model simply because it happened
    to perform best on the held-out test set.
    """

    return max(
        results,
        key=lambda row: (
            row["cv_f1_mean"],
            row["cv_recall_mean"],
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

    print(
        "\n[INFO] Creating stratified train/test split..."
    )

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    )

    print(
        f"[INFO] Training rows: "
        f"{len(X_train)}"
    )

    print(
        f"[INFO] Testing rows : "
        f"{len(X_test)}"
    )

    # --------------------------------------------------------
    # Candidate models
    # --------------------------------------------------------

    models = build_models()

    fitted_models: dict[
        str,
        Pipeline,
    ] = {}

    results: list[
        dict
    ] = []

    # --------------------------------------------------------
    # Train and evaluate
    # --------------------------------------------------------

    for (
        model_name,
        pipeline,
    ) in models.items():

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"TRAINING {model_name.upper()}"
        )

        print(
            "=" * 70
        )

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

        (
            cv_f1_mean,
            cv_f1_std,
            cv_recall_mean,
        ) = calculate_cross_validation(
            model_name=model_name,
            pipeline=pipeline,
            X=X,
            y=y,
        )

        test_results[
            "cv_f1_mean"
        ] = cv_f1_mean

        test_results[
            "cv_f1_std"
        ] = cv_f1_std

        test_results[
            "cv_recall_mean"
        ] = cv_recall_mean

        results.append(
            test_results
        )

        fitted_models[
            model_name
        ] = pipeline

    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

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
            "cv_recall_mean",
        ]
    ]

    print(
        "\n"
        + "=" * 70
    )

    print(
        "MODEL COMPARISON"
    )

    print(
        "=" * 70
    )

    print(
        results_df.to_string(
            index=False,
            float_format=(
                lambda value:
                f"{value:.4f}"
            ),
        )
    )

    # --------------------------------------------------------
    # Final model selection
    # --------------------------------------------------------

    best_result = select_best_model(
        results
    )

    best_model_name = (
        best_result["model"]
    )

    best_pipeline = fitted_models[
        best_model_name
    ]

    print(
        "\n"
        + "=" * 70
    )

    print(
        "FINAL MODEL SELECTION"
    )

    print(
        "=" * 70
    )

    print(
        f"Selected model : "
        f"{best_model_name}"
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

    print(
        f"CV Recall      : "
        f"{best_result['cv_recall_mean']:.4f}"
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

    print(
        "\n[INFO] Winning model saved:"
    )

    print(
        MODEL_PATH
    )

    # --------------------------------------------------------
    # Save comparison
    # --------------------------------------------------------

    results_df.to_csv(
        RESULTS_PATH,
        index=False,
    )

    print(
        "\n[INFO] Model comparison saved:"
    )

    print(
        RESULTS_PATH
    )

    # --------------------------------------------------------
    # Random Forest feature importance
    # --------------------------------------------------------

    if (
        "random_forest"
        in fitted_models
    ):

        rf_pipeline = fitted_models[
            "random_forest"
        ]

        rf_model = (
            rf_pipeline
            .named_steps["model"]
        )

        rf_preprocessor = (
            rf_pipeline
            .named_steps[
                "preprocessor"
            ]
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
                "\n[INFO] Random Forest "
                "feature importance saved:"
            )

            print(
                RF_IMPORTANCE_PATH
            )

            print(
                "\nTop 15 Random Forest features:"
            )

            print(
                importance_df
                .head(15)
                .to_string(
                    index=False
                )
            )

        except Exception as exc:

            print(
                "\n[WARNING] Could not calculate "
                "Random Forest feature importance: "
                f"{exc}"
            )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TRAINING COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()