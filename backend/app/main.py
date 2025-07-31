from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from routes import blueprint, job, billing, auth, jobs, admin
from app.middleware.error_handler import traceback_exception_handler, CORSMiddleware as CustomCORSMiddleware
from app.config import DEBUG, DEV_VERIFIED_EMAILS
from services.database_rate_limiter import database_rate_limiter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
import logging
import asyncio
import os
import redis

# Import stripe_config early to ensure Stripe is initialized at startup
import core.stripe_config

# Debug startup logging
print("▶ DEBUG =", DEBUG, "  DEV_VERIFIED_EMAILS =", DEV_VERIFIED_EMAILS)

app = FastAPI(title="AutoHVAC API", version="1.0.0")
logger = logging.getLogger(__name__)

# Upload size limiter middleware
class UploadSizeLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_size=100*1024*1024):  # 100MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_size:
                return JSONResponse(
                    {"error": f"File too large. Maximum size is {self.max_size // (1024*1024)}MB"},
                    status_code=413
                )
        return await call_next(request)

# Add upload size limiter (100MB max)
app.add_middleware(UploadSizeLimiter, max_size=100*1024*1024)

allowed_origins = [
    "http://localhost:3000",
    "https://autohvac-frontend.onrender.com",
    "https://autohvac.ai",
]

# Add custom CORS middleware that handles errors properly
app.add_middleware(CustomCORSMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,      # safe with explicit origin
)

# Add request logging middleware to debug routing issues
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🌐 REQUEST: {request.method} {request.url} from {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"🌐 RESPONSE: {response.status_code} for {request.method} {request.url.path}")
    return response

app.add_exception_handler(Exception, traceback_exception_handler)

app.include_router(blueprint.router, prefix="/api/v1/blueprint")
app.include_router(job.router, prefix="/api/v1/job")
app.include_router(billing.router, prefix="/api/v1/billing")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(jobs.router, prefix="/api/v1/jobs")
app.include_router(admin.router, prefix="/api/v1/admin")

# Background task for periodic cleanup
cleanup_task = None

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting AutoHVAC API...")
    
    # Log S3 configuration
    s3_bucket = os.getenv("S3_BUCKET")
    aws_region = os.getenv("AWS_REGION")
    logger.info(f"[STARTUP] S3_BUCKET: {s3_bucket}")
    logger.info(f"[STARTUP] AWS_REGION: {aws_region}")
    
    # Check AWS credentials are configured
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.info("[STARTUP] AWS credentials are configured")
        
        # Initialize S3 storage service to verify connection
        try:
            from services.s3_storage import storage_service
            logger.info(f"[STARTUP] S3 storage service initialized successfully")
            logger.info(f"[STARTUP] Using S3 bucket: {storage_service.bucket_name}")
        except Exception as e:
            logger.error(f"[STARTUP] Failed to initialize S3 storage: {e}")
    else:
        logger.warning("[STARTUP] AWS credentials not configured - S3 storage will fail")
    
    # DON'T access database here - it blocks port binding
    
    # Start periodic cleanup task WITHOUT immediate execution
    async def periodic_cleanup():
        await asyncio.sleep(60)  # Wait 60s before first run
        while True:
            try:
                cleaned = await database_rate_limiter.cleanup_stuck_jobs(older_than_minutes=60)
                if cleaned > 0:
                    logger.info(f"Periodic cleanup: cleaned {cleaned} stuck jobs")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(3600)  # Run every hour
    
    global cleanup_task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Started periodic job cleanup task")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down AutoHVAC API...")
    
    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

@app.get("/")
async def root():
    return {"message": "AutoHVAC API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/routes")
async def list_routes():
    """List all registered routes for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": sorted(routes, key=lambda x: x["path"])}

@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_async_session)):
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "autohvac-api",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        result = await session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Celery worker status (via Redis)
    try:
        from celery import Celery
        celery_app = Celery('autohvac', broker=os.getenv('REDIS_URL'))
        stats = celery_app.control.inspect().stats()
        if stats:
            health_status["checks"]["celery_workers"] = {
                "status": "healthy",
                "workers": len(stats)
            }
        else:
            health_status["checks"]["celery_workers"] = {"status": "unhealthy", "error": "No workers found"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["celery_workers"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "ok" else 503
    return JSONResponse(content=health_status, status_code=status_code)

# Catch-all route to debug unmatched requests
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def catch_all(request: Request, path: str):
    logger.warning(f"🚨 CATCH-ALL: {request.method} /{path} from {request.client.host if request.client else 'unknown'}")
    return {
        "error": "Route not found", 
        "path": path, 
        "method": request.method,
        "available_routes": [
            "POST /api/v1/blueprint/upload",
            "GET /api/v1/job/{job_id}",
            "POST /api/v1/billing/subscribe",
            "POST /api/v1/billing/webhook",
            "GET /healthz"
        ]
    }