#!/usr/bin/env python3
"""
Centralized Logging Configuration for AutoHVAC Backend
Professional-grade logging with structured output, request tracking, and performance monitoring
"""

import logging
import logging.handlers
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
import uuid
from contextlib import contextmanager
import time

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
            
        if hasattr(record, 'execution_time'):
            log_entry['execution_time_ms'] = record.execution_time
            
        if hasattr(record, 'extra_data'):
            log_entry['extra_data'] = record.extra_data
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)

class RequestContextFilter(logging.Filter):
    """
    Filter to add request context to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add request ID from context if available
        request_id = getattr(logging, '_request_id', None)
        if request_id:
            record.request_id = request_id
        
        return True

def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_format: bool = True
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files
        log_to_console: Whether to log to console
        json_format: Whether to use JSON formatting
    """
    
    # Get numeric log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Request context filter
    context_filter = RequestContextFilter()
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.addFilter(context_filter)
        
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
        
        root_logger.addHandler(console_handler)
    
    # File handlers
    if log_to_file:
        # Main application log
        main_file_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "autohvac.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        main_file_handler.setLevel(numeric_level)
        main_file_handler.addFilter(context_filter)
        
        if json_format:
            main_file_handler.setFormatter(JSONFormatter())
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            main_file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(main_file_handler)
        
        # Error log (errors and above only)
        error_file_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.addFilter(context_filter)
        error_file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_file_handler)
        
        # Performance log
        perf_logger = logging.getLogger('performance')
        perf_file_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "performance.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        perf_file_handler.setLevel(logging.INFO)
        perf_file_handler.setFormatter(JSONFormatter())
        perf_logger.addHandler(perf_file_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False
    
    # Silence noisy third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    logging.info("Logging system initialized", extra={
        'extra_data': {
            'level': level,
            'log_to_file': log_to_file,
            'log_to_console': log_to_console,
            'json_format': json_format
        }
    })

@contextmanager
def request_context(request_id: Optional[str] = None):
    """
    Context manager to set request ID for logging
    
    Args:
        request_id: Optional request ID, generates one if not provided
    """
    if not request_id:
        request_id = str(uuid.uuid4())[:8]
    
    # Store in logging module for global access
    old_request_id = getattr(logging, '_request_id', None)
    logging._request_id = request_id
    
    try:
        yield request_id
    finally:
        if old_request_id:
            logging._request_id = old_request_id
        else:
            delattr(logging, '_request_id')

@contextmanager
def performance_timer(operation_name: str, logger: Optional[logging.Logger] = None):
    """
    Context manager to time operations and log performance
    
    Args:
        operation_name: Name of the operation being timed
        logger: Optional logger instance, uses performance logger if not provided
    """
    if not logger:
        logger = logging.getLogger('performance')
    
    start_time = time.time()
    
    try:
        yield
    finally:
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(
            f"Operation '{operation_name}' completed",
            extra={
                'execution_time': execution_time,
                'extra_data': {
                    'operation': operation_name,
                    'duration_ms': execution_time
                }
            }
        )

def log_api_request(
    method: str,
    path: str,
    status_code: int,
    execution_time_ms: float,
    request_id: str,
    user_id: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Log API request details
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        execution_time_ms: Request execution time in milliseconds
        request_id: Request ID
        user_id: Optional user ID
        error: Optional error message
    """
    logger = logging.getLogger('api')
    
    log_data = {
        'method': method,
        'path': path,
        'status_code': status_code,
        'execution_time_ms': execution_time_ms,
        'request_id': request_id
    }
    
    if user_id:
        log_data['user_id'] = user_id
    
    if error:
        log_data['error'] = error
    
    level = logging.ERROR if status_code >= 400 else logging.INFO
    message = f"{method} {path} - {status_code}"
    
    logger.log(
        level,
        message,
        extra={
            'request_id': request_id,
            'execution_time': execution_time_ms,
            'extra_data': log_data
        }
    )

def log_blueprint_processing(
    job_id: str,
    stage: str,
    status: str,
    execution_time_ms: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """
    Log blueprint processing events
    
    Args:
        job_id: Blueprint processing job ID
        stage: Processing stage (upload, extraction, analysis, etc.)
        status: Status (started, completed, failed)
        execution_time_ms: Optional execution time
        details: Optional additional details
        error: Optional error message
    """
    logger = logging.getLogger('blueprint')
    
    log_data = {
        'job_id': job_id,
        'stage': stage,
        'status': status
    }
    
    if execution_time_ms:
        log_data['execution_time_ms'] = execution_time_ms
    
    if details:
        log_data.update(details)
    
    if error:
        log_data['error'] = error
    
    level = logging.ERROR if status == 'failed' else logging.INFO
    message = f"Blueprint {stage} {status} for job {job_id}"
    
    extra_data = {'extra_data': log_data}
    if execution_time_ms:
        extra_data['execution_time'] = execution_time_ms
    
    logger.log(level, message, extra=extra_data)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Initialize logging on module import
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
    log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true",
    json_format=os.getenv("LOG_JSON_FORMAT", "true").lower() == "true"
)