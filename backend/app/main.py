from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from routes import blueprint, job, billing, auth, jobs
from app.middleware.error_handler import traceback_exception_handler, CORSMiddleware as CustomCORSMiddleware
from app.config import DEBUG, DEV_VERIFIED_EMAILS

# Debug startup logging
print("▶ DEBUG =", DEBUG, "  DEV_VERIFIED_EMAILS =", DEV_VERIFIED_EMAILS)

app = FastAPI(title="AutoHVAC API", version="1.0.0")

DEV_ORIGIN = "http://localhost:3000"

# Add custom CORS middleware that handles errors properly
app.add_middleware(CustomCORSMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DEV_ORIGIN],   # no '*'
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,      # safe with explicit origin
)

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