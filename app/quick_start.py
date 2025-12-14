#!/usr/bin/env python
"""
QUICK START - License Plate Detection API
Works WITHOUT database - test segmentation and OCR
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import cv2
import numpy as np
import torch
from pathlib import Path
from ultralytics import YOLO
from datetime import datetime
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.ocr import plate_ocr

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="License Plate Detection System",
    description="Segmentation + OCR (No Database Required)",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Device
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")

# Directories
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Model
MODEL_PATH = str(Path(__file__).parent.parent / "model" / "carplate-model.pt")
logger.info(f"Loading model: {MODEL_PATH}")

try:
    model = YOLO(MODEL_PATH)
    model.to(device)
    logger.info(f"✓ Model loaded on {device}")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None

# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "License Plate Detection API",
        "version": "1.0.0",
        "endpoints": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "device": device,
        "model_loaded": model is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/detect-plates")
async def detect_plates(file: UploadFile = File(...)):
    """
    Detect and read license plates from image
    Returns: plate number + OCR confidence + detection confidence
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
        
        h, w = image.shape[:2]
        
        # Run inference
        logger.info(f"Running inference on {w}x{h} image")
        results = model.predict(image, conf=0.65, iou=0.5, verbose=False)
        result = results[0]
        
        response_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "image_shape": [h, w, 3],
            "plates_detected": [],
            "total_plates": 0
        }
        
        if result.boxes is not None:
            boxes = result.boxes.data.cpu().numpy()
            logger.info(f"Found {len(boxes)} detection(s)")
            
            # Get segmentation masks if available
            masks = result.masks
            
            for idx, box in enumerate(boxes):
                x1, y1, x2, y2, conf, cls_id = box
                
                # Filter by size
                box_width = x2 - x1
                box_height = y2 - y1
                min_size = min(h, w) * 0.05
                
                if box_width < min_size or box_height < min_size:
                    logger.debug(f"Skipping small box: {box_width}x{box_height}")
                    continue
                
                # Extract segmented plate region if masks available
                plate_region = None
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
                            logger.debug(f"Extracted segmented plate: {x_max-x_min:.0f}x{y_max-y_min:.0f}")
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
                    logger.debug(f"Using bbox region: {x2_padded-x1_padded:.0f}x{y2_padded-y1_padded:.0f}")
                
                # Read plate from cropped region
                if plate_region is None or plate_region.size == 0:
                    logger.debug("Plate region is empty, skipping")
                    continue
                
                # Save the segmented/cropped plate image for visualization
                crop_filename = f"plate_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                crop_filepath = RESULTS_DIR / crop_filename
                cv2.imwrite(str(crop_filepath), plate_region)
                logger.debug(f"Saved cropped plate to: {crop_filename}")
                
                plate_text, ocr_conf = plate_ocr.read_plate_from_crop(plate_region)
                
                # Filter by confidence and validity
                if not plate_text or ocr_conf < 0.35:
                    logger.debug(f"Low OCR confidence: {ocr_conf}")
                    continue
                
                if not plate_ocr.validate_plate(plate_text):
                    logger.debug(f"Invalid plate format: {plate_text}")
                    continue
                
                # Add to results
                plate_result = {
                    "id": idx,
                    "plate_number": plate_text,
                    "detection_confidence": float(conf),
                    "ocr_confidence": float(ocr_conf),
                    "cropped_plate_image": crop_filename,
                    "bbox": {
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2)
                    }
                }
                
                response_data["plates_detected"].append(plate_result)
                logger.info(f"✓ Plate detected: {plate_text} ({ocr_conf:.0%} confidence) - Saved crop: {crop_filename}")
        
        response_data["total_plates"] = len(response_data["plates_detected"])
        
        # Save annotated image
        annotated = result.plot()
        filename = f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = RESULTS_DIR / filename
        cv2.imwrite(str(filepath), annotated)
        response_data["segmented_image"] = filename
        
        logger.info(f"✓ Detection complete: {response_data['total_plates']} plates")
        return response_data
        
    except Exception as e:
        logger.error(f"Detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")

@app.get("/results/{filename}")
async def get_result(filename: str):
    filepath = RESULTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    return FileResponse(str(filepath))

# Run
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("License Plate Detection API (Fast Start)".center(70))
    print("="*70)
    print(f"\n✓ Device: {device}")
    print(f"✓ Model: Loaded")
    print(f"✓ OCR: Ready")
    print(f"\n📍 API: http://localhost:8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
