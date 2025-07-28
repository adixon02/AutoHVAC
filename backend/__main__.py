#!/usr/bin/env python3
"""
Main entry point for the AutoHVAC backend
Runs database migrations first, then starts the server
"""
import logging
import os
import sys
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_progress_columns_exist():
    """Self-healing schema: ensure progress columns exist, add them if missing"""
    try:
        logger.info("🔍 Checking database schema for progress tracking columns...")
        
        from sqlalchemy import create_engine, inspect, text
        from database import DATABASE_URL
        
        # Create engine for schema inspection
        engine = create_engine(DATABASE_URL, echo=False)
        inspector = inspect(engine)
        
        # Check if projects table exists
        tables = inspector.get_table_names()
        if 'projects' not in tables:
            logger.warning("⚠️ Projects table doesn't exist - will be created by SQLModel")
            return True
            
        # Get current columns
        columns = inspector.get_columns('projects')
        column_names = [col['name'] for col in columns]
        
        logger.info(f"📊 Current projects table columns: {column_names}")
        
        # Check and add missing columns
        missing_columns = []
        
        if 'progress_percent' not in column_names:
            missing_columns.append('progress_percent')
            logger.info("🔧 Adding missing progress_percent column...")
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0
                """))
                conn.commit()
            
        if 'current_stage' not in column_names:
            missing_columns.append('current_stage')
            logger.info("🔧 Adding missing current_stage column...")
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN current_stage VARCHAR(64) NOT NULL DEFAULT 'initializing'
                """))
                conn.commit()
        
        if missing_columns:
            logger.info(f"✅ Successfully added missing columns: {missing_columns}")
        else:
            logger.info("✅ All required columns already exist")
            
        return True
        
    except Exception as e:
        logger.exception(f"❌ Schema validation/fix failed: {e}")
        return False

def run_migrations():
    """Run database schema validation and migration with multiple fallbacks"""
    
    # Step 1: Always ensure critical columns exist (self-healing)
    logger.info("🏥 Running self-healing schema check...")
    if not ensure_progress_columns_exist():
        logger.error("❌ Critical: Could not ensure required columns exist")
        return False
    
    # Step 2: Try Alembic if possible (optional)
    try:
        logger.info("🔧 Attempting Alembic migrations (optional)...")
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True, cwd=Path(__file__).parent, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ Alembic migrations completed successfully")
        else:
            logger.warning("⚠️ Alembic failed, but continuing with self-healed schema")
            
    except Exception as e:
        logger.warning(f"⚠️ Alembic unavailable, but schema is self-healed: {e}")
    
    # Step 3: Fallback to direct table creation if needed
    try:
        logger.info("🔧 Ensuring all tables exist...")
        from sqlmodel import SQLModel
        from database import sync_engine
        from models.db_models import User, EmailToken, Project, RateLimit
        
        SQLModel.metadata.create_all(sync_engine)
        logger.info("✅ All tables created/verified")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Final table creation failed: {e}")
        return False


def start_server():
    """Start the uvicorn server"""
    try:
        logger.info("🚀 Starting AutoHVAC API server...")
        
        # Get port from environment (Render sets this)
        port = os.getenv("PORT", "8000")
        
        # Import here to avoid import issues during migration
        import uvicorn
        from app.main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(port),
            log_level="info"
        )
        
    except Exception as e:
        logger.exception(f"❌ Server startup failed: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    logger.info("🎯 AutoHVAC Backend Starting...")
    logger.info("🔄 Running alembic upgrade head before starting server...")
    
    # Run migrations first - this is CRITICAL for production
    if not run_migrations():
        logger.error("❌ Cannot start server - database migration failed")
        logger.error("❌ This usually means the database schema is outdated")
        sys.exit(1)
    
    logger.info("✅ Database migrations completed - starting server")
    # Start the server
    start_server()

if __name__ == "__main__":
    main()