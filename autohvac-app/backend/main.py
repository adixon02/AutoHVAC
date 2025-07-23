from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from typing import List, Dict, Any
import os
from pathlib import Path

# Import our enhanced core systems
from core.logging_config import setup_logging, get_logger
from core.error_handling import setup_error_handlers
from core.middleware import setup_middleware

from api.blueprint_v2 import router as blueprint_router_v2
from api.blueprint import router as blueprint_router_v1  # Keep v1 for backward compatibility
from api.calculations import router as calculations_router
from api.export import router as export_router
from api.climate import router as climate_router

# Initialize logging first
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

app = FastAPI(
    title="AutoHVAC Backend API",
    description="AI-powered HVAC system design and blueprint processing with professional-grade reliability",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup comprehensive error handling
setup_error_handlers(app)

# Setup middleware stack
setup_middleware(app)

# Configure CORS for Next.js frontend - Allow all origins for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins to debug
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - v2 for new optimized endpoints, v1 for backward compatibility
app.include_router(blueprint_router_v2, prefix="/api/v2/blueprint", tags=["blueprint-v2"])
app.include_router(blueprint_router_v1, prefix="/api/blueprint", tags=["blueprint-v1"])
app.include_router(calculations_router, prefix="/api/calculations", tags=["calculations"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
app.include_router(climate_router, prefix="/api/climate", tags=["climate"])

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "AutoHVAC Backend API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "blueprint_v2": "/api/v2/blueprint",
            "blueprint_v1": "/api/blueprint", 
            "calculations": "/api/calculations",
            "export": "/api/export",
            "climate": "/api/climate",
            "docs": "/docs",
            "health": "/health"
        },
        "features": [
            "Professional HVAC blueprint analysis",
            "Climate zone data with intelligent caching",
            "Comprehensive error handling and logging",
            "Rate limiting and security headers",
            "Request tracking and performance monitoring"
        ]
    }

@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint accessed")
    return {
        "status": "healthy", 
        "service": "autohvac-backend",
        "version": "2.0.0",
        "timestamp": "2024-01-01T00:00:00Z"  # This would be dynamic in production
    }

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AutoHVAC Backend API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)