import os
from app.services.blur import detect_blur

def test_sharp_image_is_not_blurry():
    image_path = os.path.join("sample_images", "sharp.png")
    score, is_blurry, confidence = detect_blur(image_path)
    
    assert score > 100.0
    assert not is_blurry
    assert 0.5 <= confidence <= 1.0

def test_blurry_image_is_blurry():
    image_path = os.path.join("sample_images", "blurry.png")
    score, is_blurry, confidence = detect_blur(image_path)
    
    assert score < 100.0
    assert is_blurry
    assert 0.5 <= confidence <= 1.0
