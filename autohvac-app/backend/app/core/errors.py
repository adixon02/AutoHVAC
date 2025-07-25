"""
Custom exception classes for the application
"""
from fastapi import HTTPException
from typing import Optional, Dict, Any


class AutoHVACException(Exception):
    """Base exception for AutoHVAC application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileUploadError(AutoHVACException):
    """Raised when file upload fails"""
    pass


class FileSizeError(AutoHVACException):
    """Raised when file is too large"""
    pass


class FileProcessingError(AutoHVACException):
    """Raised when file processing fails"""
    pass


class JobNotFoundError(AutoHVACException):
    """Raised when job is not found"""
    pass


class JobTimeoutError(AutoHVACException):
    """Raised when job times out"""
    pass


class ClimateDataError(AutoHVACException):
    """Raised when climate data retrieval fails"""
    pass


# HTTP Exception handlers
def create_http_exception(status_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create an HTTPException with consistent format"""
    content = {"detail": message}
    if details:
        content["details"] = details
    
    return HTTPException(status_code=status_code, detail=content)