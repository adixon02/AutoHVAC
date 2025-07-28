#!/usr/bin/env python3
"""
Initialize database schema using Alembic migrations
Run this script to create all tables in production
"""
import logging
import os
import sys
from pathlib import Path

# Get the backend directory path
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lock file to ensure migrations run only once per container
MIGRATION_LOCK_FILE = "/tmp/db_migrations_completed"

try:
    from alembic.config import Config
    from alembic import command
    from database import DATABASE_URL, sync_engine
except Exception as e:
    logger.exception(f"Failed to import required modules: {e}")
    sys.exit(1)

def run_migrations():
    """Run Alembic migrations to create database schema"""
    try:
        logger.info("🚀 Starting Alembic migrations...")
        logger.info(f"Database URL: {DATABASE_URL}")
        logger.info(f"Base directory: {BASE_DIR}")
        
        # Create Alembic configuration
        alembic_ini_path = BASE_DIR / "alembic.ini"
        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")
            
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        # Run migrations to head
        logger.info("Running migrations to head...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("✅ Database migrations completed successfully!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Failed to run migrations: {e}")
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

def should_run_migrations():
    """Check if migrations should run (not already completed)"""
    return not os.path.exists(MIGRATION_LOCK_FILE)

def mark_migrations_completed():
    """Mark migrations as completed"""
    try:
        with open(MIGRATION_LOCK_FILE, 'w') as f:
            f.write("migrations_completed")
        logger.info(f"✅ Marked migrations as completed: {MIGRATION_LOCK_FILE}")
    except Exception as e:
        logger.warning(f"Failed to create lock file: {e}")

def initialize_database():
    """Initialize database with migrations if needed"""
    try:
        if not should_run_migrations():
            logger.info("📋 Database migrations already completed, skipping...")
            return True
            
        logger.info("🚀 Starting database initialization...")
        
        if not check_database_connection():
            logger.error("❌ Database connection failed")
            return False
        
        if not run_migrations():
            logger.error("❌ Database migrations failed")
            return False
        
        mark_migrations_completed()
        logger.info("🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)