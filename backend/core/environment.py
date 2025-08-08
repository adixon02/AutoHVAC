"""Environment configuration management for AutoHVAC.

This module handles loading environment variables from .env files
with proper priority handling for local development vs production.

File Priority (highest to lowest):
1. .env.local (local secrets, gitignored)
2. .env (base configuration, committed)
3. Environment variables set by hosting platform
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

def load_environment(env_dir: Optional[Union[str, Path]] = None) -> None:
    """Load environment variables from .env files.
    
    Args:
        env_dir: Directory containing .env files. Defaults to current directory.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv not installed. Environment files won't be loaded.")
        return
    
    if env_dir is None:
        env_dir = Path.cwd()
    else:
        env_dir = Path(env_dir)
    
    # Load files in reverse priority order (last loaded wins)
    env_files = [
        env_dir / ".env",          # Base configuration
        env_dir / ".env.local",    # Local overrides (secrets)
    ]
    
    loaded_files = []
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            loaded_files.append(env_file.name)
            logger.debug(f"Loaded environment from {env_file}")
    
    if loaded_files:
        logger.info(f"Environment loaded from: {', '.join(loaded_files)}")
    else:
        logger.warning("No .env files found")

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set or invalid
        
    Returns:
        Boolean value
    """
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set or invalid
        
    Returns:
        Integer value
    """
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid integer value for {key}, using default: {default}")
        return default

def get_env_list(key: str, separator: str = ",", default: Optional[list] = None) -> list:
    """Get list from environment variable.
    
    Args:
        key: Environment variable name
        separator: List item separator
        default: Default value if not set
        
    Returns:
        List of strings
    """
    if default is None:
        default = []
    
    value = os.getenv(key, "")
    if not value.strip():
        return default
    
    return [item.strip() for item in value.split(separator) if item.strip()]

def validate_required_env_vars(required_vars: list[str]) -> list[str]:
    """Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        List of missing variables
    """
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() in ("", "your-api-key-here", "placeholder"):
            missing.append(var)
    
    return missing

def get_database_url() -> str:
    """Get database URL with fallback for development."""
    return os.getenv("DATABASE_URL", "sqlite:///./autohvac.db")

def get_redis_url() -> str:
    """Get Redis URL with fallback for development."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

def is_production() -> bool:
    """Check if running in production environment."""
    env = os.getenv("ENV", "development").lower()
    database_url = get_database_url()
    return env == "production" or "render.com" in database_url

def is_development() -> bool:
    """Check if running in development environment."""
    return not is_production()

def get_stripe_mode() -> str:
    """Get Stripe mode (test/live)."""
    return os.getenv("STRIPE_MODE", "test").lower()

# Load environment on import
load_environment()