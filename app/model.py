from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="admin")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)

    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    total_orders = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)
    failed_deliveries = Column(Integer, default=0, nullable=False)
    unreachable_count = Column(Integer, default=0, nullable=False)
    cancellation_count = Column(Integer, default=0, nullable=False)
    last_successful_delivery = Column(DateTime)
    orders = relationship("Order", back_populates="customer")
class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    risk_score = Column(Float, default=0.0)

    items = relationship("Item", back_populates="category")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="items")
    orders = relationship("Order", back_populates="item")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)

    is_cod = Column(Boolean, default=True, nullable=False)
    prepaid_amount = Column(Float, default=0.0, nullable=False)

    address = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

    risk_score = Column(Float)
    risk_level = Column(String)
    status = Column(String, default="placed")
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    item = relationship("Item", back_populates="orders")

    delivery = relationship("Delivery", back_populates="order", uselist=False)
    location = relationship("DeliveryLocation", back_populates="order", uselist=False)

    environment_snapshots = relationship(
        "EnvironmentSnapshot",
        back_populates="order"
    )

    operational_snapshots = relationship(
        "OperationalSnapshot",
        back_populates="order"
    )

    predictions = relationship("Prediction", back_populates="order")


class Rider(Base):
    __tablename__ = "riders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    area = Column(String)

    is_active = Column(Boolean, default=True)
    max_orders_per_day = Column(Integer, default=20)
    current_order_count = Column(Integer, default=0)

    completed_orders = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)

    deliveries = relationship("Delivery", back_populates="rider")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    rider_id = Column(Integer, ForeignKey("riders.id"))

    status = Column(String, default="unassigned")
    attempt_count = Column(Integer, default=0)
    failure_reason = Column(String)

    distance_km = Column(Float)
    estimated_duration = Column(Float)
    actual_duration = Column(Float)

    assigned_at = Column(DateTime)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="delivery")
    rider = relationship("Rider", back_populates="deliveries")
class DeliveryLocation(Base):
    __tablename__ = "delivery_locations"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)

    address = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

    address_quality = Column(Float)
    distance_km = Column(Float)
    estimated_duration = Column(Float)
    location_success_rate = Column(Float)

    order = relationship("Order", back_populates="location")


class EnvironmentSnapshot(Base):
    __tablename__ = "environment_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    weather = Column(String)
    rainfall = Column(Float)
    temperature = Column(Float)
    traffic_level = Column(String)

    recorded_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="environment_snapshots")

class OperationalSnapshot(Base):
    __tablename__ = "operational_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    rider_load = Column(Integer, default=0)
    hub_delay_minutes = Column(Float, default=0)
    route_status = Column(String)
    vehicle_status = Column(String)

    recorded_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="operational_snapshots")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    input_data = Column(JSON)
    prediction = Column(Integer)
    probability = Column(Float)
    risk = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="predictions")