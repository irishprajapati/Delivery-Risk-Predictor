import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
df = pd.read_csv("logistics_dataset_kathmandu.csv")

# Split features and target
X = df.drop("delivery_failure", axis=1)
y = df["delivery_failure"]

# Categorical columns (text features)
categorical_cols = [
    "delivery_time",
    "address_clarity",
    "payment_method",
    "order_value",
    "area_density",
    "accessibility",
    "weather_condition",
    "traffic_level"
]

# Numerical columns
numerical_cols = [
    "address_length",
    "contact_valid"
]

# Preprocessing (THIS fixes your error permanently)
preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
    ("num", "passthrough", numerical_cols)
])

# Model
model = RandomForestClassifier(n_estimators=100, random_state=42)

# Pipeline (CRITICAL PART)
pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", model)
])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
pipeline.fit(X_train, y_train)

# Predictions
y_pred = pipeline.predict(X_test)

# Evaluation
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# Save FULL pipeline (not just model)
joblib.dump(pipeline, "delivery_model.pkl")

print("Model saved successfully as delivery_model.pkl")