"""
Request models for the API
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class JobStatusEnum(str, Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"