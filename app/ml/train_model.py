import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score

from app.utils.feature_engineering import MODEL_FEATURE_COLUMNS, build_model_features

DATA_PATH = "app/data/delivery_data.csv"
MODEL_PATH = "app/ml/delivery_model.pkl"

df = pd.read_csv(DATA_PATH)
print("[INFO] Raw data loaded:")
print(df.head())

feature_rows = [build_model_features(row) for row in df.to_dict(orient="records")]
X = pd.DataFrame(feature_rows)[MODEL_FEATURE_COLUMNS]
y = df["failed"]

print("[INFO] Model feature columns:")
print(list(X.columns))

print("[INFO] Engineered features sample:")
print(X.head())

categorical_cols = MODEL_FEATURE_COLUMNS

preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
])

model = Pipeline([
    ("preprocessor", preprocessor),
    ("model", RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
    )),
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model.fit(X_train, y_train)
print("[INFO] Model trained")

cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
print(f"[INFO] Cross-val Accuracy: {cv_scores.mean():.4f}")

y_pred = model.predict(X_test)
print(f"[INFO] Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"[INFO] Precision: {precision_score(y_test, y_pred):.4f}")
print(f"[INFO] Recall: {recall_score(y_test, y_pred):.4f}")

joblib.dump(model, MODEL_PATH)
print(f"[INFO] Model saved to {MODEL_PATH}")
