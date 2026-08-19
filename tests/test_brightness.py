import os
from app.services.brightness import detect_brightness

def test_bright_image_is_not_low_light():
    image_path = os.path.join("sample_images", "sharp.png")
    score, is_low_light, confidence = detect_brightness(image_path)
    
    assert score > 60.0
    assert not is_low_light
    assert 0.5 <= confidence <= 1.0

def test_dark_image_is_low_light():
    image_path = os.path.join("sample_images", "dark.png")
    score, is_low_light, confidence = detect_brightness(image_path)
    
    assert score < 60.0
    assert is_low_light
    assert 0.5 <= confidence <= 1.0
