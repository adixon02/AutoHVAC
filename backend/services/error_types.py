"""
Custom Error Types for HVAC Load Calculation System

Provides categorized exceptions to distinguish between critical errors
that should stop processing and non-critical errors that can be logged
but shouldn't prevent calculations from completing.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HVACCalculationError(Exception):
    """Base exception for all HVAC calculation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class CriticalError(HVACCalculationError):
    """
    Critical errors that should stop processing.
    
    Examples:
    - PDF file not found or corrupted
    - Blueprint parsing completely failed
    - Manual J calculation failed
    - Required data missing
    """
    pass


class NonCriticalError(HVACCalculationError):
    """
    Non-critical errors that can be logged but shouldn't stop processing.
    
    Examples:
    - Audit logging failed
    - Optional envelope extraction failed
    - Performance metrics collection failed
    - Warning conditions
    """
    pass


class AuditError(NonCriticalError):
    """
    Audit-specific errors that shouldn't affect calculations.
    
    Examples:
    - Database table doesn't exist
    - Audit record creation failed
    - Compliance check failed
    """
    pass


class DataQualityError(NonCriticalError):
    """
    Data quality issues that should be logged but not stop processing.
    
    Examples:
    - Low confidence in extracted data
    - Missing optional fields
    - Unusual but valid values
    """
    pass


class ConfigurationError(CriticalError):
    """
    Configuration errors that prevent proper operation.
    
    Examples:
    - Missing API keys
    - Invalid configuration values
    - Required services unavailable
    """
    pass


class ValidationError(CriticalError):
    """
    Input validation errors.
    
    Examples:
    - Invalid zip code
    - File size exceeds limits
    - Invalid file format
    """
    pass


class TimeoutError(CriticalError):
    """
    Operation timeout errors.
    
    Examples:
    - AI processing timeout
    - PDF parsing timeout
    - External API timeout
    """
    pass


class ResourceError(CriticalError):
    """
    Resource availability errors.
    
    Examples:
    - Out of memory
    - Disk space exhausted
    - Connection pool exhausted
    """
    pass


class NeedsInputError(CriticalError):
    """
    Critical error indicating user input is required to proceed.
    
    Examples:
    - Scale cannot be determined (needs SCALE_OVERRIDE)
    - Blueprint quality too low to process
    - Missing critical envelope data
    - Too many/too few rooms detected
    """
    
    def __init__(self, input_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Args:
            input_type: Type of input needed ('scale', 'plan_quality', 'envelope_gaps')
            message: Descriptive error message
            details: Additional context (current values, thresholds, etc.)
        """
        super().__init__(message, details)
        self.input_type = input_type


def categorize_exception(e: Exception) -> HVACCalculationError:
    """
    Categorize a generic exception into appropriate error type.
    
    Args:
        e: Exception to categorize
        
    Returns:
        Categorized HVACCalculationError
    """
    error_message = str(e)
    error_type = type(e).__name__
    
    # Database-related errors
    if 'relation' in error_message and 'does not exist' in error_message:
        return AuditError(f"Database table missing: {error_message}")
    
    if error_type in ['OperationalError', 'DatabaseError', 'IntegrityError']:
        return AuditError(f"Database error: {error_message}")
    
    # File-related errors
    if error_type in ['FileNotFoundError', 'PermissionError']:
        return CriticalError(f"File access error: {error_message}")
    
    # Timeout errors
    if 'timeout' in error_message.lower() or error_type == 'TimeoutError':
        return TimeoutError(f"Operation timed out: {error_message}")
    
    # Memory/resource errors
    if error_type in ['MemoryError', 'OSError'] and 'space' in error_message.lower():
        return ResourceError(f"Resource exhausted: {error_message}")
    
    # Configuration errors
    if 'api' in error_message.lower() and 'key' in error_message.lower():
        return ConfigurationError(f"API configuration error: {error_message}")
    
    # Default to non-critical for unknown errors
    return NonCriticalError(f"Unexpected error: {error_message}", {'original_type': error_type})


def log_error_with_context(error: HVACCalculationError, context: Dict[str, Any]):
    """
    Log error with additional context information.
    
    Args:
        error: Error to log
        context: Additional context (project_id, stage, etc.)
    """
    log_data = {
        'error_type': type(error).__name__,
        'error_message': error.message,  # Renamed from 'message' to avoid conflict
        'details': error.details,
        'context': context
    }
    
    if isinstance(error, CriticalError):
        logger.error(f"CRITICAL ERROR: {error.message}", extra=log_data)
    else:
        logger.warning(f"Non-critical error: {error.message}", extra=log_data)