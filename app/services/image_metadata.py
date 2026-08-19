import os
import cv2
import numpy as np
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from app.logging_config import logger

def analyze_screenshot_suspected(image_path: str, original_filename: str) -> bool:
    """
    Lightweight heuristic to suspect if an image is a screenshot.
    Checks filename keywords, typical screen aspect ratios, and lack of camera EXIF data.
    """
    try:
        # Heuristic 1: Filename matches
        fn_lower = original_filename.lower()
        if "screenshot" in fn_lower or "screen_shot" in fn_lower or "scr_" in fn_lower:
            logger.info("Screenshot check: Suspected based on filename pattern")
            return True

        # Read image to check dimensions and EXIF
        with PILImage.open(image_path) as img:
            width, height = img.size
            aspect_ratio = width / height if height > 0 else 1.0
            
            # Heuristic 2: Typical screen resolutions/aspect ratios
            # e.g., 16:9 (1.77 or 0.56), 19.5:9 (2.16 or 0.46), 4:3 (1.33 or 0.75)
            common_ratios = [16/9, 9/16, 19.5/9, 9/19.5, 4/3, 3/4]
            matches_ratio = any(abs(aspect_ratio - r) < 0.05 for r in common_ratios)
            
            # Heuristic 3: Check if EXIF is empty
            exif = img.getexif()
            has_camera_info = False
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ["Make", "Model", "Software", "DateTimeOriginal"]:
                        has_camera_info = True
                        break
            
            # Suspect screenshot if aspect ratio matches screen AND no camera EXIF is present
            # Note: Web images often strip EXIF, so this is just a weak heuristic.
            if matches_ratio and not has_camera_info:
                # Add check for typical screen dimensions
                if (width in [1080, 1920, 2560, 1440, 720, 1280]) or (height in [1080, 1920, 2560, 1440, 720, 1280]):
                    logger.info("Screenshot check: Suspected based on screen dimensions and lack of EXIF")
                    return True

        return False
    except Exception as e:
        logger.warning(f"Error in screenshot heuristic: {e}")
        return False

def analyze_photo_of_photo_suspected(image_path: str) -> bool:
    """
    Lightweight heuristic to suspect if an image is a photo of another photo or screen.
    Searches for nested rectangular contours representing device borders or photo prints.
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return False

        height, width = img.shape[:2]
        total_area = width * height
        
        # Convert to gray and threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Approximate the contour
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            
            # Check if contour is a convex quadrilateral (4 vertices)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                area = cv2.contourArea(approx)
                # Check if the rectangular contour is large enough to be a frame (15% to 85% of total image area)
                if 0.15 * total_area < area < 0.85 * total_area:
                    logger.info(f"Photo-of-photo check: Suspected based on a nested rectangular contour of area {area}/{total_area}")
                    return True

        return False
    except Exception as e:
        logger.warning(f"Error in photo-of-photo heuristic: {e}")
        return False

def analyze_tampering(image_path: str) -> tuple[bool, float]:
    """
    Lightweight heuristic for JPEG tampering detection using basic Error Level Analysis (ELA)
    and EXIF software metadata analysis.
    
    Returns:
        tuple containing:
            - suspected (bool): True if tampering is suspected.
            - confidence (float): Heuristic confidence of tamper classification.
    """
    try:
        # 1. EXIF metadata tampering check (e.g. Photoshop / GIMP software tags)
        software_tamper = False
        with PILImage.open(image_path) as img:
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "Software" and isinstance(value, str):
                        val_lower = value.lower()
                        if any(sw in val_lower for sw in ["photoshop", "gimp", "picsart", "pixelmator", "snapseed"]):
                            software_tamper = True
                            logger.info(f"Tamper check: Editing software detected in EXIF: {value}")
                            break
        
        # 2. Simple Error Level Analysis (ELA) heuristic (for JPEG files)
        # Resave image at 90% quality, and analyze pixel differences.
        # Modified/spliced images will have different error levels in edited zones.
        is_jpeg = image_path.lower().endswith(('.jpg', '.jpeg'))
        if is_jpeg:
            temp_resaved = image_path + ".resaved.jpg"
            try:
                # Load, resave at 90% quality
                img_cv = cv2.imread(image_path)
                if img_cv is not None:
                    cv2.imwrite(temp_resaved, img_cv, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    
                    # Read resaved and compute absolute difference
                    resaved_cv = cv2.imread(temp_resaved)
                    diff = cv2.absdiff(img_cv, resaved_cv)
                    
                    # Compute mean and standard deviation of diff
                    mean_diff = np.mean(diff)
                    std_diff = np.std(diff)
                    
                    # If standard deviation of error level is unusually high, it indicates compression variance (tampering)
                    # Note: Thresholds are arbitrary heuristics for this demonstration
                    if std_diff > 12.0 or software_tamper:
                        logger.info(f"Tamper check: Suspected. std_diff={std_diff:.2f}, software_tamper={software_tamper}")
                        return True, round(min(0.3 + (std_diff / 50.0), 0.85), 2)
            finally:
                if os.path.exists(temp_resaved):
                    os.remove(temp_resaved)
                    
        # Fallback to software EXIF check only
        if software_tamper:
            return True, 0.75

        return False, 0.15
        
    except Exception as e:
        logger.warning(f"Error in tampering heuristic: {e}")
        return False, 0.0
