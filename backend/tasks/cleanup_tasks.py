"""
Scheduled cleanup tasks for managing file storage
Runs periodically to clean up old files and maintain disk space
"""
import os
import time
import shutil
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

# Create Celery app with Redis as broker
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery('autohvac', broker=redis_url, backend=redis_url)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Load cleanup configuration from environment
STORAGE_CLEANUP_ENABLED = os.getenv("STORAGE_CLEANUP_ENABLED", "true").lower() == "true"
TEMP_RETENTION_HOURS = int(os.getenv("TEMP_RETENTION_HOURS", "6"))
UPLOAD_RETENTION_DAYS = int(os.getenv("UPLOAD_RETENTION_DAYS", "30"))
PROCESSED_RETENTION_DAYS = int(os.getenv("PROCESSED_RETENTION_DAYS", "90"))
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH", "/var/data")

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-temp-files': {
        'task': 'tasks.cleanup_tasks.cleanup_temp_files',
        'schedule': crontab(minute='0', hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-uploads': {
        'task': 'tasks.cleanup_tasks.cleanup_old_uploads',
        'schedule': crontab(minute='0', hour='2'),  # Daily at 2 AM
    },
    'cleanup-old-processed': {
        'task': 'tasks.cleanup_tasks.cleanup_old_processed',
        'schedule': crontab(minute='0', hour='3', day_of_week='1'),  # Weekly on Monday at 3 AM
    },
    'health-check': {
        'task': 'tasks.cleanup_tasks.health_check',
        'schedule': 300.0,  # Every 5 minutes
    }
}

def get_file_age_hours(file_path: str) -> float:
    """Get age of file in hours"""
    try:
        stat = os.stat(file_path)
        age = time.time() - stat.st_mtime
        return age / 3600  # Convert to hours
    except Exception as e:
        logger.error(f"Error getting file age for {file_path}: {e}")
        return 0

def get_file_age_days(file_path: str) -> float:
    """Get age of file in days"""
    return get_file_age_hours(file_path) / 24

@celery_app.task(
    acks_late=True,
    time_limit=600,  # 10 minutes max
    soft_time_limit=540  # 9 minutes soft limit
)
def cleanup_temp_files():
    """Clean up temporary files older than TEMP_RETENTION_HOURS"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    temp_dir = os.path.join(RENDER_DISK_PATH, "temp")
    if not os.path.exists(temp_dir):
        logger.warning(f"[CLEANUP] Temp directory does not exist: {temp_dir}")
        return {"status": "error", "reason": "temp directory not found"}
    
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting temp file cleanup (retention: {TEMP_RETENTION_HOURS} hours)")
    
    try:
        # Iterate through project directories in temp/
        for project_id in os.listdir(temp_dir):
            project_dir = os.path.join(temp_dir, project_id)
            
            if not os.path.isdir(project_dir):
                continue
            
            # Check directory age
            age_hours = get_file_age_hours(project_dir)
            if age_hours > TEMP_RETENTION_HOURS:
                try:
                    # Calculate size before deletion
                    dir_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(project_dir)
                        for filename in filenames
                    )
                    
                    # Remove the directory
                    shutil.rmtree(project_dir)
                    cleaned_count += 1
                    total_size_cleaned += dir_size
                    
                    logger.info(f"[CLEANUP] Removed temp directory: {project_id} "
                              f"(age: {age_hours:.1f}h, size: {dir_size/1024/1024:.2f}MB)")
                except Exception as e:
                    error_count += 1
                    logger.error(f"[CLEANUP] Failed to remove temp directory {project_id}: {e}")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during temp cleanup: {e}")
        return {"status": "error", "reason": str(e)}
    
    logger.info(f"[CLEANUP] Temp cleanup completed: {cleaned_count} directories removed, "
              f"{total_size_cleaned/1024/1024:.2f}MB freed, {error_count} errors")
    
    return {
        "status": "success",
        "cleaned_count": cleaned_count,
        "error_count": error_count,
        "total_size_mb": round(total_size_cleaned / 1024 / 1024, 2)
    }

@celery_app.task(
    acks_late=True,
    time_limit=600,
    soft_time_limit=540
)
def cleanup_old_uploads():
    """Clean up uploaded files older than UPLOAD_RETENTION_DAYS"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    upload_dir = os.path.join(RENDER_DISK_PATH, "uploads")
    if not os.path.exists(upload_dir):
        logger.warning(f"[CLEANUP] Upload directory does not exist: {upload_dir}")
        return {"status": "error", "reason": "upload directory not found"}
    
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting upload file cleanup (retention: {UPLOAD_RETENTION_DAYS} days)")
    
    try:
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            # Skip hidden files like .write_test
            if filename.startswith('.'):
                continue
            
            # Check file age
            age_days = get_file_age_days(file_path)
            if age_days > UPLOAD_RETENTION_DAYS:
                try:
                    file_size = os.path.getsize(file_path)
                    os.unlink(file_path)
                    cleaned_count += 1
                    total_size_cleaned += file_size
                    
                    logger.info(f"[CLEANUP] Removed old upload: {filename} "
                              f"(age: {age_days:.1f}d, size: {file_size/1024/1024:.2f}MB)")
                except Exception as e:
                    error_count += 1
                    logger.error(f"[CLEANUP] Failed to remove upload {filename}: {e}")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during upload cleanup: {e}")
        return {"status": "error", "reason": str(e)}
    
    logger.info(f"[CLEANUP] Upload cleanup completed: {cleaned_count} files removed, "
              f"{total_size_cleaned/1024/1024:.2f}MB freed, {error_count} errors")
    
    return {
        "status": "success",
        "cleaned_count": cleaned_count,
        "error_count": error_count,
        "total_size_mb": round(total_size_cleaned / 1024 / 1024, 2)
    }

@celery_app.task(
    acks_late=True,
    time_limit=600,
    soft_time_limit=540
)
def cleanup_old_processed():
    """Clean up processed files older than PROCESSED_RETENTION_DAYS"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    processed_dir = os.path.join(RENDER_DISK_PATH, "processed")
    if not os.path.exists(processed_dir):
        logger.warning(f"[CLEANUP] Processed directory does not exist: {processed_dir}")
        return {"status": "error", "reason": "processed directory not found"}
    
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting processed file cleanup (retention: {PROCESSED_RETENTION_DAYS} days)")
    
    try:
        # Iterate through project directories in processed/
        for project_id in os.listdir(processed_dir):
            project_dir = os.path.join(processed_dir, project_id)
            
            if not os.path.isdir(project_dir):
                continue
            
            # Check directory age (use oldest file in directory)
            oldest_age_days = 0
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    age_days = get_file_age_days(file_path)
                    oldest_age_days = max(oldest_age_days, age_days)
            
            if oldest_age_days > PROCESSED_RETENTION_DAYS:
                try:
                    # Calculate size before deletion
                    dir_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(project_dir)
                        for filename in filenames
                    )
                    
                    # Remove the directory
                    shutil.rmtree(project_dir)
                    cleaned_count += 1
                    total_size_cleaned += dir_size
                    
                    logger.info(f"[CLEANUP] Removed processed directory: {project_id} "
                              f"(age: {oldest_age_days:.1f}d, size: {dir_size/1024/1024:.2f}MB)")
                except Exception as e:
                    error_count += 1
                    logger.error(f"[CLEANUP] Failed to remove processed directory {project_id}: {e}")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during processed cleanup: {e}")
        return {"status": "error", "reason": str(e)}
    
    logger.info(f"[CLEANUP] Processed cleanup completed: {cleaned_count} directories removed, "
              f"{total_size_cleaned/1024/1024:.2f}MB freed, {error_count} errors")
    
    return {
        "status": "success",
        "cleaned_count": cleaned_count,
        "error_count": error_count,
        "total_size_mb": round(total_size_cleaned / 1024 / 1024, 2)
    }

# Manual cleanup function for immediate cleanup (useful for testing)
@celery_app.task
def cleanup_project_temp(project_id: str):
    """Immediately clean up temp files for a specific project"""
    temp_project_dir = os.path.join(RENDER_DISK_PATH, "temp", project_id)
    
    try:
        if os.path.exists(temp_project_dir):
            shutil.rmtree(temp_project_dir)
            logger.info(f"[CLEANUP] Manually removed temp directory for project {project_id}")
            return {"status": "success", "project_id": project_id}
        else:
            return {"status": "not_found", "project_id": project_id}
    except Exception as e:
        logger.error(f"[CLEANUP] Failed to manually cleanup project {project_id}: {e}")
        return {"status": "error", "project_id": project_id, "error": str(e)}

@celery_app.task
def health_check():
    """Simple health check task for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "storage_path": os.getenv("RENDER_DISK_PATH"),
        "cleanup_enabled": STORAGE_CLEANUP_ENABLED,
        "retention_config": {
            "temp_hours": TEMP_RETENTION_HOURS,
            "upload_days": UPLOAD_RETENTION_DAYS,
            "processed_days": PROCESSED_RETENTION_DAYS
        }
    }