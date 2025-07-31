from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import traceback
import logging
import os
from typing import Dict, Any

# Allowed origins - should match the ones in main.py
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://autohvac-frontend.onrender.com",
    "https://autohvac.ai",
]

def create_error_response(error_type: str, message: str, status_code: int = 500) -> Dict[str, Any]:
    """Create structured error response"""
    return {
        "error": {
            "type": error_type,
            "message": message
        }
    }

async def traceback_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.error(tb)
    
    # Determine error type based on exception
    error_type = type(exc).__name__
    if "not found" in str(exc).lower():
        error_type = "JobNotFound"
        status_code = 404
    elif "database" in str(exc).lower() or "connection" in str(exc).lower():
        error_type = "DatabaseError"
        status_code = 503
    else:
        error_type = "InternalServerError"
        status_code = 500
    
    if os.getenv("DEBUG") == "true":
        content = create_error_response(error_type, tb, status_code)
    else:
        content = create_error_response(error_type, "Internal server error", status_code)
    
    response = JSONResponse(status_code=status_code, content=content)
    
    # Add CORS headers to error response
    origin = request.headers.get("origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

class CORSMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers on all responses, including errors"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception as exc:
            # Handle exceptions and ensure CORS headers
            response = await traceback_exception_handler(request, exc)
        
        # Ensure CORS headers are present
        origin = request.headers.get("origin")
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response