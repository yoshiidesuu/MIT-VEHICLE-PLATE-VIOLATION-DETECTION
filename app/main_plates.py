# Enhanced Main API with Plate Detection and Violation Checking

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import torch
import os
from pathlib import Path
from ultralytics import YOLO
from datetime import datetime
import logging
from sqlalchemy.orm import Session

# Import our modules
from app.database import get_db, init_db, engine
from app.models import Base, Violation, Vehicle, ViolationType
from app.ocr import detect_and_read_plate, plate_ocr
from app.violations import check_plate_violations, add_violation, register_vehicle, get_vehicle_info
from app.schemas import PlateDetectionResult, ViolationCheckResult, DetectionWithViolations

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Traffic Violation Detection System",
    description="YOLO Plate Detection + OCR + Violation Database",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check GPU availability
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")
if torch.cuda.is_available():
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

# Create directories
RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Load Custom License Plate Detection Model
MODEL_PATH = str(Path(__file__).parent.parent / "model" / "carplate-model.pt")
logger.info(f"Loading model from: {MODEL_PATH}")

try:
    model = YOLO(MODEL_PATH)
    model.to(device)
    logger.info(f"✓ License Plate Model loaded successfully on {device}")
    logger.info(f"  Model: {MODEL_PATH}")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None

# Initialize database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

# ==================== Health & Status Endpoints ====================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("🚀 Application started")
    try:
        init_db()
    except:
        pass

@app.get("/")
async def root():
    """Root endpoint - serves dashboard"""
    dashboard_path = Path(__file__).parent.parent / "dashboard.html"
    if dashboard_path.exists():
        try:
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
    
    # Fallback to JSON if dashboard not found
    return {
        "status": "ok",
        "message": "License Plate Detection System",
        "version": "2.0.0",
        "docs": "http://localhost:8000/api/docs",
        "dashboard": "http://localhost:8000/",
        "api_base": "http://localhost:8000"
    }

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "status": "ok",
        "service": "License Plate Detection System",
        "version": "2.0.0",
        "features": {
            "plate_detection": "Detect and read license plates from images",
            "violation_checking": "Automatically check if detected plates have violations",
            "cropped_plate_images": "Get segmented/cropped plate images",
            "owner_lookup": "Find vehicle owner information",
            "database": "1185+ violations for 275+ vehicles"
        },
        "endpoints": {
            "detection": "/detect-plates (POST) - Detect plates + check violations + get cropped image",
            "cropped_plate": "/cropped-plate/{filename} (GET) - View cropped license plate image",
            "cropped_plates_list": "/api/cropped-plates (GET) - List all cropped plate images",
            "violations_check": "/violations/check/{plate} (GET) - Check violations for a plate",
            "violations_add": "/violations/add (POST) - Add new violation",
            "vehicle_info": "/vehicles/info/{plate} (GET) - Get owner information",
            "vehicle_register": "/vehicles/register (POST) - Register new vehicle",
            "database_status": "/database/status (GET) - Database statistics",
            "health": "/health (GET) - Health check",
            "gpu_info": "/gpu-info (GET) - GPU information"
        },
        "docs_url": "http://localhost:8000/api/docs",
        "dashboard": "http://localhost:8000/",
        "database": {
            "total_vehicles": "275+",
            "total_violations": "1185+",
            "violation_types": "20+ different types"
        }
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "gpu_memory": f"{torch.cuda.memory_allocated() / 1e9:.2f}GB" if torch.cuda.is_available() else "N/A"
    }

@app.get("/gpu-info")
async def gpu_info():
    """Get GPU information"""
    return {
        "gpu_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_version": torch.version.cuda,
        "pytorch_version": torch.__version__,
        "memory_allocated": f"{torch.cuda.memory_allocated() / 1e9:.2f}GB" if torch.cuda.is_available() else "N/A"
    }

# ==================== Results Serving ====================

@app.get("/results/{filename}")
async def get_result_image(filename: str):
    """Serve result images"""
    results_dir = Path(__file__).parent.parent / "results"
    filepath = results_dir / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(str(filepath), media_type="image/jpeg")

@app.get("/cropped-plate/{filename}")
async def get_cropped_plate(filename: str):
    """
    Get cropped license plate image
    
    Args:
        filename: Name of the cropped plate image
    
    Returns:
        JPEG image of the cropped plate
    """
    results_dir = Path(__file__).parent.parent / "results"
    filepath = results_dir / filename
    
    # Security check: ensure filename doesn't contain path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Cropped plate image not found")
    
    logger.info(f"Serving cropped plate: {filename}")
    return FileResponse(str(filepath), media_type="image/jpeg")

@app.get("/api/cropped-plates")
async def list_cropped_plates():
    """
    List all available cropped plate images
    
    Returns:
        List of available cropped plate image filenames
    """
    results_dir = Path(__file__).parent.parent / "results"
    
    if not results_dir.exists():
        return {
            "plates": [],
            "count": 0
        }
    
    # Find all cropped plate images (pattern: plate_*_*.jpg)
    cropped_plates = sorted([
        f.name for f in results_dir.glob("plate_*.jpg") 
        if f.name.startswith("plate_") and "_" in f.name
    ], reverse=True)  # Most recent first
    
    return {
        "plates": cropped_plates,
        "count": len(cropped_plates),
        "view_url_template": "/cropped-plate/{filename}"
    }

# ==================== Plate Detection Endpoints ====================

@app.post("/detect-plates")
async def detect_plates(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Detect and read license plates from image - COMPLETE SOLUTION FOR FLUTTER
    
    Returns all data needed by mobile app:
        - Original image
        - Segmented/detected plate image
        - Plate number (OCR)
        - Violations (count, types, fines)
        - Owner information (name, ID, phone, location, email)
        - Confidence scores
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Read image
        contents = await file.read()
        image_array = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Run inference with higher confidence threshold for segmentation
        results = model.predict(image, conf=0.65, iou=0.5)
        result = results[0]
        
        response_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "image_shape": list(image.shape),
            "plates_detected": [],
            "total_plates": 0
        }
        
        if result.boxes is not None:
            boxes = result.boxes.data.cpu().numpy()
            masks = result.masks
            h, w = image.shape[:2]
            
            for idx, box in enumerate(boxes):
                x1, y1, x2, y2, conf, cls_id = box
                
                # Filter by minimum box size (plates must be reasonably sized)
                box_width = x2 - x1
                box_height = y2 - y1
                min_size = min(h, w) * 0.05  # At least 5% of image dimension
                
                if box_width < min_size or box_height < min_size:
                    logger.debug(f"Skipping small detection: {box_width}x{box_height}")
                    continue
                
                detection_bbox = {
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                    "confidence": float(conf)
                }
                
                # Extract segmented plate region if masks available
                plate_region = None
                cropped_filename = None
                
                if masks is not None and idx < len(masks.data):
                    try:
                        # Get mask for this detection
                        mask = masks.data[idx].cpu().numpy()
                        
                        # Get bounding box of the mask
                        mask_points = np.where(mask > 0)
                        if len(mask_points[0]) > 0:
                            y_min, y_max = mask_points[0].min(), mask_points[0].max()
                            x_min, x_max = mask_points[1].min(), mask_points[1].max()
                            
                            # Add small padding to mask
                            padding = 5
                            y_min = max(0, y_min - padding)
                            y_max = min(h, y_max + padding)
                            x_min = max(0, x_min - padding)
                            x_max = min(w, x_max + padding)
                            
                            # Crop to segmented region
                            plate_region = image[int(y_min):int(y_max), int(x_min):int(x_max)]
                            logger.debug(f"Extracted segmented plate: {int(x_max-x_min)}x{int(y_max-y_min)}")
                    except Exception as e:
                        logger.debug(f"Could not extract mask, using bbox: {e}")
                
                # If no mask, use bounding box with padding
                if plate_region is None:
                    padding = int(max(box_width, box_height) * 0.1)
                    x1_padded = max(0, int(x1) - padding)
                    y1_padded = max(0, int(y1) - padding)
                    x2_padded = min(w, int(x2) + padding)
                    y2_padded = min(h, int(y2) + padding)
                    
                    plate_region = image[int(y1_padded):int(y2_padded), int(x1_padded):int(x2_padded)]
                    logger.debug(f"Using bbox region: {int(x2_padded-x1_padded)}x{int(y2_padded-y1_padded)}")
                
                # Read plate from cropped region
                if plate_region is None or plate_region.size == 0:
                    logger.debug("Plate region is empty, skipping")
                    continue
                
                # Save the segmented/cropped plate image for visualization
                cropped_filename = f"plate_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cropped_filepath = Path(__file__).parent.parent / "results" / cropped_filename
                cropped_filepath.parent.mkdir(exist_ok=True)
                cv2.imwrite(str(cropped_filepath), plate_region)
                logger.debug(f"Saved cropped plate to: {cropped_filename}")
                
                # Apply OCR to cropped plate region
                plate_text, ocr_conf = plate_ocr.read_plate_from_crop(plate_region)
                
                # Filter by OCR confidence and plate validation
                if not plate_text or ocr_conf < 0.35:
                    logger.debug(f"Skipping low OCR confidence: {ocr_conf:.2f}")
                    continue
                
                # Validate plate format
                if not plate_ocr.validate_plate(plate_text):
                    logger.debug(f"Invalid plate format: {plate_text}")
                    continue
                    
                # Check violations in database
                violations = check_plate_violations(db, plate_text)
                
                # Get vehicle/owner information
                vehicle_info = get_vehicle_info(db, plate_text)
                
                # Build complete plate result
                plate_result = {
                    "id": idx,
                    "plate_number": plate_text,
                    "detection_confidence": float(conf),
                    "ocr_confidence": float(ocr_conf),
                    "cropped_plate_image": cropped_filename,
                    "bbox": detection_bbox,
                    
                    # VIOLATION INFORMATION
                    "violations": {
                        "has_violations": violations.has_violations,
                        "violation_count": violations.violation_count,
                        "total_fine": violations.total_fine,
                        "is_flagged": violations.has_violations,
                        "last_violation_date": violations.last_violation_date.isoformat() if violations.last_violation_date else None,
                        "violation_details": [
                            {
                                "id": v.id,
                                "type": v.violation_type,
                                "date": v.violation_date.isoformat(),
                                "location": v.location,
                                "fine_amount": v.fine_amount,
                                "is_paid": v.is_paid,
                                "description": v.description,
                                "speed": v.speed,
                                "speed_limit": v.speed_limit
                            }
                            for v in violations.violations
                        ] if violations.violations else []
                    },
                    
                    # OWNER INFORMATION
                    "owner_info": {
                        "found": vehicle_info.get("found", False),
                        "owner_name": vehicle_info.get("owner_name"),
                        "owner_id": vehicle_info.get("id"),
                        "owner_phone": vehicle_info.get("owner_phone"),
                        "owner_email": vehicle_info.get("owner_email"),
                        "vehicle_type": vehicle_info.get("vehicle_type"),
                        "vehicle_color": vehicle_info.get("color"),
                        "is_active": vehicle_info.get("is_active", True)
                    },
                    
                    # ALERT STATUS
                    "alert_status": {
                        "is_flagged": violations.has_violations,
                        "alert_level": "high" if violations.has_violations else "normal",
                        "message": f"⚠️ {violations.violation_count} violations found" if violations.has_violations else "✓ No violations"
                    }
                }
                
                response_data["plates_detected"].append(plate_result)
        
        response_data["total_plates"] = len(response_data["plates_detected"])
        
        # Save result image (segmented/detected)
        annotated_image = result.plot()
        filename = f"plate_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = RESULTS_DIR / filename
        cv2.imwrite(str(filepath), annotated_image)
        response_data["segmented_image"] = filename
        
        logger.info(f"✓ Detection complete: {response_data['total_plates']} plates detected")
        return response_data
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")

# ==================== Violation Check Endpoints ====================

@app.get("/violations/check/{plate_number}")
async def check_violations(plate_number: str, db: Session = Depends(get_db)):
    """
    Check if a plate has violations in the database
    
    Args:
        plate_number: License plate number (e.g., "ABC1234")
    
    Returns:
        Violation information and status
    """
    violations = check_plate_violations(db, plate_number)
    
    return {
        "plate_number": violations.plate_number,
        "has_violations": violations.has_violations,
        "violation_count": violations.violation_count,
        "total_fine": violations.total_fine,
        "last_violation": violations.last_violation_date,
        "violations": [v.dict() for v in violations.violations] if violations.violations else []
    }

@app.post("/violations/add")
async def add_new_violation(
    plate_number: str = Query(...),
    violation_type: str = Query(...),
    location: str = Query(None),
    speed: float = Query(None),
    speed_limit: float = Query(None),
    fine_amount: float = Query(None),
    description: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Add a new violation record
    
    Args:
        plate_number: License plate
        violation_type: Type of violation (speeding, red_light, parking, etc.)
        Other optional fields for violation details
    """
    success, message = add_violation(
        db,
        plate_number,
        violation_type,
        datetime.now(),
        location=location,
        speed=speed,
        speed_limit=speed_limit,
        fine_amount=fine_amount,
        description=description
    )
    
    return {
        "success": success,
        "message": message,
        "plate_number": plate_number
    }

# ==================== Vehicle Management Endpoints ====================

@app.post("/vehicles/register")
async def register_new_vehicle(
    plate_number: str = Query(...),
    vehicle_type: str = Query(None),
    color: str = Query(None),
    owner_name: str = Query(None),
    owner_phone: str = Query(None),
    owner_email: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Register a new vehicle
    """
    success, message = register_vehicle(
        db,
        plate_number,
        vehicle_type=vehicle_type,
        color=color,
        owner_name=owner_name,
        owner_phone=owner_phone,
        owner_email=owner_email
    )
    
    return {
        "success": success,
        "message": message,
        "plate_number": plate_number
    }

@app.get("/vehicles/info/{plate_number}")
async def get_vehicle(plate_number: str, db: Session = Depends(get_db)):
    """
    Get vehicle information
    """
    info = get_vehicle_info(db, plate_number)
    return info

# ==================== Database Status ====================

@app.get("/database/status")
async def database_status(db: Session = Depends(get_db)):
    """Get database status and statistics"""
    try:
        vehicle_count = db.query(Vehicle).count()
        violation_count = db.query(Violation).count()
        
        return {
            "status": "connected",
            "total_vehicles": vehicle_count,
            "total_violations": violation_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
