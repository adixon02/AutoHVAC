from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from typing import List, Dict, Any
import os
from pathlib import Path

from api.blueprint import router as blueprint_router
from api.calculations import router as calculations_router
from api.export import router as export_router

app = FastAPI(
    title="AutoHVAC Backend API",
    description="AI-powered HVAC system design and blueprint processing",
    version="0.1.0"
)

# Configure CORS for Next.js frontend - Allow all origins for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins to debug
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(blueprint_router, prefix="/api/blueprint", tags=["blueprint"])
app.include_router(calculations_router, prefix="/api/calculations", tags=["calculations"])
app.include_router(export_router, prefix="/api/export", tags=["export"])

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "AutoHVAC Backend API",
        "version": "0.1.0",
        "endpoints": {
            "blueprint": "/api/blueprint",
            "calculations": "/api/calculations",
            "export": "/api/export",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "autohvac-backend"}

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)