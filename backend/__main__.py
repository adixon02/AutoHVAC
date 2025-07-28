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

def run_migrations():
    """Run database migrations with fallback to direct table creation"""
    # First try Alembic directly
    try:
        logger.info("🔧 Running Alembic migrations directly...")
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            logger.info("✅ Alembic migrations completed successfully")
            logger.info(f"Migration output: {result.stdout}")
            return True
        else:
            logger.warning(f"⚠️ Alembic failed with return code {result.returncode}")
            logger.warning(f"Error: {result.stderr}")
    except Exception as e:
        logger.exception(f"❌ Alembic subprocess error: {e}")
    
    # Fallback to init_db
    try:
        logger.info("🔧 Trying init_db approach...")
        from init_db import initialize_database
        
        if initialize_database():
            logger.info("✅ Database migrations completed via init_db")
            return True
        else:
            logger.warning("⚠️ init_db migrations failed, trying direct table creation...")
            return create_tables_directly()
            
    except Exception as e:
        logger.exception(f"❌ init_db error: {e}")
        logger.warning("⚠️ Trying direct table creation as fallback...")
        return create_tables_directly()

def create_tables_directly():
    """Create tables directly using SQLModel as fallback"""
    try:
        logger.info("🔧 Creating tables directly with SQLModel...")
        
        from sqlmodel import SQLModel
        from database import sync_engine
        from models.db_models import User, EmailToken, Project, RateLimit
        
        SQLModel.metadata.create_all(sync_engine)
        logger.info("✅ Tables created directly with SQLModel!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Direct table creation failed: {e}")
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
    
    # Run migrations first
    if not run_migrations():
        logger.error("❌ Cannot start server - database migration failed")
        sys.exit(1)
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()