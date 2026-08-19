import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from PIL import Image as PILImage, UnidentifiedImageError

from app.database import get_db
from app.config import settings
from app.logging_config import logger
from app.models import Image, ProcessingJob
from app.schemas import UploadResponse, ErrorResponse
from app.services.duplicate import calculate_sha256
from app.worker.queue import job_queue_manager

router = APIRouter(prefix="/images", tags=["Upload"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image or size exceeded"},
        409: {"model": ErrorResponse, "description": "Duplicate image upload"},
        500: {"model": ErrorResponse, "description": "Unexpected internal error"}
    }
)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    logger.info(f"Upload request received: filename={file.filename}, content_type={file.content_type}")
    
    # 1. Validate extension
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"File upload rejected: Unsupported extension '{ext}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"Extension '{ext}' is not supported. Supported extensions: {', '.join(ALLOWED_EXTENSIONS)}"
            }
        )

    # 2. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"File upload rejected: Unsupported MIME type '{file.content_type}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_MIME_TYPE",
                "message": f"MIME type '{file.content_type}' is not supported. Supported types: {', '.join(ALLOWED_MIME_TYPES)}"
            }
        )

    # 3. Read & validate size (10 MB limit)
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    temp_file_path = os.path.join(settings.UPLOAD_DIR, f"temp_{uuid.uuid4().hex}{ext}")
    
    try:
        size = 0
        # Stream file to a temporary location to verify size and compute hash
        with open(temp_file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size_bytes:
                    logger.warning(f"File upload rejected: Size {size} exceeds limit of {max_size_bytes} bytes")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": f"File size exceeds the limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
                        }
                    )
                buffer.write(chunk)
    except HTTPException:
        # Re-raise validation exceptions
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise
    except Exception as e:
        logger.error(f"Error writing uploaded file: {e}", exc_info=True)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_WRITE_ERROR",
                "message": "Could not save uploaded file."
            }
        )

    # 4. Verify the file is decodable as an image
    try:
        with PILImage.open(temp_file_path) as img:
            width, height = img.size
    except (UnidentifiedImageError, ValueError) as e:
        logger.warning(f"File upload rejected: File is not a valid decodable image: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CORRUPTED_IMAGE",
                "message": "File upload rejected: Image contents are invalid or corrupted."
            }
        )

    # 5. Compute SHA-256 hash and check duplicate
    sha256_hash = calculate_sha256(temp_file_path)
    
    existing_image = db.query(Image).filter(Image.sha256_hash == sha256_hash).first()
    if existing_image:
        logger.warning(f"File upload rejected: Exact duplicate hash detected: {sha256_hash}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_UPLOAD",
                "message": f"This image has already been uploaded with ID {existing_image.id}."
            }
        )

    # 6. Save image to final location with secure server-side filename
    image_id = str(uuid.uuid4())
    final_filename = f"{image_id}{ext}"
    final_file_path = os.path.join(settings.UPLOAD_DIR, final_filename)
    
    try:
        shutil.move(temp_file_path, final_file_path)
        logger.info(f"Image stored successfully at {final_file_path}")
    except Exception as e:
        logger.error(f"Error moving file to final path: {e}", exc_info=True)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "FILE_PERSISTENCE_ERROR",
                "message": "Could not finalize image storage."
            }
        )

    try:
        # 7. Save metadata in DB
        new_image = Image(
            id=image_id,
            filename=final_filename,
            original_filename=file.filename or "unknown",
            file_path=final_file_path,
            file_size=size,
            mime_type=file.content_type,
            width=width,
            height=height,
            sha256_hash=sha256_hash
        )
        db.add(new_image)
        db.flush() # Populate models and verify FKs

        # 8. Create processing job (public processing_id is the Job ID)
        job_id = str(uuid.uuid4())
        new_job = ProcessingJob(
            id=job_id,
            image_id=image_id,
            status="pending"
        )
        db.add(new_job)
        db.commit()

        # 9. Enqueue job
        job_queue_manager.enqueue(job_id)
        
        logger.info(f"Job created successfully: job_id={job_id}, image_id={image_id}", extra={"processing_id": job_id})
        
        return UploadResponse(
            processing_id=job_id,
            image_id=image_id,
            status="pending",
            message="Image uploaded successfully"
        )

    except Exception as e:
        db.rollback()
        # Clean up saved file if DB write fails
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        logger.error(f"Database error during image upload registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DATABASE_ERROR",
                "message": "Failed to store upload metadata in the database."
            }
        )
