from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from routes import blueprint, job, billing, auth, jobs
from app.middleware.error_handler import traceback_exception_handler, CORSMiddleware as CustomCORSMiddleware
from app.config import DEBUG, DEV_VERIFIED_EMAILS
import logging

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
app.include_router(billing.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(jobs.router, prefix="/api/v1/jobs")

@app.get("/")
async def root():
    return {"message": "AutoHVAC API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/healthz")
async def healthz():
    """Lightweight health check endpoint - no DB or external dependencies"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "autohvac-api"
    }

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
            "GET /healthz"
        ]
    }