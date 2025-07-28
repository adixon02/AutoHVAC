"""Database-based rate limiter for API endpoints
Uses the projects table as the single source of truth for active job counting.
"""
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from sqlmodel import select, func, and_
from database import AsyncSessionLocal
from models.db_models import Project, JobStatus
import redis
import os

logger = logging.getLogger(__name__)

class DatabaseRateLimiter:
    """Database-based rate limiter that uses project status as source of truth"""
    
    def __init__(self):
        # Keep Redis for request rate limiting only (not job counting)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.redis_enabled = True
        
        try:
            self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connected for request rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available, request rate limiting disabled: {str(e)}")
            self.redis_enabled = False
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 3600,
        burst_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if request is within rate limit
        
        Args:
            key: User email
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            burst_limit: Maximum concurrent jobs (queries database)
        
        Returns:
            Dict with allowed, remaining, reset_time, and reason
        """
        current_time = time.time()
        
        # Check concurrent job limit using database
        if burst_limit:
            async with AsyncSessionLocal() as session:
                # Count active processing jobs for this user
                stmt = select(func.count(Project.id)).where(
                    and_(
                        Project.user_email == key,
                        Project.status == JobStatus.PROCESSING
                    )
                )
                result = await session.execute(stmt)
                active_count = result.scalar() or 0
                
                if active_count >= burst_limit:
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_time": current_time + 300,  # 5 minute cooldown
                        "reason": f"too_many_concurrent_jobs ({active_count}/{burst_limit})"
                    }
        
        # Check request rate limit using Redis (if available)
        if self.redis_enabled and self.redis_client:
            try:
                window_start = current_time - window_seconds
                
                pipe = self.redis_client.pipeline()
                
                # Clean up old entries
                pipe.zremrangebyscore(f"req:{key}", 0, window_start)
                
                # Count current requests in window
                pipe.zcard(f"req:{key}")
                
                # Add current request
                pipe.zadd(f"req:{key}", {str(current_time): current_time})
                
                # Set expiration
                pipe.expire(f"req:{key}", window_seconds + 60)
                
                results = pipe.execute()
                current_count = results[1] + 1  # +1 for the request we just added
                
                # Check rate limit
                if current_count > limit:
                    # Remove the request we just added since it's rejected
                    self.redis_client.zrem(f"req:{key}", str(current_time))
                    
                    # Find when the oldest request will expire
                    oldest = self.redis_client.zrange(f"req:{key}", 0, 0, withscores=True)
                    reset_time = oldest[0][1] + window_seconds if oldest else current_time + window_seconds
                    
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_time": reset_time,
                        "reason": f"rate_limit_exceeded ({current_count}/{limit})"
                    }
                
                return {
                    "allowed": True,
                    "remaining": max(0, limit - current_count),
                    "reset_time": current_time + window_seconds,
                    "reason": "within_limits"
                }
                
            except Exception as e:
                logger.error(f"Redis rate limiter error for key {key}: {str(e)}")
        
        # If Redis is not available, only check burst limit
        return {
            "allowed": True,
            "remaining": limit,
            "reset_time": current_time + window_seconds,
            "reason": "rate_limiting_partial"
        }
    
    async def get_user_stats(self, user_email: str) -> Dict[str, Any]:
        """Get current rate limiting stats for user from database"""
        async with AsyncSessionLocal() as session:
            # Count active jobs
            active_stmt = select(func.count(Project.id)).where(
                and_(
                    Project.user_email == user_email,
                    Project.status == JobStatus.PROCESSING
                )
            )
            active_result = await session.execute(active_stmt)
            active_jobs = active_result.scalar() or 0
            
            # Count recent requests from Redis (if available)
            recent_requests = 0
            if self.redis_enabled and self.redis_client:
                try:
                    current_time = time.time()
                    hour_ago = current_time - 3600
                    recent_requests = self.redis_client.zcount(f"req:{user_email}", hour_ago, current_time)
                except Exception as e:
                    logger.error(f"Error getting request count for {user_email}: {str(e)}")
            
            return {
                "active_jobs": active_jobs,
                "recent_requests": recent_requests
            }
    
    async def cleanup_stuck_jobs(self, older_than_minutes: int = 60) -> int:
        """Mark stuck processing jobs as failed and return count"""
        async with AsyncSessionLocal() as session:
            cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
            
            # Find stuck jobs
            stmt = select(Project).where(
                and_(
                    Project.status == JobStatus.PROCESSING,
                    Project.created_at < cutoff_time
                )
            )
            result = await session.execute(stmt)
            stuck_jobs = result.scalars().all()
            
            # Mark them as failed
            cleaned_count = 0
            for job in stuck_jobs:
                job.status = JobStatus.FAILED
                job.error = f"Job timed out after {older_than_minutes} minutes"
                job.completed_at = datetime.utcnow()
                cleaned_count += 1
                logger.warning(f"Cleaned up stuck job {job.id} for user {job.user_email}")
            
            await session.commit()
            return cleaned_count
    
    # Compatibility methods (no-ops since we use database)
    async def increment_active_jobs(self, user_email: str, job_id: str, ttl_seconds: int = 3600):
        """No-op - job counting is done via database queries"""
        pass
    
    async def decrement_active_jobs(self, user_email: str, job_id: str):
        """No-op - job counting is done via database queries"""
        pass

# Global instance
database_rate_limiter = DatabaseRateLimiter()