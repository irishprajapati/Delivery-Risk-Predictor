from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
import joblib

df = pd.read_csv('logistics_dataset_kathmandu.csv')

label_encoders = {}

for column in df.select_dtypes(include=['object', 'string']).columns:
    le = LabelEncoder()
    df[column] = le.fit_transform(df[column])
    label_encoders[column] = le

# DEBUG
print(df.head())
print(df.dtypes)

X = df.drop('delivery_failure', axis=1)
y = df['delivery_failure']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

joblib.dump(model, "delivery_model.pkl")
print("Model saved successfully!")