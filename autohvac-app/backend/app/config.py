"""
Configuration for AutoHVAC Backend
Environment variables and settings
"""
import os
from typing import List
import re

class Config:
    # API Configuration
    API_VERSION_PREFIX: str = os.getenv("API_VERSION_PREFIX", "/api/v2")
    
    # File Upload Limits
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "150"))
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://auto-hvac.vercel.app"
    ]
    
    # Regex pattern for Vercel preview URLs
    CORS_ORIGIN_REGEX: str = r"^https://auto-hvac.*\.vercel\.app$"
    
    # Upload Configuration
    UPLOAD_DIR: str = "/tmp/uploads"
    CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks
    
    # Background Task Configuration
    JOB_TIMEOUT_SECONDS: int = 600  # 10 minutes
    POLL_INTERVAL_SECONDS: int = 2
    
    # Redis Configuration (if using Celery)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    @classmethod
    def is_allowed_origin(cls, origin: str) -> bool:
        """Check if origin is allowed via static list or regex pattern"""
        if origin in cls.CORS_ORIGINS:
            return True
        
        if re.match(cls.CORS_ORIGIN_REGEX, origin):
            return True
            
        return False

config = Config()