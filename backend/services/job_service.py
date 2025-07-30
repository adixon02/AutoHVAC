from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import Project, JobStatus, User
from database import AsyncSessionLocal, SyncSessionLocal
from datetime import datetime, timezone
import uuid
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Debug flag to disable cleanup on failure
CLEANUP_ON_FAILURE = False  # Set to True in production

class JobService:
    """PostgreSQL-backed job service replacing InMemoryJobStore"""
    
    def __init__(self):
        # Simple job service for streamlined processing
        pass
    
    @staticmethod
    async def create_project(
        user_email: str,
        project_label: str,
        filename: str,
        file_size: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> str:
        """Create a new project and return its ID"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.create_project(user_email, project_label, filename, file_size, session)
        
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            user_email=user_email,
            project_label=project_label,
            filename=filename,
            file_size=file_size,
            status=JobStatus.PENDING
        )
        
        session.add(project)
        await session.commit()
        await session.refresh(project)
        
        return project_id
    
    @staticmethod
    async def create_project_with_assumptions(
        user_email: str,
        project_label: str,
        filename: str,
        file_size: Optional[int] = None,
        duct_config: str = "ducted_attic",
        heating_fuel: str = "gas",
        session: Optional[AsyncSession] = None
    ) -> str:
        """Create a new project with Manual J assumptions already collected"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.create_project_with_assumptions(
                    user_email, project_label, filename, file_size, 
                    duct_config, heating_fuel, session
                )
        
        project_id = str(uuid.uuid4())
        logger.info(f"Creating project {project_id} for user {user_email}")
        
        try:
            # Ensure user exists first to prevent foreign key constraint failures
            from services.user_service import user_service
            await user_service.get_or_create_user(user_email, session)
            logger.debug(f"User {user_email} confirmed/created for project {project_id}")
            
            project = Project(
                id=project_id,
                user_email=user_email,
                project_label=project_label,
                filename=filename,
                file_size=file_size,
                status=JobStatus.PENDING,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                assumptions_collected=True  # Already collected in multi-step flow
            )
            
            session.add(project)
            logger.debug(f"Project {project_id} added to session, committing...")
            
            await session.commit()
            await session.refresh(project)
            
            logger.info(f"✅ Project {project_id} created and committed successfully (status={project.status})")
            return project_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create project {project_id}: {str(e)}")
            try:
                await session.rollback()
                logger.debug(f"Session rolled back for project {project_id}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback session: {rollback_error}")
            
            raise HTTPException(
                status_code=500, 
                detail=f"Database error: Failed to create project - {str(e)}"
            )
    
    @staticmethod
    async def get_project(project_id: str, session: Optional[AsyncSession] = None) -> Optional[Project]:
        """Get project by ID"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.get_project(project_id, session)
        
        statement = select(Project).where(Project.id == project_id)
        result = await session.execute(statement)
        return result.scalars().first()
    
    @staticmethod
    async def update_project(
        project_id: str,
        updates: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Update project with given data"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.update_project(project_id, updates, session)
        
        project = await JobService.get_project(project_id, session)
        if not project:
            return False
        
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        # Set completion time if status changed to completed
        if updates.get("status") == JobStatus.COMPLETED:
            project.completed_at = datetime.utcnow()
        
        session.add(project)
        await session.commit()
        return True
    
    @staticmethod
    def sync_update_project(
        project_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Sync version of update_project for Celery workers"""
        with SyncSessionLocal() as session:
            # Get project with sync query
            project = session.get(Project, project_id)
            if not project:
                return False
            
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            
            # Set completion time if status changed to completed
            if updates.get("status") == JobStatus.COMPLETED:
                project.completed_at = datetime.utcnow()
            
            session.add(project)
            session.commit()
            return True
    
    @staticmethod
    async def get_user_projects(
        user_email: str,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Project]:
        """Get all projects for a user"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.get_user_projects(user_email, limit, session)
        
        statement = select(Project).where(Project.user_email == user_email).order_by(Project.created_at.desc())
        
        if limit:
            statement = statement.limit(limit)
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    @staticmethod
    async def delete_project(project_id: str, session: Optional[AsyncSession] = None) -> bool:
        """Delete a project"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.delete_project(project_id, session)
        
        project = await JobService.get_project(project_id, session)
        if not project:
            return False
        
        await session.delete(project)
        await session.commit()
        return True
    
    @staticmethod
    async def get_project_by_user_and_id(
        project_id: str,
        user_email: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[Project]:
        """Get project only if it belongs to the specified user"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.get_project_by_user_and_id(project_id, user_email, session)
        
        statement = select(Project).where(
            Project.id == project_id,
            Project.user_email == user_email
        )
        result = await session.execute(statement)
        return result.scalars().first()
    
    @staticmethod
    async def count_user_projects(user_email: str, session: Optional[AsyncSession] = None) -> int:
        """Count total projects for a user"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.count_user_projects(user_email, session)
        
        statement = select(Project).where(Project.user_email == user_email)
        result = await session.execute(statement)
        return len(result.scalars().all())
    
    @staticmethod
    async def get_projects_by_status(
        status: JobStatus,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Project]:
        """Get projects by status (useful for processing queue)"""
        if session is None:
            async with AsyncSessionLocal() as session:
                return await JobService.get_projects_by_status(status, limit, session)
        
        statement = select(Project).where(Project.status == status).order_by(Project.created_at)
        
        if limit:
            statement = statement.limit(limit)
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    @staticmethod
    async def set_project_processing(project_id: str, session: Optional[AsyncSession] = None) -> bool:
        """Mark project as processing"""
        return await JobService.update_project(
            project_id,
            {"status": JobStatus.PROCESSING},
            session
        )
    
    @staticmethod
    async def set_project_completed(
        project_id: str,
        result: Dict[str, Any],
        pdf_report_path: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Mark project as completed with results and cleanup files"""
        updates = {
            "status": JobStatus.COMPLETED,
            "result": result
        }
        
        if pdf_report_path:
            updates["pdf_report_path"] = pdf_report_path
        
        success = await JobService.update_project(project_id, updates, session)
        
        # Cleanup uploaded file after successful completion
        if success:
            try:
                from services.storage import storage_service
                storage_service.cleanup(project_id)
                logger.info(f"Cleaned up files for completed project {project_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup files for project {project_id}: {e}")
        
        return success
    
    @staticmethod
    async def set_project_failed(
        project_id: str,
        error: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Mark project as failed with error message and cleanup files"""
        success = await JobService.update_project(
            project_id,
            {"status": JobStatus.FAILED, "error": error},
            session
        )
        
        # Cleanup uploaded file after failure (disabled in debug mode)
        if success and CLEANUP_ON_FAILURE:
            try:
                from services.storage import storage_service
                storage_service.cleanup(project_id)
                logger.info(f"Cleaned up files for failed project {project_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup files for project {project_id}: {e}")
        elif success and not CLEANUP_ON_FAILURE:
            logger.warning(f"⚠️ CLEANUP DISABLED: Files preserved for failed project {project_id} for debugging")
        
        return success
    
    @staticmethod  
    def sync_set_project_completed(
        project_id: str,
        result: Dict[str, Any],
        pdf_report_path: Optional[str] = None
    ) -> bool:
        """Sync version of set_project_completed for Celery workers"""
        updates = {
            "status": JobStatus.COMPLETED,
            "result": result
        }
        
        if pdf_report_path:
            updates["pdf_report_path"] = pdf_report_path
        
        success = JobService.sync_update_project(project_id, updates)
        
        # Cleanup uploaded file after successful completion
        if success:
            try:
                from services.storage import storage_service
                storage_service.cleanup(project_id)
                logger.info(f"Cleaned up files for completed project {project_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup files for project {project_id}: {e}")
        
        return success
    
    @staticmethod
    def sync_set_project_failed(
        project_id: str,
        error: str
    ) -> bool:
        """Sync version of set_project_failed for Celery workers"""
        success = JobService.sync_update_project(
            project_id,
            {"status": JobStatus.FAILED, "error": error}
        )
        
        # Cleanup uploaded file after failure (disabled in debug mode)
        if success and CLEANUP_ON_FAILURE:
            try:
                from services.storage import storage_service
                storage_service.cleanup(project_id)
                logger.info(f"Cleaned up files for failed project {project_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup files for project {project_id}: {e}")
        elif success and not CLEANUP_ON_FAILURE:
            logger.warning(f"⚠️ CLEANUP DISABLED: Files preserved for failed project {project_id} for debugging")
        
        return success
    
    # Legacy assumption handling methods removed - all parameters now collected upfront

# Global instance for easy access
job_service = JobService()