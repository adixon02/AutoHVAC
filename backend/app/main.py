import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Import routes
from app.routes import blueprint, job, leads, auth, billing, admin

# Import database initialization
from app.database import create_db_and_tables

# Set OpenAI API key from environment
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Warning: OPENAI_API_KEY not set in environment")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoHVAC API V3", 
    version="3.0.0",
    description="HVAC Load Calculation API powered by Pipeline V3"
)

# CORS configuration
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://autohvac-frontend.onrender.com", 
    "https://autohvac.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🌐 REQUEST: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"🌐 RESPONSE: {response.status_code}")
    return response

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and perform startup tasks"""
    logger.info("🗄️  Initializing database tables...")
    create_db_and_tables()
    logger.info("✅ Database tables initialized")

# Include API routes
app.include_router(blueprint.router, prefix="/api/v1/blueprint")
app.include_router(job.router, prefix="/api/v1/job")
app.include_router(leads.router)  # Already has /api/leads prefix
app.include_router(auth.router)  # Already has /auth prefix
app.include_router(billing.router, prefix="/api/v1/billing")  # Billing routes
app.include_router(admin.router, prefix="/admin")  # Admin dashboard

@app.get("/")
async def root():
    return {"message": "AutoHVAC API V3 is running", "pipeline": "v3"}

@app.get("/health")
async def health():
    return {"status": "healthy", "pipeline": "v3"}

@app.get("/healthz")
async def healthz():
    """Health check endpoint for Render"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "autohvac-api-v3",
        "pipeline": "v3"
    }

# Debug endpoint to show routes
@app.get("/api/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": sorted(routes, key=lambda x: x["path"])}