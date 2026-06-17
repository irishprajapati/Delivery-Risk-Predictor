from fastapi import FastAPI, Depends
from app.schemas import PredictionInput
from app.model import predict
from app.auth import fake_login
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.model import get_feature_importance
from app.logging_service import save_log

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API is working"}

@app.post("/login")
def login(username: str, password: str):
    return fake_login(username, password) ## -> why fake_login? 

@app.post("/predict")
def predict_route(data: PredictionInput):
    result = predict(data)

    # Log only successful predictions
    if result.get("success"):
        save_log({
            "input": data.model_dump(),
            "prediction": result["prediction"],
            "probability": result["probability"],
            "risk": result["risk"],
            "reasons": result["reasons"]
        })

    return result

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    errors = []

    for err in exc.errors():
        field = err["loc"][-1]
        message = err["msg"]

        errors.append(f"{field}: {message}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Invalid input data",
            "errors": errors
        }
    )

@app.get("/feature-importance")
def feature_importance():
    features = get_feature_importance()

    if features is None:
        return {
            "success": False,
            "error": "feature_importance_failed"
        }

    return {
        "success": True,
        "model_insight": "Global feature importance based on RandomForest impurity reduction",
        "features": features[:10]
    }