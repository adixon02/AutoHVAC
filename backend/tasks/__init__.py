"""
Celery tasks module for AutoHVAC
"""
from celery import Celery
import os

# Create the main Celery app instance
app = Celery(
    'autohvac',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=[
        'tasks.calculate_hvac_loads',
        'tasks.cleanup_tasks'
    ]
)

# Import cleanup_tasks to get its beat schedule
from . import cleanup_tasks

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Import beat schedule from cleanup_tasks
    beat_schedule=cleanup_tasks.celery_app.conf.beat_schedule
)

# Make the app available at module level
celery = app