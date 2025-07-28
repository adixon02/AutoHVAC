import os
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

# Database URL with fallback to sqlite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autohvac.db")

# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create sync engine for migrations
sync_engine = create_engine(DATABASE_URL, echo=False)

# Create async engine for the application
async_database_url = DATABASE_URL
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif async_database_url.startswith("sqlite://"):
    async_database_url = async_database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

async_engine = create_async_engine(
    async_database_url, 
    echo=False,
    pool_size=5,
    max_overflow=10
)

# Create session makers
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

def create_db_and_tables():
    """Create database tables (used in migrations)"""
    SQLModel.metadata.create_all(sync_engine)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        yield session

def get_sync_session():
    """Get sync database session (for migrations)"""
    with Session(sync_engine) as session:
        yield session