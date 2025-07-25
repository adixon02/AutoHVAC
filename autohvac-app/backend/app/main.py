"""
AutoHVAC V2 Backend - Hardened for Large PDF Processing
Rock-solid FastAPI backend with async processing and enhanced CORS
"""
import os
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from contextlib import asynccontextmanager

# Import configuration
from app.config import config

# Import API routers
from api.climate import router as climate_router
from api.calculations import router as calculations_router
from app.routes.upload import router as upload_router

# In-memory job storage (Redis would be better for production)
job_storage = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    logging.info("AutoHVAC Backend started successfully")
    
    yield
    
    # Shutdown
    logging.info("AutoHVAC Backend shutting down")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with redirect_slashes for trailing slash handling
app = FastAPI(
    title="AutoHVAC API V2",
    description="Professional HVAC load calculations and system recommendations - Hardened for large files",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=True
)

# Enhanced CORS middleware - MUST be first middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Global exception handler to ensure CORS headers on ALL responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    
    # Create JSON response with CORS headers
    response = JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
    
    # Add CORS headers manually for error responses
    origin = request.headers.get("origin")
    if origin and config.is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Validation error handler with CORS
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc}")
    
    response = JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": exc.errors()}
    )
    
    # Add CORS headers
    origin = request.headers.get("origin")
    if origin and config.is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# Include API routers with configurable prefix
app.include_router(climate_router, prefix=config.API_VERSION_PREFIX)
app.include_router(calculations_router, prefix=config.API_VERSION_PREFIX)
app.include_router(upload_router, prefix=config.API_VERSION_PREFIX, dependencies=[])

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    """Lightweight health check for Render's probe"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
        "upload_dir": config.UPLOAD_DIR
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "AutoHVAC API V2 - Hardened Backend", 
        "status": "healthy",
        "max_file_size_mb": config.MAX_FILE_SIZE_MB
    }

# Make job_storage available to upload router
app.state.job_storage = job_storage

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)