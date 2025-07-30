"""
Scheduled cleanup tasks for managing S3 storage
Runs periodically to clean up old files in S3
"""
import os
import time
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab
import logging
import boto3
from botocore.exceptions import ClientError

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

# S3 configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
S3_BUCKET = os.getenv("S3_BUCKET", "autohvac-uploads")

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

def get_s3_client():
    """Create S3 client with credentials"""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def get_object_age_hours(last_modified: datetime) -> float:
    """Get age of S3 object in hours"""
    age = datetime.now(last_modified.tzinfo) - last_modified
    return age.total_seconds() / 3600

def get_object_age_days(last_modified: datetime) -> float:
    """Get age of S3 object in days"""
    return get_object_age_hours(last_modified) / 24

@celery_app.task(
    acks_late=True,
    time_limit=600,  # 10 minutes max
    soft_time_limit=540  # 9 minutes soft limit
)
def cleanup_temp_files():
    """Clean up temporary files older than TEMP_RETENTION_HOURS from S3"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    s3_client = get_s3_client()
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting temp file cleanup in S3 (retention: {TEMP_RETENTION_HOURS} hours)")
    
    try:
        # List all objects in temp/ prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=S3_BUCKET,
            Prefix='temp/'
        )
        
        objects_to_delete = []
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                # Check object age
                age_hours = get_object_age_hours(obj['LastModified'])
                
                if age_hours > TEMP_RETENTION_HOURS:
                    objects_to_delete.append({
                        'Key': obj['Key'],
                        'Size': obj['Size'],
                        'Age': age_hours
                    })
        
        # Delete objects in batches of 1000 (S3 limit)
        for i in range(0, len(objects_to_delete), 1000):
            batch = objects_to_delete[i:i+1000]
            delete_keys = [{'Key': obj['Key']} for obj in batch]
            
            try:
                response = s3_client.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={'Objects': delete_keys}
                )
                
                # Count successful deletions
                if 'Deleted' in response:
                    cleaned_count += len(response['Deleted'])
                    total_size_cleaned += sum(obj['Size'] for obj in batch)
                    
                    for obj in batch[:5]:  # Log first 5 for brevity
                        logger.info(f"[CLEANUP] Deleted temp file: {obj['Key']} "
                                  f"(age: {obj['Age']:.1f}h, size: {obj['Size']/1024/1024:.2f}MB)")
                
                # Count errors
                if 'Errors' in response:
                    error_count += len(response['Errors'])
                    for error in response['Errors']:
                        logger.error(f"[CLEANUP] Failed to delete {error['Key']}: {error['Message']}")
                        
            except Exception as e:
                error_count += len(batch)
                logger.error(f"[CLEANUP] Batch deletion failed: {e}")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during temp cleanup: {e}")
        return {"status": "error", "reason": str(e)}
    
    logger.info(f"[CLEANUP] Temp cleanup completed: {cleaned_count} files removed, "
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
    """Clean up uploaded files older than UPLOAD_RETENTION_DAYS from S3"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    s3_client = get_s3_client()
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting upload file cleanup in S3 (retention: {UPLOAD_RETENTION_DAYS} days)")
    
    try:
        # List all objects in uploads/ prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=S3_BUCKET,
            Prefix='uploads/'
        )
        
        objects_to_delete = []
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                # Skip directory markers
                if obj['Key'].endswith('/'):
                    continue
                
                # Check object age
                age_days = get_object_age_days(obj['LastModified'])
                
                if age_days > UPLOAD_RETENTION_DAYS:
                    objects_to_delete.append({
                        'Key': obj['Key'],
                        'Size': obj['Size'],
                        'Age': age_days
                    })
        
        # Delete objects
        for obj in objects_to_delete:
            try:
                s3_client.delete_object(
                    Bucket=S3_BUCKET,
                    Key=obj['Key']
                )
                cleaned_count += 1
                total_size_cleaned += obj['Size']
                
                logger.info(f"[CLEANUP] Removed old upload: {obj['Key']} "
                          f"(age: {obj['Age']:.1f}d, size: {obj['Size']/1024/1024:.2f}MB)")
                          
            except Exception as e:
                error_count += 1
                logger.error(f"[CLEANUP] Failed to remove upload {obj['Key']}: {e}")
    
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
    """Clean up processed files older than PROCESSED_RETENTION_DAYS from S3"""
    if not STORAGE_CLEANUP_ENABLED:
        logger.info("[CLEANUP] Storage cleanup is disabled")
        return {"status": "skipped", "reason": "cleanup disabled"}
    
    s3_client = get_s3_client()
    cleaned_count = 0
    error_count = 0
    total_size_cleaned = 0
    
    logger.info(f"[CLEANUP] Starting processed file cleanup in S3 (retention: {PROCESSED_RETENTION_DAYS} days)")
    
    try:
        # List all objects in processed/ prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=S3_BUCKET,
            Prefix='processed/'
        )
        
        # Group objects by project (subdirectory)
        projects_to_check = {}
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                # Skip directory markers
                if obj['Key'].endswith('/'):
                    continue
                
                # Extract project ID from key (processed/{project_id}/...)
                parts = obj['Key'].split('/')
                if len(parts) >= 2:
                    project_id = parts[1]
                    
                    if project_id not in projects_to_check:
                        projects_to_check[project_id] = []
                    
                    projects_to_check[project_id].append({
                        'Key': obj['Key'],
                        'Size': obj['Size'],
                        'LastModified': obj['LastModified']
                    })
        
        # Check each project's oldest file
        for project_id, objects in projects_to_check.items():
            # Find oldest file in project
            oldest_date = min(obj['LastModified'] for obj in objects)
            age_days = get_object_age_days(oldest_date)
            
            if age_days > PROCESSED_RETENTION_DAYS:
                # Delete all files for this project
                project_size = sum(obj['Size'] for obj in objects)
                
                for obj in objects:
                    try:
                        s3_client.delete_object(
                            Bucket=S3_BUCKET,
                            Key=obj['Key']
                        )
                        cleaned_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"[CLEANUP] Failed to delete {obj['Key']}: {e}")
                
                total_size_cleaned += project_size
                logger.info(f"[CLEANUP] Removed processed project: {project_id} "
                          f"(age: {age_days:.1f}d, size: {project_size/1024/1024:.2f}MB, "
                          f"files: {len(objects)})")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during processed cleanup: {e}")
        return {"status": "error", "reason": str(e)}
    
    logger.info(f"[CLEANUP] Processed cleanup completed: {cleaned_count} files removed, "
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
    """Immediately clean up temp files for a specific project from S3"""
    s3_client = get_s3_client()
    
    try:
        # List all objects with the project prefix
        prefix = f"temp/{project_id}/"
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=S3_BUCKET,
            Prefix=prefix
        )
        
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            # Delete all objects
            response = s3_client.delete_objects(
                Bucket=S3_BUCKET,
                Delete={'Objects': objects_to_delete}
            )
            
            deleted_count = len(response.get('Deleted', []))
            logger.info(f"[CLEANUP] Manually removed {deleted_count} temp files for project {project_id}")
            return {"status": "success", "project_id": project_id, "deleted_count": deleted_count}
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
        "storage_type": "S3",
        "s3_bucket": S3_BUCKET,
        "cleanup_enabled": STORAGE_CLEANUP_ENABLED,
        "retention_config": {
            "temp_hours": TEMP_RETENTION_HOURS,
            "upload_days": UPLOAD_RETENTION_DAYS,
            "processed_days": PROCESSED_RETENTION_DAYS
        }
    }