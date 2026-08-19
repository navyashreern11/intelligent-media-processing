import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import ProcessingJob, Image, AnalysisResult
from app.config import settings
from app.logging_config import logger

# Import analysis checkers
from app.services.blur import detect_blur
from app.services.brightness import detect_brightness
from app.services.duplicate import calculate_dhash
from app.services.ocr import perform_ocr
from app.services.validation import validate_indian_vehicle_number, validate_dimensions
from app.services.image_metadata import (
    analyze_screenshot_suspected,
    analyze_photo_of_photo_suspected,
    analyze_tampering
)

def compute_overall_confidence(
    is_blurry: bool, blur_conf: float,
    is_low_light: bool, bright_conf: float,
    dim_valid: bool,
    screenshot_suspected: bool,
    photo_of_photo_suspected: bool,
    tamper_suspected: bool, tamper_conf: float
) -> float:
    """
    Computes a heuristic overall confidence score for the image quality and analysis validity.
    This is not a scientifically proven probability, but an engineering signal.
    """
    if not dim_valid:
        return 0.10  # Very low confidence if dimensions are below minimums

    score = 0.95  # Start with high confidence for a clean image
    
    # Penalize based on blur
    if is_blurry:
        score -= (blur_conf * 0.35)
        
    # Penalize based on low light
    if is_low_light:
        score -= (bright_conf * 0.25)
        
    # Penalize for heuristics
    if screenshot_suspected:
        score -= 0.10
    if photo_of_photo_suspected:
        score -= 0.15
    if tamper_suspected:
        score -= (tamper_conf * 0.30)
        
    # Keep score bound within [0.05, 0.99]
    return float(round(max(0.05, min(score, 0.99)), 2))

def process_job(job_id: str):
    """
    Executes the image analysis pipeline for a given job.
    Includes error handling and retry orchestration.
    """
    db: Session = SessionLocal()
    
    # Track extra variables for logging with correlation ID
    log_extra = {"processing_id": job_id}
    
    try:
        # Fetch the job and associated image metadata
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Job not found in database", extra=log_extra)
            return

        # Enforce valid state transitions (must be pending or processing for retries)
        if job.status not in ["pending", "failed"]:
            logger.warning(f"Job is in invalid transition state: {job.status}", extra=log_extra)
            return

        # Transition to processing state
        job.status = "processing"
        job.started_at = datetime.datetime.utcnow()
        job.error_message = None
        db.commit()
        logger.info(f"Job status transitioned to processing", extra=log_extra)

        image = db.query(Image).filter(Image.id == job.image_id).first()
        if not image:
            raise ValueError(f"Image record with ID {job.image_id} not found")

        # Run checks
        logger.info("Executing blur detection...", extra=log_extra)
        blur_score, is_blurry, blur_conf = detect_blur(image.file_path)

        logger.info("Executing brightness detection...", extra=log_extra)
        brightness_score, is_low_light, bright_conf = detect_brightness(image.file_path)

        # Duplicate check - Exact match query via SHA-256
        logger.info("Checking for exact file duplicates...", extra=log_extra)
        duplicate_record = db.query(Image).filter(
            Image.sha256_hash == image.sha256_hash,
            Image.id != image.id
        ).order_by(Image.created_at.asc()).first()
        
        is_duplicate = duplicate_record is not None
        duplicate_of = duplicate_record.id if is_duplicate else None
        if is_duplicate:
            logger.info(f"Duplicate found: matches image {duplicate_of}", extra=log_extra)

        # Optional: Compute dhash to demonstrate code capability (logged but not stored in images schema)
        dhash_val = calculate_dhash(image.file_path)
        logger.info(f"Computed Difference Hash (dhash): {dhash_val}", extra=log_extra)

        # Run OCR (Graceful failure handled within function)
        logger.info("Running OCR extraction...", extra=log_extra)
        ocr_text = perform_ocr(image.file_path)

        # Run validation
        logger.info("Running vehicle number format validation...", extra=log_extra)
        vehicle_number, vehicle_number_valid = validate_indian_vehicle_number(ocr_text)

        logger.info("Running dimension validation...", extra=log_extra)
        dimension_valid = validate_dimensions(image.width, image.height)

        # Run Heuristics
        logger.info("Running screenshot detection heuristic...", extra=log_extra)
        screenshot_suspected = analyze_screenshot_suspected(image.file_path, image.original_filename)

        logger.info("Running photo-of-photo detection heuristic...", extra=log_extra)
        photo_of_photo_suspected = analyze_photo_of_photo_suspected(image.file_path)

        logger.info("Running tampering detection heuristic...", extra=log_extra)
        tamper_suspected, tamper_conf = analyze_tampering(image.file_path)

        # Compute overall confidence
        overall_conf = compute_overall_confidence(
            is_blurry=is_blurry, blur_conf=blur_conf,
            is_low_light=is_low_light, bright_conf=bright_conf,
            dim_valid=dimension_valid,
            screenshot_suspected=screenshot_suspected,
            photo_of_photo_suspected=photo_of_photo_suspected,
            tamper_suspected=tamper_suspected, tamper_conf=tamper_conf
        )

        # Clean existing results if this is a retry
        if job.results:
            db.delete(job.results)
            db.flush()

        # Save analysis results
        results = AnalysisResult(
            job_id=job.id,
            blur_score=blur_score,
            is_blurry=is_blurry,
            blur_confidence=blur_conf,
            brightness_score=brightness_score,
            is_low_light=is_low_light,
            brightness_confidence=bright_conf,
            is_duplicate=is_duplicate,
            duplicate_of=duplicate_of,
            ocr_text=ocr_text,
            vehicle_number=vehicle_number,
            vehicle_number_valid=vehicle_number_valid,
            dimension_valid=dimension_valid,
            screenshot_suspected=screenshot_suspected,
            photo_of_photo_suspected=photo_of_photo_suspected,
            tampering_suspected=tamper_suspected,
            overall_confidence=overall_conf
        )
        db.add(results)

        # Finalize job status
        job.status = "completed"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("Job successfully completed", extra=log_extra)

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing job: {e}", exc_info=True, extra=log_extra)
        handle_job_failure(db, job_id, e)
        
    finally:
        db.close()

def handle_job_failure(db: Session, job_id: str, exception: Exception):
    """Handles incrementing retries and marking jobs failed/pending."""
    log_extra = {"processing_id": job_id}
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            return

        job.retry_count += 1
        max_retries = settings.MAX_RETRIES
        
        if job.retry_count < max_retries:
            job.status = "pending"  # Reset status so worker can retry
            db.commit()
            logger.info(f"Retrying job. Attempt {job.retry_count}/{max_retries}", extra=log_extra)
            # Re-enqueue in worker
            from app.worker.queue import job_queue_manager
            job_queue_manager.enqueue(job_id)
        else:
            job.status = "failed"
            job.error_message = str(exception)
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.error(f"Job failed permanently after {max_retries} attempts", extra=log_extra)
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing job failure logic: {e}", exc_info=True, extra=log_extra)
