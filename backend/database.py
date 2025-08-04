import os
import time
import asyncio
import logging
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Database URL with fallback to sqlite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autohvac.db")

# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Enhanced database configuration for production stability
def get_database_config():
    """Get database configuration with SSL and connection pooling settings"""
    is_production = os.getenv("ENV") == "production" or "render.com" in DATABASE_URL
    is_postgres = DATABASE_URL.startswith(("postgres://", "postgresql://"))
    
    base_config = {
        "echo": False,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 3600,  # Recycle connections every hour
        "pool_pre_ping": True,  # Validate connections before use
    }
    
    if is_postgres and is_production:
        # Production PostgreSQL with SSL settings
        base_config.update({
            "connect_args": {
                "sslmode": "require",
                "application_name": "autohvac_backend"
            }
        })
        logger.info("Database: Production PostgreSQL with SSL configured")
    elif is_postgres:
        # Development PostgreSQL
        base_config.update({
            "connect_args": {
                "application_name": "autohvac_dev"
            }
        })
        logger.info("Database: Development PostgreSQL configured")
    else:
        # SQLite for development
        base_config.update({
            "pool_size": 1,
            "max_overflow": 0,
            "connect_args": {"check_same_thread": False}
        })
        logger.info("Database: SQLite configured")
    
    return base_config

# Create sync engine for migrations
sync_engine = create_engine(DATABASE_URL, **get_database_config())

# Create async engine for the application
async_database_url = DATABASE_URL
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif async_database_url.startswith("sqlite://"):
    async_database_url = async_database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Configure async engine with retry logic
async_config = get_database_config().copy()

# Async engines need different connect_args format for PostgreSQL
if async_database_url.startswith("postgresql+asyncpg://"):
    is_production = os.getenv("ENV") == "production" or "render.com" in DATABASE_URL
    async_config["connect_args"] = {
        "ssl": "require" if is_production else "prefer",
        "server_settings": {
            "application_name": "autohvac_async",
        }
    }

async_engine = create_async_engine(async_database_url, **async_config)

# Create session makers
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync session for Celery workers
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)

def create_db_and_tables():
    """Create database tables (used in migrations)"""
    SQLModel.metadata.create_all(sync_engine)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as session:
                yield session
                return
        except (OperationalError, DisconnectionError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Unexpected database error: {str(e)}")
            raise

def get_sync_session():
    """Get sync database session with retry logic (for migrations and Celery)"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with Session(sync_engine) as session:
                yield session
                return
        except (OperationalError, DisconnectionError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Unexpected database error: {str(e)}")
            raise