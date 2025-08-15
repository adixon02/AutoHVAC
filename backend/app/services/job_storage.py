import json
import redis
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.models.user import JobModel, JobStatus, JobPriority, JobLogEntry

logger = logging.getLogger(__name__)

class JobStorage:
    """
    Production job storage with PostgreSQL primary + Redis cache
    
    Architecture:
    - PostgreSQL: Primary persistent storage (survives restarts/deploys)
    - Redis: High-performance cache layer (optional, graceful fallback)
    """
    
    def __init__(self):
        self.redis_client = None
        self.redis_available = False
        self._initialize_redis()
        logger.info("🏗️  JobStorage initialized (PostgreSQL primary + Redis cache)")
    
    def _initialize_redis(self):
        """Initialize Redis connection with graceful fallback"""
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info("✅ Redis cache layer connected")
            else:
                logger.info("ℹ️  REDIS_URL not set - PostgreSQL only mode")
                self.redis_available = False
        except Exception as e:
            logger.warning(f"⚠️  Redis cache unavailable: {e} - PostgreSQL only mode")
            self.redis_client = None
            self.redis_available = False
    
    def _get_job_key(self, job_id: str) -> str:
        """Generate Redis key for job"""
        return f"job:{job_id}"
    
    def _cache_job_data(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Cache job data in Redis for performance"""
        if not self.redis_available:
            return
            
        try:
            job_json = json.dumps(job_data, default=str)
            key = self._get_job_key(job_id)
            self.redis_client.setex(key, 3600, job_json)  # 1 hour cache
            logger.debug(f"📦 CACHE: Stored job {job_id}")
        except Exception as e:
            logger.warning(f"⚠️  Cache write failed for {job_id}: {e}")
    
    def save_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Save job to PostgreSQL with Redis cache"""
        try:
            with Session(engine) as session:
                # Check if job already exists
                existing = session.get(JobModel, job_id)
                if existing:
                    # Update existing job
                    existing.status = JobStatus(job_data.get("status", "created"))
                    existing.progress = job_data.get("progress", 0)
                    existing.result_data = job_data.get("result")
                    existing.error_data = {"message": job_data.get("error")} if job_data.get("error") else None
                    existing.updated_at = datetime.utcnow()
                    
                    session.add(existing)
                    session.commit()
                    logger.info(f"💾 DB: Updated job {job_id}")
                else:
                    # Create new job
                    job = JobModel(
                        id=job_id,
                        user_email=job_data.get("email", "unknown"),
                        filename=job_data.get("filename", "unknown.pdf"),
                        project_label=job_data.get("project_label", job_data.get("filename", "unknown")),
                        zip_code=job_data.get("zip_code", "00000"),
                        status=JobStatus(job_data.get("status", "created")),
                        progress=job_data.get("progress", 0),
                        user_inputs=job_data.get("user_inputs", {}),
                        result_data=job_data.get("result"),
                        error_data={"message": job_data.get("error")} if job_data.get("error") else None,
                        is_free_report=job_data.get("is_first_report", False),
                        requires_upgrade=job_data.get("needs_upgrade", False)
                    )
                    
                    session.add(job)
                    session.commit()
                    logger.info(f"💾 DB: Created job {job_id}")
                
                # Cache in Redis for performance
                self._cache_job_data(job_id, job_data)
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"❌ DB: Failed to save job {job_id}: {e}")
            # Fallback to in-memory for local development
            try:
                from app.routes.blueprint import jobs
                jobs[job_id] = job_data
                logger.info(f"💾 MEMORY FALLBACK: Saved job {job_id}")
                return True
            except:
                return False
        except Exception as e:
            logger.error(f"❌ SYSTEM: Failed to save job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job with cache-first strategy"""
        try:
            # Try Redis cache first for performance
            if self.redis_available:
                key = self._get_job_key(job_id)
                cached_json = self.redis_client.get(key)
                if cached_json:
                    job_data = json.loads(cached_json)
                    logger.debug(f"🎯 CACHE HIT: Retrieved job {job_id}")
                    return job_data
            
            # Fallback to PostgreSQL
            with Session(engine) as session:
                job = session.get(JobModel, job_id)
                if job:
                    # Convert to API format
                    job_data = {
                        "status": job.status,
                        "progress": job.progress,
                        "filename": job.filename,
                        "project_label": job.project_label,
                        "zip_code": job.zip_code,
                        "email": job.user_email,
                        "user_inputs": job.user_inputs,
                        "created_at": job.created_at.isoformat(),
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "result": job.result_data,
                        "error": job.error_data.get("message") if job.error_data else None,
                        "needs_upgrade": job.requires_upgrade,
                        "is_first_report": job.is_free_report
                    }
                    
                    # Cache for next time
                    self._cache_job_data(job_id, job_data)
                    
                    logger.info(f"📖 DB: Retrieved job {job_id}")
                    return job_data
                else:
                    logger.warning(f"❌ DB: Job {job_id} not found")
                    
                    # Final fallback to in-memory for local development
                    try:
                        from app.routes.blueprint import jobs
                        if job_id in jobs:
                            logger.info(f"📖 MEMORY FALLBACK: Retrieved job {job_id}")
                            return jobs[job_id]
                    except:
                        pass
                    
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"❌ DB: Failed to get job {job_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ SYSTEM: Failed to get job {job_id}: {e}")
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