"""
Configuration management using Pydantic Settings
All configuration from environment variables
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App settings
    app_name: str = Field(default="AutoHVAC API", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001", 
            "https://auto-hvac.vercel.app"
        ],
        env="ALLOWED_ORIGINS"
    )
    
    # File upload settings
    max_file_size_mb: int = Field(default=150, env="MAX_FILE_SIZE_MB")
    upload_chunk_size_mb: int = Field(default=1, env="UPLOAD_CHUNK_SIZE_MB")
    temp_dir: str = Field(default="/tmp", env="TEMP_DIR")
    
    # Redis settings for job storage
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Background task settings
    job_timeout_seconds: int = Field(default=300, env="JOB_TIMEOUT_SECONDS")
    
    # OpenAI settings
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()