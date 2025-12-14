import os
from dotenv import load_dotenv

load_dotenv()

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n-seg.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", 0.45))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# GPU Configuration
USE_GPU = os.getenv("USE_GPU", "True").lower() == "true"

# Directories
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")
MODEL_DIR = os.getenv("MODEL_DIR", "model")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# API Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB

# Image Configuration
SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff"]
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 1280))
