#!/usr/bin/env python3
"""
Simple script to test database connection and basic job service functionality
"""
import asyncio
import logging
from services.job_service import job_service
from database import get_async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_db_connection():
    """Test basic database connection"""
    try:
        logger.info("Testing database connection...")
        async with get_async_session() as session:
            logger.info("✅ Database session created successfully")
            
            # Test getting a project (should return None for fake ID)
            project = await job_service.get_project("test-job-id", session)
            logger.info(f"✅ get_project returned: {project}")
            
            # Test getting a real project ID if any exist
            projects = await job_service.get_projects_by_status("pending", limit=1, session=session)
            logger.info(f"✅ Found {len(projects)} pending projects")
            
            if projects:
                project = projects[0]
                logger.info(f"✅ Sample project: {project.id}, status={project.status.value}")
            
            logger.info("✅ All database tests passed!")
            
    except Exception as e:
        logger.exception(f"❌ Database test failed: {e}")
        return False
    return True

if __name__ == "__main__":
    asyncio.run(test_db_connection())