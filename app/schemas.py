# Schemas for request/response validation

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models import ViolationType

# ==================== Vehicle Schemas ====================

class VehicleBase(BaseModel):
    plate_number: str = Field(..., min_length=6, max_length=20)
    vehicle_type: Optional[str] = None
    color: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    color: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: int
    registration_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Violation Schemas ====================

class ViolationBase(BaseModel):
    plate_number: str
    violation_type: str
    violation_date: datetime
    location: Optional[str] = None
    speed: Optional[float] = None
    speed_limit: Optional[float] = None
    fine_amount: Optional[float] = None
    description: Optional[str] = None

class ViolationCreate(ViolationBase):
    pass

class ViolationResponse(ViolationBase):
    id: int
    is_paid: bool
    paid_date: Optional[datetime] = None
    image_path: Optional[str] = None
    officer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Detection Schemas ====================

class PlateDetectionResult(BaseModel):
    """Result of plate detection and OCR"""
    plate_number: str = Field(..., description="Detected plate number")
    ocr_confidence: float = Field(..., ge=0, le=1, description="OCR confidence score")
    detection_confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    bbox: dict = Field(..., description="Bounding box coordinates")

class ViolationCheckResult(BaseModel):
    """Result of checking violations for a plate"""
    plate_number: str
    has_violations: bool
    violation_count: int
    violations: List[ViolationResponse] = []
    total_fine: float = 0.0
    last_violation_date: Optional[datetime] = None

class DetectionWithViolations(BaseModel):
    """Complete detection result with violation check"""
    plate: PlateDetectionResult
    violations: ViolationCheckResult
    is_flagged: bool  # True if has unpaid violations
    alert_message: Optional[str] = None

# ==================== Prediction Schemas ====================

class PlateSegmentationResult(BaseModel):
    """Result of plate segmentation from image"""
    success: bool
    timestamp: datetime
    image_shape: List[int]
    detections: List[dict]  # Plate detections
    plate_results: Optional[List[PlateDetectionResult]] = None
    result_image: Optional[str] = None

# ==================== Statistics Schemas ====================

class ViolationStats(BaseModel):
    """Violation statistics"""
    total_plates_detected: int
    plates_with_violations: int
    total_violations: int
    unpaid_violations: int
    total_fines: float
    detection_accuracy: float
