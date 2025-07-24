"""
AutoHVAC V2 Backend
Clean FastAPI implementation following our planning documents
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import API routers
try:
    from api.climate import router as climate_router
    climate_router_loaded = True
except Exception as e:
    print(f"Failed to import climate router: {e}")
    climate_router = None
    climate_router_loaded = False

try:
    from api.calculations import router as calculations_router
    calculations_router_loaded = True
except Exception as e:
    print(f"Failed to import calculations router: {e}")
    calculations_router = None
    calculations_router_loaded = False

try:
    from api.blueprint import router as blueprint_router
    blueprint_router_loaded = True
except Exception as e:
    print(f"Failed to import blueprint router: {e}")
    blueprint_router = None
    blueprint_router_loaded = False

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
        "https://auto-hvac-oh1m0an31-hello-austinjdixons-projects.vercel.app",
        "https://auto-hvac-2nwdlrsjh-hello-austinjdixons-projects.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers  
if climate_router_loaded:
    app.include_router(climate_router)
    print("✅ Climate router included")
else:
    print("❌ Climate router not included")

if calculations_router_loaded:
    app.include_router(calculations_router)
    print("✅ Calculations router included")
else:
    print("❌ Calculations router not included")

if blueprint_router_loaded:
    app.include_router(blueprint_router)
    print("✅ Blueprint router included")
else:
    print("❌ Blueprint router not included")

# Add test data loading endpoint for development
try:
    from add_test_endpoint import test_router
    app.include_router(test_router)
    print("✅ Test router included")
except Exception as e:
    print(f"❌ Test router failed: {e}")

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