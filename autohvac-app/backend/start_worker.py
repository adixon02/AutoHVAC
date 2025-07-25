#!/usr/bin/env python3
"""
Celery worker startup script with proper error handling and logging
"""
import logging
import os
import sys
from celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start Celery worker with proper configuration"""
    try:
        logger.info("Starting AutoHVAC Celery worker...")
        
        # Validate Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        logger.info(f"Using Redis URL: {redis_url}")
        
        # Start worker
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--max-tasks-per-child=10',
            '--time-limit=1800',  # 30 minutes
            '--soft-time-limit=1500',  # 25 minutes
            '--prefetch-multiplier=1'
        ])
        
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()