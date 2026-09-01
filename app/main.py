from pathlib import Path

from dotenv import load_dotenv
import os

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

print("SECRET_KEY:", os.getenv("SECRET_KEY"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import config  # noqa: F401 — ensure env is loaded before route imports
from app.database import Base, engine
from app.routes.route_api import router as route_router
from app.routes import predict, auth, history, explain, rider

# Create tables -> in database
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # NOT "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(explain.router)
app.include_router(route_router)
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(rider.router)


# entry point of the file
@app.get("/")
def home():
    return {"message": "API is working"}
