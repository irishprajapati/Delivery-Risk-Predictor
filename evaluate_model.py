#!/usr/bin/env python3
"""
Evaluate the trained delivery failure prediction model.

Usage:
    python evaluate_model.py

Loads app/ml/delivery_model.pkl, evaluates on a held-out test split
(same random_state=42, test_size=0.2 as train_model.py), and prints:
  - accuracy, precision, recall, f1-score
  - confusion matrix
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from app.utils.feature_engineering import MODEL_FEATURE_COLUMNS, build_model_features

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "app" / "data" / "delivery_data.csv"
MODEL_PATH = PROJECT_ROOT / "app" / "ml" / "delivery_model.pkl"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    feature_rows = [build_model_features(row) for row in df.to_dict(orient="records")]
    X = pd.DataFrame(feature_rows)[MODEL_FEATURE_COLUMNS]
    y = df["failed"]
    return X, y


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Train first with: python -m app.ml.train_model"
        )
    return joblib.load(MODEL_PATH)


def print_section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_confusion_matrix(cm: list[list[int]], labels: list[str]) -> None:
    col_width = max(len(l) for l in labels) + 4
    header = " " * col_width + "".join(f"Pred:{l:>8}" for l in labels)
    print(header)
    print("-" * len(header))
    for i, label in enumerate(labels):
        row = f"Actual:{label:<{col_width - 7}}"
        row += "".join(f"{cm[i][j]:>12}" for j in range(len(labels)))
        print(row)


def main() -> int:
    print_section("MODEL EVALUATION — Delivery Failure Predictor")
    print(f"  Dataset : {DATA_PATH}")
    print(f"  Model   : {MODEL_PATH}")
    print(f"  Split   : test_size={TEST_SIZE}, random_state={RANDOM_STATE}")

    try:
        X, y = load_dataset()
        model = load_model()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}")
        return 1

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    print_section("DATASET OVERVIEW")
    print(f"  Total samples  : {len(X)}")
    print(f"  Train samples  : {len(X_train)}")
    print(f"  Test samples   : {len(X_test)}")
    print(f"  Failure rate   : {y.mean():.2%} (full dataset)")
    print(f"  Test failures  : {int(y_test.sum())} / {len(y_test)}")

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print_section("METRICS (Test Set)")
    print(f"  Accuracy   : {accuracy:.4f}  ({accuracy * 100:.2f}%)")
    print(f"  Precision  : {precision:.4f}  (of predicted failures, how many are correct)")
    print(f"  Recall     : {recall:.4f}  (of actual failures, how many were caught)")
    print(f"  F1-Score   : {f1:.4f}  (harmonic mean of precision & recall)")

    print_section("CONFUSION MATRIX")
    print("  Rows = actual, Columns = predicted")
    print("  0 = success likely, 1 = failure likely\n")
    print_confusion_matrix(cm.tolist(), labels=["0 (success)", "1 (failure)"])
    print()
    print(f"  True Negatives  (correct success) : {cm[0][0]}")
    print(f"  False Positives (false alarm)     : {cm[0][1]}")
    print(f"  False Negatives (missed failure)  : {cm[1][0]}")
    print(f"  True Positives  (correct failure) : {cm[1][1]}")

    print_section("CLASSIFICATION REPORT")
    print(classification_report(y_test, y_pred, target_names=["Success (0)", "Failure (1)"]))

    print_section("PROBABILITY DISTRIBUTION (Test Set)")
    print(f"  Mean failure probability : {y_prob.mean():.4f}")
    print(f"  Min failure probability  : {y_prob.min():.4f}")
    print(f"  Max failure probability  : {y_prob.max():.4f}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
