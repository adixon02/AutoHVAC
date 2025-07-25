"""
Celery worker configuration for background task processing
"""
from celery import Celery
from ..core import settings, setup_logging, get_logger

# Setup logging for worker
setup_logging()
logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "autohvac_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.blueprint_processing"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.job_timeout_seconds,
    task_soft_time_limit=settings.job_timeout_seconds - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

if __name__ == "__main__":
    celery_app.start()