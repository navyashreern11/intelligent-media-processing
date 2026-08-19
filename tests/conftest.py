import os
import pytest
from sqlalchemy.sql import text

# Force the database URL to point to the test database BEFORE any app modules load
os.environ["DATABASE_URL"] = "sqlite:///./test_media_processing.db"

# Now we can safely import Base and engine
from app.database import Base, engine, SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initializes the test database schema before all tests and cleans up afterwards."""
    # Ensure test directories exist
    os.makedirs("uploads", exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up tables
    Base.metadata.drop_all(bind=engine)
    
    # Remove test database file
    if os.path.exists("test_media_processing.db"):
        try:
            os.remove("test_media_processing.db")
        except PermissionError:
            pass

@pytest.fixture(scope="function", autouse=True)
def clean_database():
    """Deletes all records from database tables before each test to ensure test isolation."""
    db = SessionLocal()
    try:
        # Disable foreign key checks for SQLite table purging
        db.execute(text("PRAGMA foreign_keys = OFF"))
        db.execute(text("DELETE FROM analysis_results"))
        db.execute(text("DELETE FROM processing_jobs"))
        db.execute(text("DELETE FROM images"))
        db.execute(text("PRAGMA foreign_keys = ON"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
