import re
from app.config import settings
from app.logging_config import logger

def validate_indian_vehicle_number(ocr_text: str) -> tuple[str | None, bool]:
    """
    Attempts to identify a possible Indian vehicle registration number from OCR text.
    
    Format: State Code (2 letters) + RTO Code (2 digits) + Series (1 or 2 letters) + Plate Number (4 digits)
    Examples: KA01AB1234, MH12DE1432, DL01AB1234, KL07CD5678
    
    Args:
        ocr_text: Raw text extracted from the image.
        
    Returns:
        tuple containing:
            - vehicle_number (str | None): The detected matching pattern or None.
            - valid (bool): True if a valid format was detected.
    """
    if not ocr_text or ocr_text == "OCR_UNAVAILABLE":
        return None, False

    try:
        # Normalize text: uppercase, remove non-alphanumeric characters
        normalized = re.sub(r"[^A-Z0-9]", "", ocr_text.upper())
        
        # Regex for standard Indian registration format
        # State (2 chars), RTO (2 digits), unique series (1-2 chars), plate unique number (4 digits)
        pattern = r"([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})"
        
        match = re.search(pattern, normalized)
        if match:
            vehicle_number = match.group(1)
            logger.info(f"Vehicle validation: Found possible Indian registration number: {vehicle_number}")
            return vehicle_number, True
            
        # Support alternative formats (e.g. single digit RTO like DL1C1234 or shorter plate numbers like KA01A123)
        alt_pattern = r"([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4})"
        match_alt = re.search(alt_pattern, normalized)
        if match_alt:
            vehicle_number = match_alt.group(1)
            logger.info(f"Vehicle validation: Found alternative registration number format: {vehicle_number}")
            return vehicle_number, True

        logger.info("Vehicle validation: No matching registration number format found")
        return None, False
        
    except Exception as e:
        logger.error(f"Error validating vehicle number: {e}", exc_info=True)
        return None, False

def validate_dimensions(width: int, height: int) -> bool:
    """
    Checks if the image dimensions meet the minimum required width and height.
    
    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        
    Returns:
        bool: True if both dimensions meet or exceed the minimum configuration.
    """
    min_width = settings.MIN_IMAGE_WIDTH
    min_height = settings.MIN_IMAGE_HEIGHT
    
    valid = width >= min_width and height >= min_height
    logger.info(f"Dimension check: width={width} (min={min_width}), height={height} (min={min_height}) -> valid={valid}")
    return valid
