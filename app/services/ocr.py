import cv2
import pytesseract
from app.config import settings
from app.logging_config import logger

import os
import sys

# Set Tesseract binary path if configured, or use standard Windows fallback if it exists
tesseract_cmd_path = settings.TESSERACT_CMD
if not tesseract_cmd_path and sys.platform == "win32":
    default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_win_path):
        tesseract_cmd_path = default_win_path

if tesseract_cmd_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
    logger.info(f"Tesseract OCR path configured to: {tesseract_cmd_path}")


def perform_ocr(image_path: str) -> str:
    """
    Extracts text from the image using Tesseract OCR.
    Preprocesses the image (grayscale + Otsu's thresholding) to improve accuracy.
    Fails gracefully if Tesseract is not installed/configured.
    
    Returns:
        ocr_text (str): The extracted text, or "OCR_UNAVAILABLE" if Tesseract is missing.
    """
    try:
        # Load the image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image at {image_path} for OCR")

        # Preprocess: grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Preprocess: upscale image slightly to improve character recognition for small text
        height, width = gray.shape[:2]
        resized = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Preprocess: adaptive thresholding or Otsu's thresholding
        thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Perform OCR (using --psm 11 for sparse text search or --psm 3 as default)
        ocr_text = pytesseract.image_to_string(thresh, config="--psm 11").strip()
        
        logger.info("OCR processing completed successfully")
        return ocr_text

    except pytesseract.TesseractNotFoundError as e:
        logger.warning(f"OCR failure: Tesseract is not installed or configured: {e}")
        return "OCR_UNAVAILABLE"
    except Exception as e:
        logger.warning(f"OCR failure: An unexpected error occurred: {e}")
        return "OCR_UNAVAILABLE"
