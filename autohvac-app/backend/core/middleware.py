#!/usr/bin/env python3
"""
Middleware for AutoHVAC Backend
Request tracking, performance monitoring, and security features
"""

import time
import uuid
import logging
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

from .logging_config import request_context, log_api_request, get_logger
from .error_handling import AutoHVACErrors, AutoHVACException

logger = get_logger(__name__)

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking requests with unique IDs and performance monitoring
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.excluded_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Skip tracking for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        
        # Log request start
        with request_context(request_id):
            logger.info(
                f"Request started: {method} {path}",
                extra={
                    'extra_data': {
                        'method': method,
                        'path': path,
                        'query_params': query_params,
                        'user_agent': request.headers.get('user-agent', ''),
                        'client_ip': self._get_client_ip(request)
                    }
                }
            )
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate execution time
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Log successful request
                log_api_request(
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    execution_time_ms=execution_time_ms,
                    request_id=request_id
                )
                
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except Exception as e:
                # Calculate execution time for failed requests
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Log failed request
                log_api_request(
                    method=method,
                    path=path,
                    status_code=500,
                    execution_time_ms=execution_time_ms,
                    request_id=request_id,
                    error=str(e)
                )
                
                # Re-raise the exception to be handled by error handlers
                raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware
    Note: In production, this should use Redis or similar distributed cache
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # In-memory storage (use Redis in production)
        self._minute_buckets: Dict[str, Dict[int, int]] = {}
        self._hour_buckets: Dict[str, Dict[int, int]] = {}
        
        # Excluded paths that don't count towards rate limit
        self.excluded_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        current_time = int(time.time())
        current_minute = current_time // 60
        current_hour = current_time // 3600
        
        # Check minute limit
        if not self._check_rate_limit(
            client_id, current_minute, self.requests_per_minute, self._minute_buckets
        ):
            logger.warning(
                f"Rate limit exceeded (per minute) for client {client_id}",
                extra={
                    'extra_data': {
                        'client_id': client_id,
                        'limit_type': 'per_minute',
                        'limit': self.requests_per_minute,
                        'path': request.url.path
                    }
                }
            )
            raise AutoHVACException(AutoHVACErrors.RATE_LIMIT_EXCEEDED)
        
        # Check hour limit
        if not self._check_rate_limit(
            client_id, current_hour, self.requests_per_hour, self._hour_buckets
        ):
            logger.warning(
                f"Rate limit exceeded (per hour) for client {client_id}",
                extra={
                    'extra_data': {
                        'client_id': client_id,
                        'limit_type': 'per_hour',
                        'limit': self.requests_per_hour,
                        'path': request.url.path
                    }
                }
            )
            raise AutoHVACException(AutoHVACErrors.RATE_LIMIT_EXCEEDED)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        minute_count = self._minute_buckets.get(client_id, {}).get(current_minute, 0)
        hour_count = self._hour_buckets.get(client_id, {}).get(current_hour, 0)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, self.requests_per_minute - minute_count)
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, self.requests_per_hour - hour_count)
        )
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # In production, might want to use authenticated user ID
        # For now, use IP address
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def _check_rate_limit(
        self,
        client_id: str,
        time_bucket: int,
        limit: int,
        buckets: Dict[str, Dict[int, int]]
    ) -> bool:
        """Check if client is within rate limit"""
        if client_id not in buckets:
            buckets[client_id] = {}
        
        client_buckets = buckets[client_id]
        current_count = client_buckets.get(time_bucket, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        client_buckets[time_bucket] = current_count + 1
        
        # Clean old buckets (keep only last 2 time periods)
        old_buckets = [bucket for bucket in client_buckets.keys() if bucket < time_bucket - 1]
        for old_bucket in old_buckets:
            del client_buckets[old_bucket]
        
        return True

class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size
    """
    
    def __init__(self, app: ASGIApp, max_size_mb: int = 10):
        super().__init__(app)
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header if present
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size_bytes:
                    logger.warning(
                        f"Request size limit exceeded: {size} bytes",
                        extra={
                            'extra_data': {
                                'size_bytes': size,
                                'limit_bytes': self.max_size_bytes,
                                'path': request.url.path
                            }
                        }
                    )
                    raise AutoHVACException(
                        AutoHVACErrors.FILE_TOO_LARGE,
                        details={
                            'size_mb': size / 1024 / 1024,
                            'limit_mb': self.max_size_bytes / 1024 / 1024
                        }
                    )
            except ValueError:
                pass  # Invalid Content-Length header, let it through
        
        return await call_next(request)

class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle health check requests efficiently
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.health_paths = {"/health", "/healthz", "/ping"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle health checks quickly without full processing
        if request.url.path in self.health_paths and request.method == "GET":
            return JSONResponse(
                status_code=200,
                content={"status": "healthy", "timestamp": time.time()}
            )
        
        return await call_next(request)

def setup_middleware(app):
    """
    Setup all middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added runs first)
    
    # Health check middleware (runs first for efficiency)
    app.add_middleware(HealthCheckMiddleware)
    
    # Request size limiting
    app.add_middleware(RequestSizeMiddleware, max_size_mb=10)
    
    # Rate limiting
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=100,  # Generous limits for professional users
        requests_per_hour=2000
    )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request tracking (runs last, logs everything)
    app.add_middleware(RequestTrackingMiddleware)
    
    logger.info("Middleware stack configured successfully")