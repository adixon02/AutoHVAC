import redis
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

class RateLimiter:
    """Redis-based rate limiter for API endpoints"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
        self.enabled = True
        
        try:
            self.client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("Redis rate limiter initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, rate limiting disabled: {str(e)}")
            self.enabled = False
    
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
            key: Unique identifier (e.g., user email, IP)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            burst_limit: Maximum concurrent requests (for upload limiting)
        
        Returns:
            Dict with allowed, remaining, reset_time, and reason
        """
        if not self.enabled or not self.client:
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": time.time() + window_seconds,
                "reason": "rate_limiting_disabled"
            }
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        try:
            pipe = self.client.pipeline()
            
            # Clean up old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_seconds + 60)  # Extra buffer
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            # Check burst limit (concurrent jobs)
            if burst_limit:
                active_jobs_key = f"{key}:active_jobs"
                active_count = self.client.get(active_jobs_key) or 0
                active_count = int(active_count)
                
                if active_count >= burst_limit:
                    # Remove the request we just added since it's rejected
                    self.client.zrem(key, str(current_time))
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_time": current_time + 300,  # 5 minute cooldown
                        "reason": f"too_many_concurrent_jobs ({active_count}/{burst_limit})"
                    }
            
            # Check rate limit
            if current_count > limit:
                # Remove the request we just added since it's rejected
                self.client.zrem(key, str(current_time))
                
                # Find when the oldest request will expire
                oldest = self.client.zrange(key, 0, 0, withscores=True)
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
            logger.error(f"Rate limiter error for key {key}: {str(e)}")
            # Fail open - allow request if rate limiter fails
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": current_time + window_seconds,
                "reason": "rate_limiter_error"
            }
    
    async def increment_active_jobs(self, user_email: str, job_id: str, ttl_seconds: int = 3600):
        """Track active jobs for burst limiting"""
        if not self.enabled or not self.client:
            return
        
        try:
            active_jobs_key = f"{user_email}:active_jobs"
            jobs_list_key = f"{user_email}:job_list"
            
            # Increment counter
            pipe = self.client.pipeline()
            pipe.incr(active_jobs_key)
            pipe.expire(active_jobs_key, ttl_seconds)
            
            # Track individual job
            pipe.sadd(jobs_list_key, job_id)
            pipe.expire(jobs_list_key, ttl_seconds)
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Error incrementing active jobs for {user_email}: {str(e)}")
    
    async def decrement_active_jobs(self, user_email: str, job_id: str):
        """Decrement active jobs counter when job completes"""
        if not self.enabled or not self.client:
            return
        
        try:
            active_jobs_key = f"{user_email}:active_jobs"
            jobs_list_key = f"{user_email}:job_list"
            
            pipe = self.client.pipeline()
            
            # Remove from job list
            pipe.srem(jobs_list_key, job_id)
            
            # Decrement counter (but don't go below 0)
            current = self.client.get(active_jobs_key) or 0
            current = max(0, int(current) - 1)
            
            if current > 0:
                pipe.set(active_jobs_key, current)
            else:
                pipe.delete(active_jobs_key)
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Error decrementing active jobs for {user_email}: {str(e)}")
    
    async def get_user_stats(self, user_email: str) -> Dict[str, Any]:
        """Get current rate limiting stats for user"""
        if not self.enabled or not self.client:
            return {"active_jobs": 0, "recent_requests": 0}
        
        try:
            active_jobs_key = f"{user_email}:active_jobs"
            rate_limit_key = user_email
            
            # Get active jobs count
            active_jobs = self.client.get(active_jobs_key) or 0
            active_jobs = int(active_jobs)
            
            # Get recent requests (last hour)
            current_time = time.time()
            hour_ago = current_time - 3600
            recent_requests = self.client.zcount(rate_limit_key, hour_ago, current_time)
            
            return {
                "active_jobs": active_jobs,
                "recent_requests": recent_requests
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_email}: {str(e)}")
            return {"active_jobs": 0, "recent_requests": 0}

# Global instance
rate_limiter = RateLimiter()