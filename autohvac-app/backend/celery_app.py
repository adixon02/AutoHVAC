"""
Celery application setup for background task processing
"""
from celery import Celery
import os
import logging

logger = logging.getLogger(__name__)

# Redis configuration from environment or default to localhost
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'autohvac',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks.blueprint_processing']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    result_expires=3600,  # Results expire after 1 hour
)

# Health check task
@celery_app.task(bind=True)
def health_check_task(self):
    """Simple health check task"""
    return {"status": "healthy", "worker_id": self.request.id}

if __name__ == '__main__':
    celery_app.start()