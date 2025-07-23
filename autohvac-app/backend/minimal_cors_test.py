#!/usr/bin/env python3
"""Absolutely minimal CORS test server to isolate the issue"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
import os

# Create the most basic FastAPI app possible
app = FastAPI(title="Minimal CORS Test")

# Add CORS - the ONLY middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Minimal CORS Test Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/blueprint/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None)
):
    """Ultra-simple upload endpoint with CORS"""
    print(f"✅ Received upload: {file.filename}")
    print(f"   zip_code: {zip_code}")
    print(f"   project_name: {project_name}")
    
    return {
        "status": "success",
        "job_id": "minimal-test-123",
        "filename": file.filename,
        "message": "CORS is working!"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting MINIMAL CORS test server on port {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )