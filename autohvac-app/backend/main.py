"""
AutoHVAC V2 Backend
Clean FastAPI implementation following our planning documents
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import signal
import asyncio
from contextlib import asynccontextmanager
import threading
import time

# Import API routers
from api.climate import router as climate_router
from api.calculations import router as calculations_router
from api.blueprint import router as blueprint_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state for graceful shutdown
shutdown_event = asyncio.Event()
active_uploads = set()
upload_lock = threading.Lock()

def add_active_upload(job_id: str):
    """Track an active upload to prevent shutdown"""
    with upload_lock:
        active_uploads.add(job_id)
        logger.info(f"Added active upload: {job_id}, total active: {len(active_uploads)}")

def remove_active_upload(job_id: str):
    """Remove completed upload from tracking"""
    with upload_lock:
        active_uploads.discard(job_id)
        logger.info(f"Removed active upload: {job_id}, total active: {len(active_uploads)}")

def get_active_upload_count() -> int:
    """Get current number of active uploads"""
    with upload_lock:
        return len(active_uploads)

async def wait_for_uploads_to_complete(max_wait_seconds: int = 300):
    """Wait for all active uploads to complete before shutdown"""
    start_time = time.time()
    while get_active_upload_count() > 0 and (time.time() - start_time) < max_wait_seconds:
        logger.info(f"Waiting for {get_active_upload_count()} active uploads to complete...")
        await asyncio.sleep(5)
    
    remaining = get_active_upload_count()
    if remaining > 0:
        logger.warning(f"Shutdown timeout reached, {remaining} uploads still active")
    else:
        logger.info("All uploads completed, safe to shutdown")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for graceful startup/shutdown"""
    logger.info("AutoHVAC API starting up...")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    yield
    
    # Graceful shutdown
    logger.info("AutoHVAC API shutting down...")
    await wait_for_uploads_to_complete()
    logger.info("AutoHVAC API shutdown complete")

app = FastAPI(
    title="AutoHVAC API V2",
    description="Professional HVAC load calculations and system recommendations",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001", 
        "https://auto-hvac.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    
    # Create JSON response with CORS headers
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )
    
    # Add CORS headers manually for error responses
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:3000", 
        "http://localhost:3001", 
        "https://auto-hvac.vercel.app"
    ]
    
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# Include API routers with v2 prefix
app.include_router(climate_router, prefix="/api/v2")
app.include_router(calculations_router, prefix="/api/v2")
app.include_router(blueprint_router, prefix="/api/v2")

@app.get("/")
async def root():
    return {"message": "AutoHVAC API V2 - Clean rebuild", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Immediate health check - returns 200 immediately for load balancer"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)