import json
import redis
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class JobStorage:
    """Redis-based job storage for production persistence"""
    
    def __init__(self):
        self.redis_client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis connected successfully")
            else:
                logger.warning("⚠️ REDIS_URL not set - falling back to in-memory storage")
                self.redis_client = None
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e} - falling back to in-memory storage")
            self.redis_client = None
    
    def _get_job_key(self, job_id: str) -> str:
        """Generate Redis key for job"""
        return f"job:{job_id}"
    
    def save_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Save job to Redis (or in-memory fallback)"""
        try:
            if self.redis_client:
                # Save to Redis with 24 hour expiration
                job_json = json.dumps(job_data, default=str)
                key = self._get_job_key(job_id)
                self.redis_client.setex(key, 86400, job_json)  # 24 hours
                logger.info(f"💾 REDIS: Saved job {job_id}")
                return True
            else:
                # Fallback to in-memory (for local development)
                from app.routes.blueprint import jobs
                jobs[job_id] = job_data
                logger.info(f"💾 MEMORY: Saved job {job_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job from Redis (or in-memory fallback)"""
        try:
            if self.redis_client:
                key = self._get_job_key(job_id)
                job_json = self.redis_client.get(key)
                if job_json:
                    job_data = json.loads(job_json)
                    logger.info(f"📖 REDIS: Retrieved job {job_id}")
                    return job_data
                else:
                    logger.warning(f"❌ REDIS: Job {job_id} not found")
                    return None
            else:
                # Fallback to in-memory
                from app.routes.blueprint import jobs
                if job_id in jobs:
                    logger.info(f"📖 MEMORY: Retrieved job {job_id}")
                    return jobs[job_id]
                else:
                    logger.warning(f"❌ MEMORY: Job {job_id} not found")
                    return None
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job data"""
        try:
            job_data = self.get_job(job_id)
            if job_data:
                job_data.update(updates)
                return self.save_job(job_id, job_data)
            return False
        except Exception as e:
            logger.error(f"❌ Failed to update job {job_id}: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job"""
        try:
            if self.redis_client:
                key = self._get_job_key(job_id)
                result = self.redis_client.delete(key)
                logger.info(f"🗑️ REDIS: Deleted job {job_id}")
                return result > 0
            else:
                from app.routes.blueprint import jobs
                if job_id in jobs:
                    del jobs[job_id]
                    logger.info(f"🗑️ MEMORY: Deleted job {job_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ Failed to delete job {job_id}: {e}")
            return False
    
    def get_job_count(self) -> int:
        """Get total number of jobs"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys("job:*")
                return len(keys)
            else:
                from app.routes.blueprint import jobs
                return len(jobs)
        except Exception as e:
            logger.error(f"❌ Failed to get job count: {e}")
            return 0
    
    def get_recent_jobs(self, limit: int = 5) -> list:
        """Get recent job IDs"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys("job:*")
                job_ids = [key.replace("job:", "") for key in keys[-limit:]]
                return job_ids
            else:
                from app.routes.blueprint import jobs
                return list(jobs.keys())[-limit:]
        except Exception as e:
            logger.error(f"❌ Failed to get recent jobs: {e}")
            return []

# Global instance
job_storage = JobStorage()