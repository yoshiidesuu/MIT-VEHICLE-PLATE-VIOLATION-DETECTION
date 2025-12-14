# Database Models for Traffic Violations System

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, Enum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base

class ViolationType(str, enum.Enum):
    SPEEDING = "speeding"
    RED_LIGHT = "red_light"
    PARKING = "parking"
    NO_SEATBELT = "no_seatbelt"
    EXPIRED_LICENSE = "expired_license"
    UNREGISTERED = "unregistered"
    OTHER = "other"

class Vehicle(Base):
    """Vehicle/License Plate Information"""
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(50))  # Car, Motorcycle, Truck, etc.
    color = Column(String(50))
    owner_name = Column(String(100))
    owner_phone = Column(String(20))
    owner_email = Column(String(100))
    registration_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Violation(Base):
    """Traffic Violations Record"""
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), index=True, nullable=False)
    violation_type = Column(String(50), nullable=False)
    violation_date = Column(DateTime, nullable=False)
    location = Column(String(200))
    speed = Column(Float)  # For speeding violations
    speed_limit = Column(Float)
    fine_amount = Column(Float)
    is_paid = Column(Boolean, default=False)
    paid_date = Column(DateTime, nullable=True)
    image_path = Column(String(500))
    description = Column(Text)
    officer_id = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class DetectionLog(Base):
    """Log of all detections for tracking"""
    __tablename__ = "detection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), index=True, nullable=True)
    confidence = Column(Float)
    ocr_confidence = Column(Float)
    image_path = Column(String(500))
    has_violations = Column(Boolean, default=False)
    violation_count = Column(Integer, default=0)
    detection_date = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
