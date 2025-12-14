from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import torch
import os
from pathlib import Path
from ultralytics import YOLO
import io
from PIL import Image
import json
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YOLO Instance Segmentation API",
    description="API for instance segmentation with YOLO 12",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check GPU availability
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")
if torch.cuda.is_available():
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"CUDA Version: {torch.version.cuda}")

# Create results directory
RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Load YOLO model
MODEL_PATH = "yolov8n-seg.pt"  # You can change to yolo12 when available
try:
    model = YOLO(MODEL_PATH)
    model.to(device)
    logger.info(f"Model loaded successfully on {device}")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard"""
    return {"status": "ok", "message": "YOLO Instance Segmentation API", "endpoints": "/docs"}


@app.get("/dashboard")
async def dashboard():
    """Serve the web dashboard"""
    dashboard_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path, media_type="text/html")
    else:
        return HTMLResponse("""
        <html>
            <head><title>YOLO Dashboard</title></head>
            <body>
                <h1>Dashboard not found</h1>
                <p><a href="/docs">View API Documentation</a></p>
            </body>
        </html>
        """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "gpu_memory": f"{torch.cuda.memory_allocated() / 1e9:.2f}GB" if torch.cuda.is_available() else "N/A"
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Perform instance segmentation on uploaded image
    
    Returns:
        - segmented_image: Base64 encoded image with segmentation masks
        - masks: List of segmentation masks
        - bboxes: List of bounding boxes
        - classes: Detected class names
        - confidence: Confidence scores
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
        
        # Run inference
        results = model.predict(image, conf=0.5)
        
        # Process results
        result = results[0]
        
        # Prepare response data
        response_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "image_shape": image.shape,
            "detections": []
        }
        
        if result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            boxes = result.boxes.data.cpu().numpy()
            
            for idx, (box, mask) in enumerate(zip(boxes, masks)):
                x1, y1, x2, y2, conf, cls_id = box
                detection = {
                    "id": idx,
                    "class": model.names[int(cls_id)],
                    "confidence": float(conf),
                    "bbox": {
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2)
                    }
                }
                response_data["detections"].append(detection)
        
        # Save segmented image
        annotated_image = result.plot()
        filename = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = RESULTS_DIR / filename
        cv2.imwrite(str(filepath), annotated_image)
        response_data["result_image"] = filename
        
        logger.info(f"Prediction completed: {len(response_data['detections'])} objects detected")
        return response_data
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/predict-batch")
async def predict_batch(files: list[UploadFile] = File(...)):
    """Process multiple images at once"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    results = []
    for file in files:
        try:
            contents = await file.read()
            image_array = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                results.append({"filename": file.filename, "error": "Invalid image format"})
                continue
            
            pred_results = model.predict(image, conf=0.5)
            result = pred_results[0]
            
            detections = []
            if result.masks is not None:
                boxes = result.boxes.data.cpu().numpy()
                for box in boxes:
                    x1, y1, x2, y2, conf, cls_id = box
                    detections.append({
                        "class": model.names[int(cls_id)],
                        "confidence": float(conf),
                        "bbox": {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)}
                    })
            
            results.append({
                "filename": file.filename,
                "success": True,
                "detection_count": len(detections),
                "detections": detections
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})
    
    return {"results": results}


@app.get("/model-info")
async def model_info():
    """Get model information"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "model_name": MODEL_PATH,
        "device": device,
        "input_size": 640,
        "classes": model.names,
        "task": "segmentation"
    }


@app.get("/gpu-info")
async def gpu_info():
    """Get GPU information"""
    return {
        "gpu_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "current_device": torch.cuda.current_device() if torch.cuda.is_available() else -1,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_version": torch.version.cuda,
        "pytorch_version": torch.__version__,
        "memory_allocated": f"{torch.cuda.memory_allocated() / 1e9:.2f}GB" if torch.cuda.is_available() else "N/A",
        "memory_reserved": f"{torch.cuda.memory_reserved() / 1e9:.2f}GB" if torch.cuda.is_available() else "N/A"
    }


@app.get("/results/{filename}")
async def get_result(filename: str):
    """Get saved result image"""
    filepath = RESULTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    
    return FileResponse(str(filepath))


@app.get("/results")
async def list_results():
    """List all saved results"""
    files = list(RESULTS_DIR.glob("*.jpg"))
    return {
        "total": len(files),
        "files": [f.name for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]]
    }


@app.post("/clear-results")
async def clear_results():
    """Clear all saved results"""
    import shutil
    try:
        for file in RESULTS_DIR.glob("*.jpg"):
            file.unlink()
        return {"status": "success", "message": "Results cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
