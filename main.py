#!/usr/bin/env python
"""
License Plate Detection System - Main Entry Point
Run this file to start everything automatically
"""

import sys
import os
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

# Start the FastAPI server
if __name__ == "__main__":
    import uvicorn
    
    # Import after path is set up
    from app.main_plates import app
    
    print("\n" + "="*80)
    print("STARTING LICENSE PLATE DETECTION SYSTEM".center(80))
    print("="*80)
    print("\n✓ System Components:")
    print("  • YOLO Instance Segmentation Model")
    print("  • Segmentation-based Plate Cropping")
    print("  • EasyOCR Text Recognition")
    print("  • Violation Database Integration")
    print("\n📊 Dashboard & API:")
    print("  • Dashboard:   http://localhost:8000")
    print("  • API Docs:    http://localhost:8000/api/docs")
    print("  • API Base:    http://localhost:8000/api")
    print("\n✨ Process Flow:")
    print("  1. Upload Image")
    print("  2. YOLO detects & segments plates")
    print("  3. Segment cropped to individual plate")
    print("  4. OCR reads cropped plate image")
    print("  5. Results shown with cropped image visualization")
    print("\n" + "="*80 + "\n")
    
    # Run the server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
