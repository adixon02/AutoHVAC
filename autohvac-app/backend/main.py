"""
AutoHVAC V2 Backend
Clean FastAPI implementation following our planning documents
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

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

app = FastAPI(
    title="AutoHVAC API V2",
    description="Professional HVAC load calculations and system recommendations",
    version="2.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001", 
        "https://autohvac.com",
        "https://auto-hvac.vercel.app",
        "https://auto-hvac-oh1m0an31-hello-austinjdixons-projects.vercel.app",
        "https://auto-hvac-2nwdlrsjh-hello-austinjdixons-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers  
app.include_router(climate_router)
app.include_router(calculations_router)
app.include_router(blueprint_router)

# Add test data loading endpoint for development (optional)
try:
    from add_test_endpoint import test_router
    app.include_router(test_router)
except ImportError as e:
    logger.warning(f"Test endpoint not available: {e}")

@app.get("/")
async def root():
    return {"message": "AutoHVAC API V2 - Clean rebuild", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "api": "healthy",
            "calculations": "healthy"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)