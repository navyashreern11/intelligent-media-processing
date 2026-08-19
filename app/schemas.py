from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

# Standard Error Response Schemas
class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

# Upload Response Schema
class UploadResponse(BaseModel):
    processing_id: str
    image_id: str
    status: str
    message: str

# Status Response Schema
class StatusResponse(BaseModel):
    processing_id: str
    status: str
    error: Optional[str] = None

# Analysis Sub-schemas
class BlurAnalysis(BaseModel):
    score: Optional[float] = None
    is_blurry: Optional[bool] = None
    confidence: Optional[float] = None

class BrightnessAnalysis(BaseModel):
    score: Optional[float] = None
    is_low_light: Optional[bool] = None
    confidence: Optional[float] = None

class DuplicateAnalysis(BaseModel):
    is_duplicate: Optional[bool] = None
    duplicate_of: Optional[str] = None

class OCRAnalysis(BaseModel):
    text: Optional[str] = None

class VehicleNumberAnalysis(BaseModel):
    value: Optional[str] = None
    valid: Optional[bool] = None

class DimensionsAnalysis(BaseModel):
    valid: Optional[bool] = None

class ScreenshotAnalysis(BaseModel):
    suspected: Optional[bool] = None

class PhotoOfPhotoAnalysis(BaseModel):
    suspected: Optional[bool] = None

class TamperingAnalysis(BaseModel):
    suspected: Optional[bool] = None
    confidence: Optional[float] = None

# Comprehensive Analysis Schema
class DetailedAnalysis(BaseModel):
    blur: BlurAnalysis
    brightness: BrightnessAnalysis
    duplicate: DuplicateAnalysis
    ocr: OCRAnalysis
    vehicle_number: VehicleNumberAnalysis
    dimensions: DimensionsAnalysis
    screenshot: ScreenshotAnalysis
    photo_of_photo: PhotoOfPhotoAnalysis
    tampering: TamperingAnalysis
    overall_confidence: Optional[float] = None

# Results Response Schema
class ResultsResponse(BaseModel):
    processing_id: str
    status: str
    analysis: Optional[DetailedAnalysis] = None
    error: Optional[str] = None

# Health Check Response Schema
class HealthResponse(BaseModel):
    status: str
    database: str
    worker: str
