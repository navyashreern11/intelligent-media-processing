from fastapi import APIRouter
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Image, ProcessingJob, AnalysisResult


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/summary")
def get_analytics_summary():
    db = SessionLocal()

    try:
        total_images = db.query(func.count(Image.id)).scalar() or 0

        total_jobs = db.query(func.count(ProcessingJob.id)).scalar() or 0

        completed_jobs = (
            db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status == "completed")
            .scalar()
            or 0
        )

        failed_jobs = (
            db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status == "failed")
            .scalar()
            or 0
        )

        pending_jobs = (
            db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status == "pending")
            .scalar()
            or 0
        )

        processing_jobs = (
            db.query(func.count(ProcessingJob.id))
            .filter(ProcessingJob.status == "processing")
            .scalar()
            or 0
        )

        duplicate_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.is_duplicate == True)
            .scalar()
            or 0
        )

        blurry_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.is_blurry == True)
            .scalar()
            or 0
        )

        low_light_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.is_low_light == True)
            .scalar()
            or 0
        )

        screenshot_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.screenshot_suspected == True)
            .scalar()
            or 0
        )

        photo_of_photo_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.photo_of_photo_suspected == True)
            .scalar()
            or 0
        )

        tampered_images = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.tampering_suspected == True)
            .scalar()
            or 0
        )

        valid_vehicle_numbers = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.vehicle_number_valid == True)
            .scalar()
            or 0
        )

        invalid_vehicle_numbers = (
            db.query(func.count(AnalysisResult.id))
            .filter(AnalysisResult.vehicle_number_valid == False)
            .scalar()
            or 0
        )

        average_confidence = (
            db.query(func.avg(AnalysisResult.overall_confidence))
            .scalar()
        )

        return {
            "total_images": total_images,
            "total_jobs": total_jobs,
            "jobs": {
                "pending": pending_jobs,
                "processing": processing_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs
            },
            "quality_issues": {
                "duplicates": duplicate_images,
                "blurry_images": blurry_images,
                "low_light_images": low_light_images,
                "screenshots": screenshot_images,
                "photo_of_photo": photo_of_photo_images,
                "tampering_suspected": tampered_images
            },
            "vehicle_validation": {
                "valid": valid_vehicle_numbers,
                "invalid": invalid_vehicle_numbers
            },
            "average_confidence": (
                round(float(average_confidence), 3)
                if average_confidence is not None
                else None
            )
        }

    finally:
        db.close()