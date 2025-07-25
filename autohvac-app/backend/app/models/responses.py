"""
Response models for the API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .requests import JobStatusEnum


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    request_id: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    uptime_seconds: Optional[float] = None


class UploadResponse(BaseModel):
    """File upload response"""
    job_id: str
    status: JobStatusEnum = JobStatusEnum.QUEUED
    message: str = "File uploaded successfully and queued for processing"
    file_size_bytes: Optional[int] = None
    filename: Optional[str] = None


class JobResponse(BaseModel):
    """Job status and result response"""
    job_id: str
    status: JobStatusEnum
    created_at: datetime
    updated_at: datetime
    progress_percent: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class ClimateResponse(BaseModel):
    """Climate data response"""
    zip_code: str
    climate_zone: Optional[str] = None
    heating_design_temp: Optional[float] = None
    cooling_design_temp: Optional[float] = None
    data_source: Optional[str] = None
    message: Optional[str] = None