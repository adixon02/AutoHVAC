"""
Health check endpoint for monitoring and load balancers
"""
from fastapi import APIRouter
from datetime import datetime
import time
import os

from ..models.responses import HealthResponse
from ..core import settings, get_logger

router = APIRouter()
logger = get_logger(__name__)

# Track startup time for uptime calculation
startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Fast health check endpoint for Render's load balancer.
    Returns 200 OK within 50ms as per requirements.
    """
    uptime = time.time() - startup_time
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        uptime_seconds=round(uptime, 2)
    )