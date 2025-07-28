#!/usr/bin/env python3
"""
Initialize database schema using Alembic migrations
Run this script to create all tables in production
"""
import asyncio
import logging
import os
import subprocess
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from alembic.config import Config
    from alembic import command
    from database import sync_engine, DATABASE_URL
except Exception as e:
    logging.error(f"Failed to import required modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run Alembic migrations to create database schema"""
    try:
        logger.info(f"Initializing database schema...")
        logger.info(f"Database URL: {DATABASE_URL}")
        
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        # Run migrations
        logger.info("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("✅ Database schema initialized successfully!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Failed to initialize database: {e}")
        return False

def check_database_connection():
    """Test database connection"""
    try:
        logger.info("Testing database connection...")
        with sync_engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Database connection successful!")
            return True
    except Exception as e:
        logger.exception(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting database initialization...")
    
    if not check_database_connection():
        sys.exit(1)
    
    if not run_migrations():
        sys.exit(1)
    
    logger.info("🎉 Database initialization completed!")