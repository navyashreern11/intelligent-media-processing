import cv2
import numpy as np
from app.config import settings
from app.logging_config import logger

def detect_blur(image_path: str, threshold: float = None) -> tuple[float, bool, float]:
    """
    Detects if an image is blurry using the Laplacian variance method.
    
    Args:
        image_path: Path to the image file.
        threshold: Variance threshold below which an image is considered blurry.
        
    Returns:
        tuple containing:
            - blur_score (float): The variance of the Laplacian.
            - is_blurry (bool): True if blur_score is below threshold.
            - confidence (float): Heuristic confidence of the blur classification [0.5, 0.99].
    """
    if threshold is None:
        threshold = settings.BLUR_THRESHOLD

    try:
        # Read image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image at {image_path} for blur detection")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate Laplacian variance
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = blur_score < threshold
        
        # Heuristic confidence calculation based on distance from threshold
        # High distance from threshold -> High confidence.
        # Close to threshold -> Low confidence (minimum 0.5).
        diff = abs(blur_score - threshold)
        confidence = min(0.5 + (diff / (threshold if threshold > 0 else 1.0)) * 0.5, 0.99)
        
        logger.info(f"Blur check complete: score={blur_score:.2f}, is_blurry={is_blurry}, confidence={confidence:.2f}")
        return blur_score, is_blurry, round(confidence, 2)
        
    except Exception as e:
        logger.error(f"Error executing blur detection: {e}", exc_info=True)
        # Return fallback values
        return 0.0, True, 0.5
