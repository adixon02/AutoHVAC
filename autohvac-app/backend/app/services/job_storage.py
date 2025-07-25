"""
Job storage service with Redis and in-memory fallback
"""
import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..core import settings, get_logger
from ..models.requests import JobStatusEnum

logger = get_logger(__name__)


class JobStorageService:
    """Service for storing and retrieving job data"""
    
    def __init__(self):
        self.redis_client = self._init_redis()
        self.memory_storage: Dict[str, Dict[str, Any]] = {}
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis client with error handling"""
        try:
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            logger.info("Redis connection established")
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory storage: {e}")
            return None
    
    def create_job(self, filename: str, file_size: int) -> str:
        """Create a new job entry"""
        job_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        job_data = {
            "job_id": job_id,
            "status": JobStatusEnum.QUEUED.value,
            "created_at": timestamp,
            "updated_at": timestamp,
            "filename": filename,
            "file_size": file_size,
            "progress_percent": 0,
            "message": "Job queued for processing"
        }
        
        self._store_job(job_id, job_data)
        logger.info(f"Created job {job_id} for file {filename}")
        return job_id
    
    def update_job_status(
        self, 
        job_id: str, 
        status: JobStatusEnum, 
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Update job status and metadata"""
        job_data = self.get_job(job_id)
        if not job_data:
            logger.error(f"Cannot update non-existent job: {job_id}")
            return False
        
        job_data.update({
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        if progress is not None:
            job_data["progress_percent"] = progress
        if message is not None:
            job_data["message"] = message
        if result is not None:
            job_data["result"] = result
        if error is not None:
            job_data["error"] = error
        
        self._store_job(job_id, job_data)
        logger.info(f"Updated job {job_id} status to {status.value}")
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data"""
        if self.redis_client:
            try:
                job_data = self.redis_client.get(f"job:{job_id}")
                if job_data:
                    return json.loads(job_data)
            except Exception as e:
                logger.error(f"Error reading from Redis: {e}")
        
        # Fallback to memory storage
        return self.memory_storage.get(job_id)
    
    def _store_job(self, job_id: str, job_data: Dict[str, Any]):
        """Store job data in Redis with fallback to memory"""
        if self.redis_client:
            try:
                # Store with 24 hour expiration
                self.redis_client.setex(
                    f"job:{job_id}", 
                    86400,  # 24 hours
                    json.dumps(job_data)
                )
                return
            except Exception as e:
                logger.error(f"Error writing to Redis: {e}")
        
        # Fallback to memory storage
        self.memory_storage[job_id] = job_data
    
    def cleanup_old_jobs(self):
        """Clean up old jobs from memory storage (Redis handles this automatically)"""
        if not self.redis_client:
            # Only clean memory storage if not using Redis
            current_time = datetime.utcnow()
            to_remove = []
            
            for job_id, job_data in self.memory_storage.items():
                created_at = datetime.fromisoformat(job_data["created_at"])
                age_hours = (current_time - created_at).total_seconds() / 3600
                
                if age_hours > 24:  # Remove jobs older than 24 hours
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del self.memory_storage[job_id]
                logger.info(f"Cleaned up old job: {job_id}")


# Global instance
job_storage = JobStorageService()