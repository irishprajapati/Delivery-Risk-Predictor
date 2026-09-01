from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import matplotlib

# Use a non-interactive backend so plots can be generated
# directly from Terminal without opening a GUI window.
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
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

FIGURES_DIR = (
    PROJECT_ROOT
    / "ml"
    / "figures"
)

FIGURES_DIR.mkdir(
    parents=True,
    exist_ok=True,
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
    "day_type",
    "time_period",
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
    Recreates the exact preprocessing strategy used during
    model training.

    Numerical:
        missing values -> median

    Categorical:
        missing values -> most frequent
        categorical values -> one-hot encoding
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
    Recreates the three candidate models from train_model.py.

    This is important because model_comparison.csv contains
    evaluation results, while delivery_model.pkl contains only
    the selected final model.
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

def validate_dataset(df: pd.DataFrame) -> None:
    """
    Ensures that the dataset contains exactly the expected
    model features plus the target.
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


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    print("=" * 70)
    print("DELIVERY FAILURE MODEL EVALUATION")
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

    validate_dataset(df)

    y = df[
        TARGET_COLUMN
    ].copy()

    y = y.astype(int)

    X = df[
        MODEL_FEATURES
    ].copy()

    # Numeric conversion
    for column in NUMERICAL_FEATURES:
        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

    # Categorical normalization
    for column in CATEGORICAL_FEATURES:
        X[column] = (
            X[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    return X, y


# ============================================================
# FIGURE 1 — CONFUSION MATRIX
# ============================================================

def generate_confusion_matrix(
    y_test: pd.Series,
    y_pred: np.ndarray,
) -> None:
    """
    Generate confusion matrix for the final saved model.
    """

    cm = confusion_matrix(
        y_test,
        y_pred,
    )

    fig, ax = plt.subplots(
        figsize=(7, 6)
    )

    image = ax.imshow(
        cm,
        interpolation="nearest",
        cmap="Blues",
    )

    ax.figure.colorbar(
        image,
        ax=ax,
    )

    classes = [
        "Success (0)",
        "Failure (1)",
    ]

    ax.set(
        xticks=np.arange(len(classes)),
        yticks=np.arange(len(classes)),
        xticklabels=classes,
        yticklabels=classes,
        ylabel="Actual Class",
        xlabel="Predicted Class",
        title="Confusion Matrix - Delivery Failure Prediction",
    )

    threshold = cm.max() / 2.0

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                format(cm[i, j], "d"),
                ha="center",
                va="center",
                color="white"
                if cm[i, j] > threshold
                else "black",
                fontsize=14,
                fontweight="bold",
            )

    fig.tight_layout()

    output_path = (
        FIGURES_DIR
        / "confusion_matrix.png"
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[SAVED] {output_path}"
    )


# ============================================================
# FIGURE 2 — ROC CURVE
# ============================================================

def generate_roc_curve(
    y_test: pd.Series,
    y_probability: np.ndarray,
) -> None:
    """
    Generate ROC curve for the final saved model.
    """

    fpr, tpr, _ = roc_curve(
        y_test,
        y_probability,
    )

    roc_auc = auc(
        fpr,
        tpr,
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.plot(
        fpr,
        tpr,
        linewidth=2,
        label=f"Final Model (AUC = {roc_auc:.3f})",
    )

    ax.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        linewidth=1.5,
        label="Random Classifier",
    )

    ax.set(
        xlim=[0.0, 1.0],
        ylim=[0.0, 1.05],
        xlabel="False Positive Rate",
        ylabel="True Positive Rate",
        title="ROC Curve - Delivery Failure Prediction",
    )

    ax.legend(
        loc="lower right"
    )

    ax.grid(
        alpha=0.3
    )

    fig.tight_layout()

    output_path = (
        FIGURES_DIR
        / "roc_curve.png"
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[SAVED] {output_path}"
    )


# ============================================================
# FIGURE 3 — MODEL COMPARISON
# ============================================================

def generate_model_comparison() -> None:
    """
    Generate a comparison chart for the three candidate models.

    Uses model_comparison.csv generated by train_model.py.
    """

    if not RESULTS_PATH.exists():
        print(
            "[WARNING] model_comparison.csv not found."
        )
        print(
            "[WARNING] Run train_model.py first."
        )
        return

    results_df = pd.read_csv(
        RESULTS_PATH
    )

    required_columns = [
        "model",
        "accuracy",
        "precision",
        "recall",
        "f1",
    ]

    missing = [
        column
        for column in required_columns
        if column not in results_df.columns
    ]

    if missing:
        print(
            "[WARNING] model_comparison.csv is missing:"
        )
        print(
            missing
        )
        return

    model_labels = [
        name.replace(
            "_",
            " ",
        ).title()
        for name in results_df["model"]
    ]

    metrics = [
        "accuracy",
        "precision",
        "recall",
        "f1",
    ]

    metric_labels = [
        "Accuracy",
        "Precision",
        "Recall",
        "F1-Score",
    ]

    x = np.arange(
        len(results_df)
    )

    width = 0.18

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    for i, metric in enumerate(metrics):

        offset = (
            i - 1.5
        ) * width

        bars = ax.bar(
            x + offset,
            results_df[metric],
            width,
            label=metric_labels[i],
        )

        ax.bar_label(
            bars,
            fmt="%.2f",
            padding=2,
            fontsize=8,
        )

    ax.set(
        ylabel="Score",
        title="Comparison of Machine Learning Models",
        xticks=x,
        xticklabels=model_labels,
        ylim=(0, 1),
    )

    ax.legend()

    ax.grid(
        axis="y",
        alpha=0.3,
    )

    fig.tight_layout()

    output_path = (
        FIGURES_DIR
        / "model_comparison.png"
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[SAVED] {output_path}"
    )


# ============================================================
# SHAP SUPPORT
# ============================================================

def get_feature_names_from_pipeline(
    pipeline: Pipeline,
) -> np.ndarray:
    """
    Retrieve the actual feature names after preprocessing,
    including one-hot encoded categorical features.
    """

    preprocessor = (
        pipeline
        .named_steps["preprocessor"]
    )

    return (
        preprocessor
        .get_feature_names_out()
    )


# ============================================================
# FIGURE 4 — SHAP SUMMARY
# ============================================================

def generate_shap_summary(
    model: Pipeline,
    X_test: pd.DataFrame,
) -> None:
    """
    Generate SHAP summary plot for the final saved model.

    The script automatically detects whether the final model is:

        Logistic Regression
        Random Forest
        Gradient Boosting

    and uses the appropriate SHAP explainer.
    """

    try:
        import shap
    except ImportError:
        print(
            "\n[WARNING] SHAP is not installed."
        )
        print(
            "Install it using:"
        )
        print(
            "    pip install shap"
        )
        return

    print(
        "\n[INFO] Generating SHAP explanation..."
    )

    try:
        # ----------------------------------------------------
        # Transform data using the fitted preprocessing stage
        # ----------------------------------------------------

        preprocessor = (
            model
            .named_steps["preprocessor"]
        )

        X_transformed = (
            preprocessor.transform(
                X_test
            )
        )

        feature_names = (
            preprocessor
            .get_feature_names_out()
        )

        X_transformed_df = pd.DataFrame(
            X_transformed,
            columns=feature_names,
            index=X_test.index,
        )

        # ----------------------------------------------------
        # Extract final estimator
        # ----------------------------------------------------

        estimator = (
            model
            .named_steps["model"]
        )

        model_name = (
            estimator.__class__.__name__
        )

        print(
            f"[INFO] SHAP model: {model_name}"
        )

        # ----------------------------------------------------
        # Choose appropriate SHAP explainer
        # ----------------------------------------------------

        if isinstance(
            estimator,
            (
                RandomForestClassifier,
                GradientBoostingClassifier,
            ),
        ):

            explainer = shap.TreeExplainer(
                estimator
            )

            shap_values = (
                explainer.shap_values(
                    X_transformed_df
                )
            )

            # Binary classification:
            # depending on SHAP version, the output may be
            # [samples, features, classes] or a list.
            if isinstance(
                shap_values,
                list,
            ):
                shap_values = shap_values[1]

            elif (
                isinstance(
                    shap_values,
                    np.ndarray,
                )
                and shap_values.ndim == 3
            ):
                shap_values = shap_values[:, :, 1]

        else:
            # Logistic Regression
            explainer = shap.LinearExplainer(
                estimator,
                X_transformed_df,
            )

            shap_values = (
                explainer.shap_values(
                    X_transformed_df
                )
            )

            if isinstance(
                shap_values,
                list,
            ):
                shap_values = shap_values[0]

            elif (
                isinstance(
                    shap_values,
                    np.ndarray,
                )
                and shap_values.ndim == 3
            ):
                shap_values = shap_values[:, :, 1]

        # ----------------------------------------------------
        # SHAP summary plot
        # ----------------------------------------------------

        plt.figure(
            figsize=(11, 8)
        )

        shap.summary_plot(
            shap_values,
            X_transformed_df,
            show=False,
            max_display=20,
        )

        plt.title(
            "SHAP Feature Contribution Summary - Delivery Failure Prediction"
        )

        plt.tight_layout()

        output_path = (
            FIGURES_DIR
            / "shap_summary.png"
        )

        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight",
        )

        plt.close()

        print(
            f"[SAVED] {output_path}"
        )

    except Exception as exc:
        print(
            "\n[WARNING] SHAP generation failed:"
        )
        print(
            f"  {type(exc).__name__}: {exc}"
        )


# ============================================================
# FINAL MODEL EVALUATION
# ============================================================

def evaluate_final_model(
    X: pd.DataFrame,
    y: pd.Series,
) -> None:

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Run train_model.py first."
        )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "LOADING FINAL MODEL"
    )

    print(
        "=" * 70
    )

    final_model = joblib.load(
        MODEL_PATH
    )

    print(
        f"[INFO] Model loaded from:"
    )

    print(
        MODEL_PATH
    )

    # --------------------------------------------------------
    # Same test split used by train_model.py
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    )

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    y_pred = final_model.predict(
        X_test
    )

    y_probability = (
        final_model.predict_proba(
            X_test
        )[:, 1]
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print(
        "\n"
        + "-" * 70
    )

    print(
        "FINAL MODEL TEST RESULTS"
    )

    print(
        "-" * 70
    )

    print(
        f"Accuracy   : {accuracy:.4f} ({accuracy * 100:.2f}%)"
    )

    print(
        f"Precision  : {precision:.4f}"
    )

    print(
        f"Recall     : {recall:.4f}"
    )

    print(
        f"F1-Score   : {f1:.4f}"
    )

    print(
        f"ROC-AUC    : {roc_auc:.4f}"
    )

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            y_pred,
            target_names=[
                "Success (0)",
                "Failure (1)",
            ],
            zero_division=0,
        )
    )

    print(
        "\nConfusion Matrix:"
    )

    cm = confusion_matrix(
        y_test,
        y_pred,
    )

    print(
        cm
    )

    # --------------------------------------------------------
    # Generate figures
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "GENERATING REPORT FIGURES"
    )

    print(
        "=" * 70
    )

    # Figure 1
    generate_confusion_matrix(
        y_test,
        y_pred,
    )

    # Figure 2
    generate_roc_curve(
        y_test,
        y_probability,
    )

    # Figure 3
    generate_model_comparison()

    # Figure 4
    generate_shap_summary(
        final_model,
        X_test,
    )

    # --------------------------------------------------------
    # Final information
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "FIGURE GENERATION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"\nAll figures are stored in:"
    )

    print(
        FIGURES_DIR
    )

    print(
        "\nGenerated files:"
    )

    print(
        "  1. confusion_matrix.png"
    )

    print(
        "  2. roc_curve.png"
    )

    print(
        "  3. model_comparison.png"
    )

    print(
        "  4. shap_summary.png"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    try:

        X, y = load_dataset()

        evaluate_final_model(
            X,
            y,
        )

        return 0

    except Exception as exc:

        print(
            "\n"
            + "=" * 70
        )

        print(
            "ERROR"
        )

        print(
            "=" * 70
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )