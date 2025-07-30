"""
Automated cleanup tasks for old files and database records
"""
import os
import time
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab
import logging
from typing import List, Tuple

from services.job_service import job_service
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

celery_app = Celery(
    'autohvac',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configuration
DEFAULT_GRACE_PERIOD_DAYS = 7
MAX_FILES_PER_RUN = 100  # Limit to prevent overwhelming the system


@celery_app.task(
    acks_late=True,
    time_limit=600,  # 10 minutes max
    soft_time_limit=540  # 9 minutes soft limit
)
def cleanup_old_files(grace_period_days: int = None) -> dict:
    """
    Clean up old PDF files from storage and their associated database records
    
    Args:
        grace_period_days: Number of days to keep files (default: from env or 7)
        
    Returns:
        Dict with cleanup statistics
    """
    if grace_period_days is None:
        grace_period_days = int(os.getenv('FILE_CLEANUP_GRACE_DAYS', DEFAULT_GRACE_PERIOD_DAYS))
    
    logger.info(f"[CLEANUP] Starting cleanup task with {grace_period_days} day grace period")
    
    # Get storage path from environment
    storage_path = os.getenv("RENDER_DISK_PATH")
    if not storage_path:
        logger.error("[CLEANUP] RENDER_DISK_PATH not set, skipping cleanup")
        return {"error": "RENDER_DISK_PATH not set"}
    
    logger.info(f"[CLEANUP] Storage path: {storage_path}")
    
    # Track statistics
    stats = {
        "files_checked": 0,
        "files_deleted": 0,
        "files_failed": 0,
        "bytes_freed": 0,
        "db_records_cleaned": 0,
        "errors": []
    }
    
    try:
        # List all PDF files in storage
        if not os.path.exists(storage_path):
            logger.error(f"[CLEANUP] Storage path does not exist: {storage_path}")
            return {"error": f"Storage path does not exist: {storage_path}"}
        
        all_files = os.listdir(storage_path)
        pdf_files = [f for f in all_files if f.endswith('.pdf')]
        
        logger.info(f"[CLEANUP] Found {len(pdf_files)} PDF files to check")
        
        # Calculate cutoff time
        cutoff_time = time.time() - (grace_period_days * 24 * 60 * 60)
        cutoff_datetime = datetime.fromtimestamp(cutoff_time)
        
        logger.info(f"[CLEANUP] Will delete files older than {cutoff_datetime}")
        
        # Process files
        files_to_delete: List[Tuple[str, float, int]] = []
        
        for filename in pdf_files[:MAX_FILES_PER_RUN]:  # Limit files per run
            stats["files_checked"] += 1
            file_path = os.path.join(storage_path, filename)
            
            try:
                # Get file stats
                file_stat = os.stat(file_path)
                file_mtime = file_stat.st_mtime
                file_size = file_stat.st_size
                
                # Check if file is old enough to delete
                if file_mtime < cutoff_time:
                    files_to_delete.append((filename, file_mtime, file_size))
                    
            except Exception as e:
                logger.warning(f"[CLEANUP] Error checking file {filename}: {e}")
                stats["files_failed"] += 1
                stats["errors"].append(f"Error checking {filename}: {str(e)}")
        
        # Sort by modification time (oldest first)
        files_to_delete.sort(key=lambda x: x[1])
        
        logger.info(f"[CLEANUP] Found {len(files_to_delete)} files to delete")
        
        # Delete old files
        for filename, mtime, size in files_to_delete:
            file_path = os.path.join(storage_path, filename)
            file_age_days = (time.time() - mtime) / (24 * 60 * 60)
            
            try:
                # Extract project_id from filename (format: project_id.pdf)
                project_id = filename[:-4] if filename.endswith('.pdf') else filename
                
                logger.info(f"[CLEANUP] Deleting {filename} (age: {file_age_days:.1f} days, size: {size} bytes)")
                
                # Delete the file
                os.unlink(file_path)
                
                stats["files_deleted"] += 1
                stats["bytes_freed"] += size
                
                # Update database record if exists
                try:
                    # Mark project as cleaned up in database
                    async def mark_cleaned():
                        async with AsyncSessionLocal() as session:
                            success = await job_service.update_project(
                                project_id, 
                                {"cleanup_timestamp": datetime.utcnow()},
                                session
                            )
                            if success:
                                stats["db_records_cleaned"] += 1
                    
                    # Run async operation
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(mark_cleaned())
                    loop.close()
                    
                except Exception as e:
                    logger.warning(f"[CLEANUP] Could not update database for {project_id}: {e}")
                
            except Exception as e:
                logger.error(f"[CLEANUP] Error deleting file {filename}: {e}")
                stats["files_failed"] += 1
                stats["errors"].append(f"Error deleting {filename}: {str(e)}")
        
        # Log summary
        logger.info(f"[CLEANUP] Cleanup complete:")
        logger.info(f"[CLEANUP]   Files checked: {stats['files_checked']}")
        logger.info(f"[CLEANUP]   Files deleted: {stats['files_deleted']}")
        logger.info(f"[CLEANUP]   Files failed: {stats['files_failed']}")
        logger.info(f"[CLEANUP]   Bytes freed: {stats['bytes_freed']:,} ({stats['bytes_freed'] / (1024*1024):.1f} MB)")
        logger.info(f"[CLEANUP]   DB records updated: {stats['db_records_cleaned']}")
        
        if stats["errors"]:
            logger.warning(f"[CLEANUP] Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"][:10]:  # Log first 10 errors
                logger.warning(f"[CLEANUP]   - {error}")
        
        return stats
        
    except Exception as e:
        logger.error(f"[CLEANUP] Fatal error during cleanup: {e}", exc_info=True)
        return {"error": f"Fatal error: {str(e)}"}


@celery_app.task
def health_check():
    """Simple health check task for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "storage_path": os.getenv("RENDER_DISK_PATH")
    }


# Celery beat schedule configuration
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'tasks.cleanup_tasks.cleanup_old_files',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
        'options': {
            'queue': 'celery',
            'routing_key': 'celery'
        }
    },
    'health-check': {
        'task': 'tasks.cleanup_tasks.health_check',
        'schedule': 300.0,  # Every 5 minutes
        'options': {
            'queue': 'celery',
            'routing_key': 'celery'
        }
    }
}

# Configure timezone
celery_app.conf.timezone = 'UTC'