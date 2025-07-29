"""Admin endpoints for system maintenance and debugging"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import redis
import os
import logging
from datetime import datetime, timedelta
from sqlmodel import select, func, and_
from database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import Project, JobStatus
from services.database_rate_limiter import database_rate_limiter as rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/clear-rate-limits")
async def clear_rate_limits(email: str = None):
    """
    Clear rate limit counters for a specific user or all users
    
    Args:
        email: User email to clear limits for. If None, clears all.
    """
    if not rate_limiter.enabled or not rate_limiter.client:
        return {"status": "error", "message": "Rate limiter not enabled"}
    
    try:
        if email:
            # Clear specific user's counters
            active_jobs_key = f"{email}:active_jobs"
            jobs_list_key = f"{email}:job_list"
            rate_limit_key = email
            
            deleted_count = 0
            deleted_count += rate_limiter.client.delete(active_jobs_key)
            deleted_count += rate_limiter.client.delete(jobs_list_key)
            deleted_count += rate_limiter.client.delete(rate_limit_key)
            
            return {
                "status": "success",
                "message": f"Cleared rate limits for {email}",
                "keys_deleted": deleted_count
            }
        else:
            # Clear all rate limit keys (dangerous - use with caution)
            pattern_counts = {}
            
            # Find and delete all rate limit related keys
            for pattern in ["*:active_jobs", "*:job_list"]:
                keys = rate_limiter.client.keys(pattern)
                if keys:
                    deleted = rate_limiter.client.delete(*keys)
                    pattern_counts[pattern] = deleted
            
            return {
                "status": "success",
                "message": "Cleared all rate limits",
                "patterns_cleared": pattern_counts
            }
            
    except Exception as e:
        logger.error(f"Error clearing rate limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rate-limit-status")
async def get_rate_limit_status(email: str = None):
    """
    Get current rate limit status for debugging
    
    Args:
        email: User email to check. If None, returns all users.
    """
    if not rate_limiter.enabled or not rate_limiter.client:
        return {"status": "error", "message": "Rate limiter not enabled"}
    
    try:
        if email:
            # Get specific user's status
            active_jobs_key = f"{email}:active_jobs"
            jobs_list_key = f"{email}:job_list"
            
            active_count = rate_limiter.client.get(active_jobs_key) or 0
            job_ids = rate_limiter.client.smembers(jobs_list_key) or set()
            
            return {
                "email": email,
                "active_jobs_count": int(active_count),
                "job_ids": list(job_ids),
                "limit": 5
            }
        else:
            # Get all users with active jobs
            users_status = []
            
            # Find all active_jobs keys
            keys = rate_limiter.client.keys("*:active_jobs")
            for key in keys:
                email = key.decode('utf-8').replace(':active_jobs', '')
                active_count = rate_limiter.client.get(key) or 0
                jobs_list_key = f"{email}:job_list"
                job_ids = rate_limiter.client.smembers(jobs_list_key) or set()
                
                users_status.append({
                    "email": email,
                    "active_jobs_count": int(active_count),
                    "job_ids": [j.decode('utf-8') if isinstance(j, bytes) else j for j in job_ids]
                })
            
            return {
                "total_users_with_limits": len(users_status),
                "users": users_status
            }
            
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job-status-summary")
async def get_job_status_summary(session: AsyncSession = Depends(get_async_session)):
    """Get summary of all jobs in the database by status"""
    try:
        # Count jobs by status
        stmt = select(
            Project.status,
            func.count(Project.id).label('count')
        ).group_by(Project.status)
        
        result = await session.exec(stmt)
        status_counts = {row.status.value: row.count for row in result}
        
        # Get stuck processing jobs (older than 1 hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stuck_stmt = select(Project).where(
            and_(
                Project.status == JobStatus.PROCESSING,
                Project.created_at < one_hour_ago
            )
        )
        stuck_result = await session.exec(stuck_stmt)
        stuck_jobs = stuck_result.all()
        
        # Count active jobs per user
        active_stmt = select(
            Project.user_email,
            func.count(Project.id).label('count')
        ).where(
            Project.status == JobStatus.PROCESSING
        ).group_by(Project.user_email)
        
        active_result = await session.exec(active_stmt)
        active_by_user = {row.user_email: row.count for row in active_result}
        
        return {
            "status_counts": status_counts,
            "stuck_jobs": [
                {
                    "id": job.id,
                    "email": job.user_email,
                    "created_at": job.created_at.isoformat(),
                    "age_minutes": int((datetime.utcnow() - job.created_at).total_seconds() / 60)
                }
                for job in stuck_jobs
            ],
            "active_jobs_by_user": active_by_user,
            "total_stuck": len(stuck_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error getting job status summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup-stuck-jobs")
async def cleanup_stuck_jobs(
    older_than_minutes: int = 60,
    session: AsyncSession = Depends(get_async_session)
):
    """Mark stuck processing jobs as failed"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        
        # Find stuck jobs
        stmt = select(Project).where(
            and_(
                Project.status == JobStatus.PROCESSING,
                Project.created_at < cutoff_time
            )
        )
        result = await session.exec(stmt)
        stuck_jobs = result.all()
        
        # Mark them as failed
        cleaned_count = 0
        for job in stuck_jobs:
            job.status = JobStatus.FAILED
            job.error = f"Job timed out after {older_than_minutes} minutes"
            job.completed_at = datetime.utcnow()
            cleaned_count += 1
        
        await session.commit()
        
        return {
            "status": "success",
            "cleaned_count": cleaned_count,
            "cleaned_jobs": [job.id for job in stuck_jobs]
        }
        
    except Exception as e:
        logger.error(f"Error cleaning stuck jobs: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/redis-info")
async def get_redis_info():
    """Get Redis connection info and key statistics"""
    if not rate_limiter.enabled or not rate_limiter.client:
        return {"status": "error", "message": "Redis not connected"}
    
    try:
        info = rate_limiter.client.info()
        
        # Count different key patterns
        patterns = {
            "active_jobs": len(rate_limiter.client.keys("*:active_jobs")),
            "job_lists": len(rate_limiter.client.keys("*:job_list")),
            "rate_limits": len(rate_limiter.client.keys("*@*"))  # Email pattern
        }
        
        return {
            "connected": True,
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_keys": rate_limiter.client.dbsize(),
            "key_patterns": patterns
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}