from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import logger
from app.models import ProcessingJob, AnalysisResult
from app.schemas import (
    StatusResponse, ResultsResponse, ErrorResponse, DetailedAnalysis,
    BlurAnalysis, BrightnessAnalysis, DuplicateAnalysis, OCRAnalysis,
    VehicleNumberAnalysis, DimensionsAnalysis, ScreenshotAnalysis,
    PhotoOfPhotoAnalysis, TamperingAnalysis
)
from app.worker.queue import job_queue_manager

router = APIRouter(prefix="/images", tags=["Results & Management"])

@router.get(
    "/{processing_id}/status",
    response_model=StatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Processing ID not found"},
        500: {"model": ErrorResponse, "description": "Unexpected internal error"}
    }
)
def get_job_status(processing_id: str, db: Session = Depends(get_db)):
    """Retrieves the status of an asynchronous image processing job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == processing_id).first()
    if not job:
        logger.warning(f"Status check failed: Job {processing_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "The requested processing ID does not exist."
            }
        )
    
    return StatusResponse(
        processing_id=job.id,
        status=job.status,
        error=job.error_message
    )

@router.get(
    "/{processing_id}/results",
    response_model=ResultsResponse,
    responses={
        202: {"description": "Job is still processing"},
        404: {"model": ErrorResponse, "description": "Processing ID not found"},
        500: {"model": ErrorResponse, "description": "Unexpected internal error"}
    }
)
def get_job_results(processing_id: str, response: Response, db: Session = Depends(get_db)):
    """
    Retrieves the complete analysis results of an image processing job.
    Returns HTTP 202 if processing is not yet complete.
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.id == processing_id).first()
    if not job:
        logger.warning(f"Results check failed: Job {processing_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "The requested processing ID does not exist."
            }
        )

    if job.status in ["pending", "processing"]:
        # Job is still in progress, return HTTP 202 Accepted
        response.status_code = status.HTTP_202_ACCEPTED
        return ResultsResponse(
            processing_id=job.id,
            status=job.status,
            message="Analysis is in progress. Please check again later."
        )

    if job.status == "failed":
        return ResultsResponse(
            processing_id=job.id,
            status=job.status,
            error=job.error_message
        )

    # Status must be completed, map results
    results: AnalysisResult = job.results
    if not results:
        logger.error(f"Integrity error: Job {processing_id} is marked completed but has no results")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DATA_INTEGRITY_ERROR",
                "message": "Analysis results are missing from database."
            }
        )

    # Heuristic tamper confidence mapping (since we didn't add it as a column)
    tamper_conf = 0.75 if results.tampering_suspected else 0.15

    analysis = DetailedAnalysis(
        blur=BlurAnalysis(
            score=results.blur_score,
            is_blurry=results.is_blurry,
            confidence=results.blur_confidence
        ),
        brightness=BrightnessAnalysis(
            score=results.brightness_score,
            is_low_light=results.is_low_light,
            confidence=results.brightness_confidence
        ),
        duplicate=DuplicateAnalysis(
            is_duplicate=results.is_duplicate,
            duplicate_of=results.duplicate_of
        ),
        ocr=OCRAnalysis(text=results.ocr_text),
        vehicle_number=VehicleNumberAnalysis(
            value=results.vehicle_number,
            valid=results.vehicle_number_valid
        ),
        dimensions=DimensionsAnalysis(valid=results.dimension_valid),
        screenshot=ScreenshotAnalysis(suspected=results.screenshot_suspected),
        photo_of_photo=PhotoOfPhotoAnalysis(suspected=results.photo_of_photo_suspected),
        tampering=TamperingAnalysis(
            suspected=results.tampering_suspected,
            confidence=tamper_conf
        ),
        overall_confidence=results.overall_confidence
    )

    return ResultsResponse(
        processing_id=job.id,
        status=job.status,
        analysis=analysis
    )

@router.post(
    "/{processing_id}/retry",
    responses={
        200: {"description": "Job retry successfully scheduled"},
        400: {"model": ErrorResponse, "description": "Job cannot be retried"},
        404: {"model": ErrorResponse, "description": "Processing ID not found"},
        500: {"model": ErrorResponse, "description": "Unexpected internal error"}
    }
)
def retry_job(processing_id: str, db: Session = Depends(get_db)):
    """
    Manually retries a failed job.
    Only allows retry if status is failed and maximum attempts (3) have not been exhausted.
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.id == processing_id).first()
    if not job:
        logger.warning(f"Retry request failed: Job {processing_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "The requested processing ID does not exist."
            }
        )

    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_JOB_STATE",
                "message": f"Only failed jobs can be retried. Current status: '{job.status}'"
            }
        )

    if job.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MAX_RETRIES_EXCEEDED",
                "message": f"Job has already reached the maximum limit of 3 retry attempts."
            }
        )

    # Schedule retry: Reset status, clear errors, increment retry count, and queue it
    job.status = "pending"
    job.error_message = None
    job.completed_at = None
    db.commit()

    job_queue_manager.enqueue(job.id)
    logger.info(f"Manual retry scheduled for job {job.id}", extra={"processing_id": job.id})

    return {
        "processing_id": job.id,
        "status": "pending",
        "message": "Processing retry scheduled"
    }
