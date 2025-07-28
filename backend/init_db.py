#!/usr/bin/env python3
"""
Initialize database schema by creating tables directly
Run this script to create all tables in production
"""
import asyncio
import logging
import os
import subprocess
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sqlmodel import SQLModel
    from database import sync_engine, DATABASE_URL
    # Import all models to register them with SQLModel
    from models.db_models import User, EmailToken, Project, RateLimit
except Exception as e:
    logger.exception(f"Failed to import required modules: {e}")
    sys.exit(1)

def create_tables():
    """Create all tables using SQLModel metadata"""
    try:
        logger.info(f"Creating database tables...")
        logger.info(f"Database URL: {DATABASE_URL}")
        
        # Create all tables
        logger.info("Creating tables using SQLModel.metadata.create_all...")
        SQLModel.metadata.create_all(sync_engine)
        
        logger.info("✅ Database tables created successfully!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Failed to create tables: {e}")
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
    
    if not create_tables():
        sys.exit(1)
    
    logger.info("🎉 Database initialization completed!")