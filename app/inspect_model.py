# inspect_model.py

import joblib

pipeline = joblib.load("../delivery_model.pkl")

preprocessor = pipeline.named_steps["preprocessor"]

print(preprocessor.named_transformers_["cat"].get_feature_names_out())