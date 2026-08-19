from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.sql import text


from app.database import engine, Base, SessionLocal
from app.logging_config import logger
from app.config import settings
from app.api.upload import router as upload_router
from app.api.results import router as results_router
from app.api.analytics import router as analytics_router
from app.worker.queue import job_queue_manager
from app.schemas import HealthResponse, ErrorResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown lifecycles of the application."""
    # Startup: Ensure database tables are created
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Startup: Launch background worker thread
    logger.info("Starting background worker thread...")
    job_queue_manager.start()
    
    yield
    
    # Shutdown: Stop background worker thread clean
    logger.info("Shutting down background worker thread...")
    job_queue_manager.stop()

# Initialize FastAPI app
app = FastAPI(
    title="Intelligent Media Processing Pipeline",
    description=(
        "A take-home backend system that ingests vehicle images, stores metadata, "
        "processes images asynchronously, and exposes structured quality analysis reports."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)
BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_FILE = BASE_DIR / "dashboard" / "index.html"


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_FILE)
# Exception Handlers to keep API error format consistent
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats standard HTTPExceptions into structured error responses."""
    # Ensure details are formatted as dict
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        error_code = detail["code"]
        error_message = detail["message"]
    else:
        error_code = "BAD_REQUEST"
        error_message = str(detail)
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic/FastAPI validation exceptions into structured error responses."""
    # Gather errors
    errors = exc.errors()
    message = "Validation failed: " + "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in errors])
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Formats unhandled python exceptions without exposing stack traces."""
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact the administrator."
            }
        }
    )

# Register Routers under v1 prefix
app.include_router(upload_router, prefix="/api/v1")
app.include_router(results_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Utility"],
    summary="Health check endpoint"
)
def health_check():
    """Checks the health of the application, database, and background worker."""
    db_status = "connected"
    try:
        # Perform quick database check
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
        db_status = "disconnected"

    worker_status = job_queue_manager.get_status()
    
    overall_status = "healthy"
    if db_status != "connected" or worker_status != "running":
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        worker=worker_status
    )
