import logging
import sys

class ProcessingIdFormatter(logging.Formatter):
    """Custom formatter to include processing_id if present in log record extra."""
    def format(self, record):
        if not hasattr(record, "processing_id"):
            record.processing_id = "-"
        return super().format(record)

def setup_logging():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Format pattern
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] [job:%(processing_id)s] %(message)s"
    formatter = ProcessingIdFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

# Initialize logger
logger = setup_logging()
logger.info("Structured logging initialized")
