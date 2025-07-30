"""
Logging Utilities for Consistent Structured Logging

Provides helpers for structured logging with context and performance tracking.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, TypeVar, List
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Timer:
    """Simple timer context manager for measuring operation duration."""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.duration = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        self.logger.info(f"{self.name} completed in {self.duration:.2f}s")
        

@contextmanager
def log_operation(operation_name: str, context: Dict[str, Any], logger: Optional[logging.Logger] = None):
    """
    Context manager for logging operation start, end, and duration with context.
    
    Usage:
        with log_operation("blueprint_parsing", {"project_id": "123", "file": "test.pdf"}):
            # Do operation
            pass
    """
    logger = logger or logging.getLogger(__name__)
    start_time = time.time()
    
    # Log operation start
    logger.info(f"Starting {operation_name}", extra={
        'operation': operation_name,
        'context': context,
        'status': 'started'
    })
    
    try:
        yield
        # Log successful completion
        duration = time.time() - start_time
        logger.info(f"Completed {operation_name} in {duration:.2f}s", extra={
            'operation': operation_name,
            'context': context,
            'status': 'completed',
            'duration_seconds': duration
        })
    except Exception as e:
        # Log failure
        duration = time.time() - start_time
        logger.error(f"Failed {operation_name} after {duration:.2f}s: {str(e)}", extra={
            'operation': operation_name,
            'context': context,
            'status': 'failed',
            'duration_seconds': duration,
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        raise


def log_with_context(level: str, message: str, context: Dict[str, Any], logger: Optional[logging.Logger] = None):
    """
    Log a message with structured context.
    
    Args:
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: Additional context data
        logger: Logger instance (uses module logger if None)
    """
    logger = logger or logging.getLogger(__name__)
    log_func = getattr(logger, level.lower(), logger.info)
    
    log_func(message, extra={'context': context})


def log_performance_metric(metric_name: str, value: float, unit: str = "ms", 
                          tags: Optional[Dict[str, str]] = None, 
                          logger: Optional[logging.Logger] = None):
    """
    Log a performance metric with optional tags.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Optional tags for categorization
        logger: Logger instance
    """
    logger = logger or logging.getLogger(__name__)
    
    logger.info(f"[METRIC] {metric_name}: {value:.2f} {unit}", extra={
        'metric_type': 'performance',
        'metric_name': metric_name,
        'metric_value': value,
        'metric_unit': unit,
        'tags': tags or {}
    })


def timed_operation(operation_name: Optional[str] = None):
    """
    Decorator to time function execution and log results.
    
    Usage:
        @timed_operation("parse_blueprint")
        def parse_blueprint(pdf_path):
            # Function implementation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"[TIMING] {name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[TIMING] {name} failed after {duration:.2f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator


def log_data_quality(data_type: str, quality_score: float, 
                    issues: Optional[List[str]] = None,
                    logger: Optional[logging.Logger] = None):
    """
    Log data quality information.
    
    Args:
        data_type: Type of data (blueprint, climate, envelope, etc.)
        quality_score: Quality score (0.0-1.0)
        issues: List of quality issues found
        logger: Logger instance
    """
    logger = logger or logging.getLogger(__name__)
    
    level = "info" if quality_score >= 0.8 else "warning"
    message = f"[DATA_QUALITY] {data_type}: {quality_score:.2f}"
    
    log_with_context(level, message, {
        'data_type': data_type,
        'quality_score': quality_score,
        'issues': issues or [],
        'issues_count': len(issues) if issues else 0
    }, logger)


def create_operation_logger(operation_id: str, base_logger: Optional[logging.Logger] = None):
    """
    Create a logger that automatically includes operation ID in all messages.
    
    Args:
        operation_id: Unique operation identifier
        base_logger: Base logger to use
        
    Returns:
        Logger adapter with operation context
    """
    base_logger = base_logger or logging.getLogger(__name__)
    
    class OperationLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['operation_id'] = operation_id
            return msg, kwargs
    
    return OperationLoggerAdapter(base_logger, {})