"""
Structured logging configuration
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict
import json

from .config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_logging():
    """Configure application logging"""
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with structured format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


# Request logging utilities
def log_request_start(logger: logging.Logger, method: str, path: str, **kwargs):
    """Log request start with structured data"""
    extra = {"method": method, "path": path, **kwargs}
    logger.info("Request started", extra=extra)
    

def log_request_end(logger: logging.Logger, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """Log request completion with structured data"""
    extra = {
        "method": method, 
        "path": path, 
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs
    }
    logger.info("Request completed", extra=extra)