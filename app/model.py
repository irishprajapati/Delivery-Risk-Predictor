from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .database import Base
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # hashed password
    is_active = Column(Boolean, default=True)
    role = Column(String, default="admin")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    input_data = Column(JSON)
    prediction = Column(Integer)
    probability = Column(Float)
    risk = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String, unique=True)
    total_orders = Column(Integer, default=0, nullable=False)
    failed_deliveries = Column(Integer, default=0, nullable=False)
    failure_rate = Column(Float, default=0.0, nullable=False)