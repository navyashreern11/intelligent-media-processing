import os
from fastapi.testclient import TestClient
from app.main import app

def test_valid_image_upload():
    with TestClient(app) as client:
        image_path = os.path.join("sample_images", "sharp.png")
        with open(image_path, "rb") as img_file:
            response = client.post(
                "/api/v1/images/upload",
                files={"file": ("sharp.png", img_file, "image/png")}
            )
            
        assert response.status_code == 201
        data = response.json()
        assert "processing_id" in data
        assert "image_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "Image uploaded successfully"

def test_invalid_file_type_rejection():
    with TestClient(app) as client:
        # Upload a mockup text file renamed to .png to test type checks
        bad_file_content = b"This is not a real image but a plain text file."
        response = client.post(
            "/api/v1/images/upload",
            files={"file": ("fake_image.png", bad_file_content, "image/png")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "CORRUPTED_IMAGE"
        assert "rejected" in data["error"]["message"]

def test_unsupported_mime_rejection():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/images/upload",
            files={"file": ("document.pdf", b"%PDF-1.4 mock pdf data", "application/pdf")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_FILE_TYPE"

def test_oversized_upload_rejection():
    with TestClient(app) as client:
        # Generate dummy data exceeding 10MB limit
        huge_data = b"0" * (11 * 1024 * 1024)
        response = client.post(
            "/api/v1/images/upload",
            files={"file": ("huge.png", huge_data, "image/png")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "FILE_TOO_LARGE"

def test_duplicate_upload_rejection():
    with TestClient(app) as client:
        # First upload
        image_path = os.path.join("sample_images", "dark.png")
        with open(image_path, "rb") as img_file:
            response1 = client.post(
                "/api/v1/images/upload",
                files={"file": ("dark.png", img_file, "image/png")}
            )
        assert response1.status_code == 201
        
        # Second upload with same image contents
        with open(image_path, "rb") as img_file:
            response2 = client.post(
                "/api/v1/images/upload",
                files={"file": ("dark_copy.png", img_file, "image/png")}
            )
            
        assert response2.status_code == 409
        data = response2.json()
        assert data["error"]["code"] == "DUPLICATE_UPLOAD"
