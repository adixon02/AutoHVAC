#!/usr/bin/env python3
"""
Comprehensive Error Handling System for AutoHVAC Backend
Professional-grade error handling with proper HTTP status codes, logging, and monitoring
"""

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Dict, Any, Optional, Union, Type
import logging
import traceback
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import sys

from .logging_config import log_api_request, get_logger

logger = get_logger(__name__)

class ErrorCategory(Enum):
    """Error categories for better monitoring and handling"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    PROCESSING = "processing"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"

class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AutoHVACError:
    """
    Structured error representation
    """
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    details: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    http_status: int = 500
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = {
            "error_code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.user_message:
            result["user_message"] = self.user_message
        
        if self.details:
            result["details"] = self.details
        
        return result

# Predefined error types
class AutoHVACErrors:
    """
    Predefined error definitions for consistent error handling
    """
    
    # Validation Errors
    INVALID_FILE_TYPE = AutoHVACError(
        code="INVALID_FILE_TYPE",
        message="Uploaded file type is not supported",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        user_message="Please upload a PDF file for blueprint analysis",
        http_status=400
    )
    
    FILE_TOO_LARGE = AutoHVACError(
        code="FILE_TOO_LARGE",
        message="Uploaded file exceeds maximum size limit",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        user_message="File is too large. Please upload a file smaller than 10MB",
        http_status=400
    )
    
    INVALID_ZIP_CODE = AutoHVACError(
        code="INVALID_ZIP_CODE",
        message="ZIP code format is invalid",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        user_message="Please enter a valid 5-digit ZIP code",
        http_status=400
    )
    
    # Not Found Errors
    JOB_NOT_FOUND = AutoHVACError(
        code="JOB_NOT_FOUND",
        message="Processing job not found",
        category=ErrorCategory.NOT_FOUND,
        severity=ErrorSeverity.MEDIUM,
        user_message="Job not found or has expired",
        http_status=404
    )
    
    FILE_NOT_FOUND = AutoHVACError(
        code="FILE_NOT_FOUND",
        message="Requested file not found",
        category=ErrorCategory.NOT_FOUND,
        severity=ErrorSeverity.MEDIUM,
        user_message="The requested file is not available",
        http_status=404
    )
    
    # Processing Errors
    BLUEPRINT_PROCESSING_FAILED = AutoHVACError(
        code="BLUEPRINT_PROCESSING_FAILED",
        message="Blueprint analysis failed",
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.HIGH,
        user_message="We encountered an issue analyzing your blueprint. Please try again",
        http_status=500
    )
    
    PDF_EXTRACTION_FAILED = AutoHVACError(
        code="PDF_EXTRACTION_FAILED",
        message="Failed to extract data from PDF",
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.MEDIUM,
        user_message="Unable to read the PDF file. Please ensure it's not corrupted",
        http_status=422
    )
    
    # Database Errors
    DATABASE_CONNECTION_FAILED = AutoHVACError(
        code="DATABASE_CONNECTION_FAILED",
        message="Database connection failed",
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.CRITICAL,
        user_message="Service temporarily unavailable. Please try again later",
        http_status=503
    )
    
    CLIMATE_DATA_UNAVAILABLE = AutoHVACError(
        code="CLIMATE_DATA_UNAVAILABLE",
        message="Climate data not available for location",
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.MEDIUM,
        user_message="Climate data not available for this ZIP code",
        http_status=404
    )
    
    # External Service Errors
    EXTERNAL_SERVICE_TIMEOUT = AutoHVACError(
        code="EXTERNAL_SERVICE_TIMEOUT",
        message="External service request timed out",
        category=ErrorCategory.EXTERNAL_SERVICE,
        severity=ErrorSeverity.HIGH,
        user_message="Service is experiencing delays. Please try again",
        http_status=503
    )
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = AutoHVACError(
        code="RATE_LIMIT_EXCEEDED",
        message="Rate limit exceeded",
        category=ErrorCategory.RATE_LIMIT,
        severity=ErrorSeverity.MEDIUM,
        user_message="Too many requests. Please wait before trying again",
        http_status=429
    )
    
    # Internal Errors
    INTERNAL_SERVER_ERROR = AutoHVACError(
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
        category=ErrorCategory.INTERNAL,
        severity=ErrorSeverity.CRITICAL,
        user_message="An unexpected error occurred. Our team has been notified",
        http_status=500
    )

class AutoHVACException(Exception):
    """
    Custom exception class for AutoHVAC errors
    """
    
    def __init__(
        self,
        error: AutoHVACError,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.error = error
        self.details = details or {}
        self.cause = cause
        
        # Update error details
        if self.details:
            self.error.details = {**(self.error.details or {}), **self.details}
        
        super().__init__(self.error.message)

async def autohvac_exception_handler(request: Request, exc: AutoHVACException) -> JSONResponse:
    """
    Handler for AutoHVAC exceptions
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    # Log the error
    logger.error(
        f"AutoHVAC error: {exc.error.code}",
        extra={
            'request_id': request_id,
            'extra_data': {
                'error_code': exc.error.code,
                'category': exc.error.category.value,
                'severity': exc.error.severity.value,
                'details': exc.details,
                'cause': str(exc.cause) if exc.cause else None,
                'path': str(request.url.path),
                'method': request.method
            }
        },
        exc_info=exc.cause
    )
    
    # Prepare response
    response_data = exc.error.to_dict()
    response_data['request_id'] = request_id
    
    return JSONResponse(
        status_code=exc.error.http_status,
        content=response_data
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for FastAPI HTTP exceptions
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    # Map status codes to error categories
    category_map = {
        400: ErrorCategory.VALIDATION,
        401: ErrorCategory.AUTHENTICATION,
        403: ErrorCategory.AUTHORIZATION,
        404: ErrorCategory.NOT_FOUND,
        422: ErrorCategory.VALIDATION,
        429: ErrorCategory.RATE_LIMIT,
        500: ErrorCategory.INTERNAL,
        503: ErrorCategory.EXTERNAL_SERVICE
    }
    
    category = category_map.get(exc.status_code, ErrorCategory.INTERNAL)
    severity = ErrorSeverity.HIGH if exc.status_code >= 500 else ErrorSeverity.MEDIUM
    
    # Log the error
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            'request_id': request_id,
            'extra_data': {
                'status_code': exc.status_code,
                'detail': exc.detail,
                'category': category.value,
                'severity': severity.value,
                'path': str(request.url.path),
                'method': request.method
            }
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "category": category.value,
            "severity": severity.value,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for request validation errors
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    # Extract validation details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Request validation failed",
        extra={
            'request_id': request_id,
            'extra_data': {
                'validation_errors': validation_errors,
                'path': str(request.url.path),
                'method': request.method
            }
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "category": ErrorCategory.VALIDATION.value,
            "severity": ErrorSeverity.LOW.value,
            "details": {
                "validation_errors": validation_errors
            },
            "user_message": "Please check your input and try again",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unexpected exceptions
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    # Log the error with full traceback
    logger.error(
        f"Unexpected error: {type(exc).__name__}",
        extra={
            'request_id': request_id,
            'extra_data': {
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'path': str(request.url.path),
                'method': request.method,
                'traceback': traceback.format_exc()
            }
        },
        exc_info=True
    )
    
    # Use internal server error
    error = AutoHVACErrors.INTERNAL_SERVER_ERROR
    response_data = error.to_dict()
    response_data['request_id'] = request_id
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )

def setup_error_handlers(app):
    """
    Setup error handlers for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AutoHVACException, autohvac_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers configured successfully")

# Utility functions for common error scenarios

def validate_file_upload(file, max_size_mb: int = 10, allowed_extensions: set = {".pdf"}) -> None:
    """
    Validate file upload
    
    Args:
        file: Uploaded file
        max_size_mb: Maximum file size in MB
        allowed_extensions: Set of allowed file extensions
        
    Raises:
        AutoHVACException: If validation fails
    """
    if not file or not file.filename:
        raise AutoHVACException(
            AutoHVACErrors.INVALID_FILE_TYPE,
            details={"reason": "No file provided"}
        )
    
    # Check file extension
    file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if f".{file_ext}" not in allowed_extensions:
        raise AutoHVACException(
            AutoHVACErrors.INVALID_FILE_TYPE,
            details={
                "uploaded_extension": file_ext,
                "allowed_extensions": list(allowed_extensions)
            }
        )
    
    # Check file size (this would need to be implemented based on how file size is available)
    # For now, we'll skip this check as it requires reading the file

def validate_zip_code(zip_code: Optional[str]) -> str:
    """
    Validate ZIP code format
    
    Args:
        zip_code: ZIP code to validate
        
    Returns:
        Normalized ZIP code
        
    Raises:
        AutoHVACException: If ZIP code is invalid
    """
    if not zip_code:
        raise AutoHVACException(
            AutoHVACErrors.INVALID_ZIP_CODE,
            details={"reason": "ZIP code is required"}
        )
    
    # Remove spaces and normalize
    zip_code = zip_code.strip().replace(" ", "")
    
    # Check format (basic 5-digit validation)
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise AutoHVACException(
            AutoHVACErrors.INVALID_ZIP_CODE,
            details={
                "provided_zip": zip_code,
                "expected_format": "5-digit number"
            }
        )
    
    return zip_code

def handle_database_error(error: Exception, operation: str) -> None:
    """
    Handle database errors consistently
    
    Args:
        error: Database error
        operation: Description of the operation that failed
        
    Raises:
        AutoHVACException: Appropriate database error
    """
    error_message = str(error).lower()
    
    if "connection" in error_message or "timeout" in error_message:
        raise AutoHVACException(
            AutoHVACErrors.DATABASE_CONNECTION_FAILED,
            details={"operation": operation, "original_error": str(error)},
            cause=error
        )
    else:
        # Generic database error
        raise AutoHVACException(
            AutoHVACErrors.INTERNAL_SERVER_ERROR,
            details={
                "operation": operation,
                "error_type": "database",
                "original_error": str(error)
            },
            cause=error
        )

def handle_file_system_error(error: Exception, operation: str, file_path: str = None) -> None:
    """
    Handle file system errors consistently
    
    Args:
        error: File system error
        operation: Description of the operation that failed
        file_path: Optional file path that caused the error
        
    Raises:
        AutoHVACException: Appropriate file system error
    """
    if isinstance(error, FileNotFoundError):
        raise AutoHVACException(
            AutoHVACErrors.FILE_NOT_FOUND,
            details={
                "operation": operation,
                "file_path": file_path,
                "original_error": str(error)
            },
            cause=error
        )
    else:
        # Generic file system error
        raise AutoHVACException(
            AutoHVACErrors.INTERNAL_SERVER_ERROR,
            details={
                "operation": operation,
                "error_type": "file_system",
                "file_path": file_path,
                "original_error": str(error)
            },
            cause=error
        )