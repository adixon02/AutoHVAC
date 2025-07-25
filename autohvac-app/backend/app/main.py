"""
AutoHVAC V2 Backend - Clean FastAPI implementation
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import uuid
import re

from .core import settings, setup_logging, get_logger, create_http_exception
from .routes import blueprint, job, health, climate


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("AutoHVAC API V2 starting up...")
    yield
    logger.info("AutoHVAC API V2 shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Professional HVAC load calculations and system recommendations",
    version=settings.app_version,
    lifespan=lifespan,
    redirect_slashes=True
)


# CORS middleware with dynamic origin validation
def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed including wildcard subdomains"""
    if origin in settings.allowed_origins:
        return True
    
    # Check for auto-hvac.*.vercel.app pattern
    if re.match(r"https://auto-hvac-.+\.vercel\.app$", origin):
        return True
        
    return False


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://auto-hvac-.*\.vercel\.app$",
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Request ID middleware for tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracking"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Log request start
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else None,
            "user_agent": request.headers.get("user-agent"),
            "origin": request.headers.get("origin")
        }
    )
    
    response = await call_next(request)
    
    # Log request completion
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
    )
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with CORS headers"""
    origin = request.headers.get("origin")
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    
    # Add CORS headers for error responses
    if origin and is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    origin = request.headers.get("origin")
    
    response = JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )
    
    # Add CORS headers
    if origin and is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        "Unhandled exception", 
        extra={"request_id": request_id, "exception": str(exc)},
        exc_info=True
    )
    
    origin = request.headers.get("origin")
    
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id
        }
    )
    
    # Add CORS headers
    if origin and is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


# Include routers with v2 prefix
app.include_router(health.router, tags=["health"])
app.include_router(blueprint.router, prefix="/api/v2/blueprint", tags=["blueprint"])
app.include_router(job.router, prefix="/api/v2/job", tags=["jobs"])
app.include_router(climate.router, prefix="/api/v2/climate", tags=["climate"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AutoHVAC API V2 - Clean architecture",
        "version": settings.app_version,
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )