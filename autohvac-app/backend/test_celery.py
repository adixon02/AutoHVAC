#!/usr/bin/env python3
"""
Test script to verify Celery setup works correctly
"""
import time
import logging
from celery_app import celery_app, health_check_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_celery_connection():
    """Test Celery connection and basic task execution"""
    try:
        logger.info("Testing Celery connection...")
        
        # Test health check task
        result = health_check_task.delay()
        logger.info(f"Health check task submitted: {result.id}")
        
        # Wait for result (with timeout)
        try:
            response = result.get(timeout=10)
            logger.info(f"Health check result: {response}")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Celery connection test failed: {e}")
        return False

if __name__ == '__main__':
    if test_celery_connection():
        logger.info("✅ Celery setup is working correctly!")
    else:
        logger.error("❌ Celery setup has issues")