import os
import time
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import ProcessingJob, Image

def test_unknown_processing_id():
    with TestClient(app) as client:
        # Check status
        response = client.get("/api/v1/images/non-existent-uuid/status")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

        # Check results
        response = client.get("/api/v1/images/non-existent-uuid/results")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

        # Try retry
        response = client.post("/api/v1/images/non-existent-uuid/retry")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

def test_successful_flow_results():
    with TestClient(app) as client:
        # Upload valid image
        image_path = os.path.join("sample_images", "sharp.png")
        with open(image_path, "rb") as img_file:
            upload_response = client.post(
                "/api/v1/images/upload",
                files={"file": ("sharp.png", img_file, "image/png")}
            )
        assert upload_response.status_code == 201
        job_id = upload_response.json()["processing_id"]

        # Wait up to 5 seconds for background worker to complete
        completed = False
        for _ in range(10):
            time.sleep(0.5)
            status_response = client.get(f"/api/v1/images/{job_id}/status")
            assert status_response.status_code == 200
            if status_response.json()["status"] == "completed":
                completed = True
                break
            
        assert completed, "Background processing failed to complete in time"

        # Check results
        results_response = client.get(f"/api/v1/images/{job_id}/results")
        assert results_response.status_code == 200
        data = results_response.json()
        assert data["status"] == "completed"
        assert "analysis" in data
        
        # Verify specific analyzer checks are present
        analysis = data["analysis"]
        assert "blur" in analysis
        assert "brightness" in analysis
        assert "duplicate" in analysis
        assert "ocr" in analysis
        assert "vehicle_number" in analysis
        assert "dimensions" in analysis
        assert "screenshot" in analysis
        assert "photo_of_photo" in analysis
        assert "tampering" in analysis
        assert "overall_confidence" in analysis

def test_retry_scenarios():
    # Insert mock failed jobs directly into test database to verify state transitions and manual retry limitations
    db = SessionLocal()
    
    # 1. Create a dummy image record
    mock_image = Image(
        id="mock-img-1",
        filename="mock.png",
        original_filename="mock.png",
        file_path="sample_images/sharp.png",
        file_size=1000,
        mime_type="image/png",
        width=400,
        height=300,
        sha256_hash="mock-hash-123"
    )
    db.add(mock_image)
    
    # 2. Create job that failed on first attempt
    failed_job = ProcessingJob(
        id="failed-job-1",
        image_id="mock-img-1",
        status="failed",
        error_message="Simulated analysis failure",
        retry_count=1
    )
    db.add(failed_job)
    
    # 3. Create job that failed permanently (reached 3 attempts)
    exhausted_job = ProcessingJob(
        id="failed-job-exhausted",
        image_id="mock-img-1",
        status="failed",
        error_message="Fatal error",
        retry_count=3
    )
    db.add(exhausted_job)
    
    db.commit()
    db.close()

    with TestClient(app) as client:
        # Try retrying the exhausted job (should be rejected)
        response = client.post("/api/v1/images/failed-job-exhausted/retry")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "MAX_RETRIES_EXCEEDED"

        # Try retrying the standard failed job (should succeed)
        response = client.post("/api/v1/images/failed-job-1/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "retry scheduled" in data["message"]
        
        # Verify status transitioned back to pending or is processing in the DB
        status_res = client.get("/api/v1/images/failed-job-1/status")
        assert status_res.status_code == 200
        assert status_res.json()["status"] in ["pending", "processing", "completed"]
