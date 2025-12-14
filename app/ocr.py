# OCR and Plate Recognition Module

import easyocr
import cv2
import numpy as np
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

class PlateOCR:
    """License plate OCR reader"""
    
    def __init__(self):
        """Initialize OCR reader"""
        try:
            self.reader = easyocr.Reader(['en'], gpu=True)
            logger.info("✓ OCR initialized with GPU support")
        except Exception as e:
            logger.warning(f"GPU not available for OCR, using CPU: {e}")
            self.reader = easyocr.Reader(['en'], gpu=False)
    
    def read_plate(self, image: np.ndarray, plate_region: dict) -> Tuple[str, float]:
        """
        Read license plate text from image region using bounding box coordinates
        
        Args:
            image: Input image (numpy array)
            plate_region: Bounding box of plate region {'x1': float, 'y1': float, 'x2': float, 'y2': float}
        
        Returns:
            Tuple of (plate_text, confidence_score)
        """
        try:
            # Extract plate region
            x1 = int(plate_region['x1'])
            y1 = int(plate_region['y1'])
            x2 = int(plate_region['x2'])
            y2 = int(plate_region['y2'])
            
            # Ensure coordinates are within bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(image.shape[1], x2)
            y2 = min(image.shape[0], y2)
            
            plate_img = image[y1:y2, x1:x2]
            
            if plate_img.size == 0:
                return "", 0.0
            
            # Preprocess image for better OCR
            plate_img = self._preprocess_plate(plate_img)
            
            # Read text
            results = self.reader.readtext(plate_img, detail=1)
            
            if not results:
                return "", 0.0
            
            # Combine all detected text
            plate_text = ""
            confidence = 0.0
            
            for (bbox, text, conf) in results:
                plate_text += text
                confidence += conf
            
            if results:
                confidence = confidence / len(results)
            
            # Clean up text (remove spaces, special characters)
            plate_text = self._clean_plate_text(plate_text)
            
            logger.info(f"✓ Plate detected: {plate_text} (confidence: {confidence:.2f})")
            return plate_text, confidence
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "", 0.0
    
    def read_plate_from_crop(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """
        Read license plate text from already-cropped plate image
        
        Args:
            plate_img: Cropped plate image (numpy array)
        
        Returns:
            Tuple of (plate_text, confidence_score)
        """
        try:
            if plate_img.size == 0:
                return "", 0.0
            
            # Preprocess image for better OCR
            plate_img_processed = self._preprocess_plate(plate_img)
            
            # Read text
            results = self.reader.readtext(plate_img_processed, detail=1)
            
            if not results:
                return "", 0.0
            
            # Combine all detected text with proper spacing
            plate_text = ""
            confidence = 0.0
            
            for (bbox, text, conf) in results:
                # Clean individual text segments
                text = text.strip()
                if text:
                    plate_text += text + " "
                confidence += conf
            
            if results:
                confidence = confidence / len(results)
            
            # Clean up text - preserves spaces between segments
            plate_text = self._clean_plate_text(plate_text.strip())
            
            logger.info(f"✓ Plate OCR result: {plate_text} (confidence: {confidence:.2f})")
            return plate_text, confidence
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "", 0.0
    
    @staticmethod
    def _preprocess_plate(image: np.ndarray) -> np.ndarray:
        """
        Preprocess plate image for better OCR accuracy
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detect and correct skew angle
            gray = PlateOCR._deskew_image(gray)
            
            # Upscale image - more aggressive for small plates
            height, width = gray.shape
            scale = 1
            if height < 30 or width < 100:
                scale = 4  # More upscaling for very small plates
            elif height < 50 or width < 150:
                scale = 3
            else:
                scale = 2
            
            if scale > 1:
                gray = cv2.resize(gray, (width * scale, height * scale), interpolation=cv2.INTER_CUBIC)
            
            # Apply bilateral filter to preserve edges while reducing noise
            gray = cv2.bilateralFilter(gray, 11, 17, 17)
            
            # Apply CLAHE for contrast enhancement with stronger parameters
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
            # Additional contrast stretching
            gray = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
            
            # Sharpen image to enhance characters
            kernel_sharpen = np.array([[-1, -1, -1],
                                       [-1,  9, -1],
                                       [-1, -1, -1]])
            gray = cv2.filter2D(gray, -1, kernel_sharpen)
            
            # Threshold with Otsu method for automatic level detection
            _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Morphological operations to clean up and connect characters
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel, iterations=1)
            gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=1)
            
            return gray
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return image
    
    @staticmethod
    def _deskew_image(image: np.ndarray) -> np.ndarray:
        """Detect and correct image skew for better OCR"""
        try:
            # Use Hough Line Transform to find text lines
            edges = cv2.Canny(image, 50, 150)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 50)
            
            if lines is None or len(lines) == 0:
                return image
            
            # Extract angles from lines
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = np.rad2deg(theta) - 90
                angles.append(angle)
            
            # Use median angle
            median_angle = np.median(angles)
            
            # Correct skew if angle is significant
            if abs(median_angle) > 1.0:
                h, w = image.shape
                center = (w // 2, h // 2)
                rot_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                image = cv2.warpAffine(image, rot_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
            
            return image
        except Exception as e:
            logger.debug(f"Deskew warning: {e}")
            return image
    
    @staticmethod
    def _clean_plate_text(text: str) -> str:
        """
        Clean and normalize plate text
        
        Format: ABC1234 or AB-12-CD or 34 TBT 77 (varies by region)
        Preserves spaces which are important for some regional formats
        """
        # Remove extra spaces
        text = text.strip()
        text = ' '.join(text.split())  # Normalize multiple spaces
        
        # Convert to uppercase
        text = text.upper()
        
        return text
    
    @staticmethod
    def validate_plate(plate_text: str) -> bool:
        """
        Validate if text looks like a license plate
        Supports formats: ABC1234, AB-12-CD, 34 TBT 77, AB12CD, etc.
        """
        # Remove hyphens and spaces for validation
        cleaned = plate_text.replace('-', '').replace(' ', '')
        
        # Must have 4-10 characters (accounting for various formats)
        if len(cleaned) < 4 or len(cleaned) > 10:
            return False
        
        # Must have at least one letter and one number
        has_letter = any(c.isalpha() for c in cleaned)
        has_number = any(c.isdigit() for c in cleaned)
        
        if not (has_letter and has_number):
            return False
        
        return True


# Global OCR instance
plate_ocr = PlateOCR()

def detect_and_read_plate(image: np.ndarray, detection: dict) -> Tuple[str, float]:
    """
    Detect and read plate from image
    
    Args:
        image: Input image
        detection: Detection object with x1, y1, x2, y2 coordinates
    
    Returns:
        Tuple of (plate_text, ocr_confidence)
    """
    plate_text, confidence = plate_ocr.read_plate(image, detection)
    
    # Don't validate here - let the caller decide
    return plate_text, confidence
