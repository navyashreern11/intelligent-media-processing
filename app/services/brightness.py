import cv2
import numpy as np
from app.config import settings
from app.logging_config import logger

def detect_brightness(image_path: str, threshold: float = None) -> tuple[float, bool, float]:
    """
    Detects if an image is in low light by computing the average grayscale intensity.
    
    Args:
        image_path: Path to the image file.
        threshold: Intensity threshold [0-255] below which an image is low-light.
        
    Returns:
        tuple containing:
            - brightness_score (float): Mean pixel value [0.0 - 255.0].
            - is_low_light (bool): True if brightness_score is below threshold.
            - confidence (float): Heuristic confidence of classification [0.5, 0.99].
    """
    if threshold is None:
        threshold = settings.LOW_LIGHT_THRESHOLD

    try:
        # Read image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image at {image_path} for brightness check")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate mean brightness score
        brightness_score = float(np.mean(gray))
        is_low_light = brightness_score < threshold
        
        # Heuristic confidence calculation
        diff = abs(brightness_score - threshold)
        confidence = min(0.5 + (diff / (threshold if threshold > 0 else 1.0)) * 0.5, 0.99)
        
        logger.info(f"Brightness check complete: score={brightness_score:.2f}, is_low_light={is_low_light}, confidence={confidence:.2f}")
        return brightness_score, is_low_light, round(confidence, 2)
        
    except Exception as e:
        logger.error(f"Error executing brightness detection: {e}", exc_info=True)
        return 127.5, False, 0.5
