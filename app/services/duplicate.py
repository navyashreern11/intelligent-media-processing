import hashlib
import cv2
from app.logging_config import logger

def calculate_sha256(file_path: str) -> str:
    """Calculates the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating SHA-256 hash: {e}", exc_info=True)
        raise

def calculate_dhash(image_path: str) -> str:
    """
    Computes a 64-bit Difference Hash (dhash) for perceptual similarity comparison.
    
    Resizes the image to 9x8, converts to grayscale, and compares horizontal pixel gradients.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Failed to read image at {image_path} for dhash")

        # Resize to 9x8
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        
        # Calculate differences between adjacent pixels in each row
        diff = resized[:, 1:] > resized[:, :-1]
        
        # Convert the Boolean array to a hex string
        decimal_val = 0
        hex_string = []
        for i, val in enumerate(diff.flatten()):
            if val:
                decimal_val += 2**(i % 8)
            if (i % 8) == 7:
                hex_string.append(format(decimal_val, '02x'))
                decimal_val = 0
                
        return "".join(hex_string)
    except Exception as e:
        logger.warning(f"Failed to calculate dhash: {e}")
        return ""

def hamming_distance(hash1: str, hash2: str) -> int:
    """Computes the Hamming distance between two hex hashes."""
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 999  # Invalid comparison value

    try:
        bin1 = bin(int(hash1, 16))[2:].zfill(64)
        bin2 = bin(int(hash2, 16))[2:].zfill(64)
        return sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
    except Exception as e:
        logger.warning(f"Error computing Hamming distance: {e}")
        return 999
