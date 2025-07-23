#!/usr/bin/env python3
"""Minimal test to check if basic FastAPI works"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="AutoHVAC Test")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AutoHVAC Backend is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting minimal server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)