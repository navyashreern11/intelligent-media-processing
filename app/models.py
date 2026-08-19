import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Image(Base):
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False, unique=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("ProcessingJob", back_populates="image", cascade="all, delete-orphan")

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    image_id = Column(String(36), ForeignKey("images.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True) # pending, processing, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1024), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    image = relationship("Image", back_populates="jobs")
    results = relationship("AnalysisResult", back_populates="job", uselist=False, cascade="all, delete-orphan")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("processing_jobs.id"), nullable=False, unique=True)
    
    # Check 1: Blur
    blur_score = Column(Float, nullable=True)
    is_blurry = Column(Boolean, nullable=True)
    blur_confidence = Column(Float, nullable=True)
    
    # Check 2: Brightness
    brightness_score = Column(Float, nullable=True)
    is_low_light = Column(Boolean, nullable=True)
    brightness_confidence = Column(Float, nullable=True)
    
    # Check 3: Duplicate
    is_duplicate = Column(Boolean, nullable=True)
    duplicate_of = Column(String(36), nullable=True) # References images.id of the original image
    
    # Check 4: OCR
    ocr_text = Column(String(1024), nullable=True)
    
    # Check 5: Indian Vehicle Number Validation
    vehicle_number = Column(String(100), nullable=True)
    vehicle_number_valid = Column(Boolean, nullable=True)
    
    # Check 6: Dimension Validation
    dimension_valid = Column(Boolean, nullable=True)
    
    # Optional Heuristics
    screenshot_suspected = Column(Boolean, nullable=True)
    photo_of_photo_suspected = Column(Boolean, nullable=True)
    tampering_suspected = Column(Boolean, nullable=True)
    
    # Overall Score
    overall_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("ProcessingJob", back_populates="results")

