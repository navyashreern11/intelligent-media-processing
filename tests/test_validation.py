from app.services.validation import validate_indian_vehicle_number, validate_dimensions

def test_indian_vehicle_number_regex():
    # Valid standard registrations
    assert validate_indian_vehicle_number("KA01AB1234") == ("KA01AB1234", True)
    assert validate_indian_vehicle_number("MH12DE1432") == ("MH12DE1432", True)
    assert validate_indian_vehicle_number("TN38AB1234") == ("TN38AB1234", True)
    assert validate_indian_vehicle_number("DL01AB1234") == ("DL01AB1234", True)
    
    # Text with noise (should extract normalized plate)
    assert validate_indian_vehicle_number("Registration: KA 01 AB 1234 on plate") == ("KA01AB1234", True)
    
    # Invalid registrations
    assert validate_indian_vehicle_number("XYZ123")[1] is False
    assert validate_indian_vehicle_number("KA011234")[1] is False
    assert validate_indian_vehicle_number(None) == (None, False)

def test_dimension_validation():
    # Min width/height = 200/200
    assert validate_dimensions(400, 300) is True
    assert validate_dimensions(200, 200) is True
    assert validate_dimensions(150, 300) is False
    assert validate_dimensions(400, 150) is False
