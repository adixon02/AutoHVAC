from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from models.schemas import JobStatus
import logging

router = APIRouter()

@router.post("/force-migration")
async def force_migration():
    """Force database migration for debugging"""
    try:
        import logging
        import subprocess
        
        logging.info("🔧 Force running database migration...")
        
        # Run Alembic migration
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/opt/render/project/src/backend" if "/opt/render" in __file__ else "."
        )
        
        if result.returncode == 0:
            logging.info("✅ Alembic migration successful")
            return {
                "status": "success",
                "message": "Migration completed successfully",
                "output": result.stdout
            }
        else:
            logging.error(f"❌ Alembic migration failed: {result.stderr}")
            return {
                "status": "failed",
                "message": f"Migration failed: {result.stderr}",
                "output": result.stdout
            }
            
    except Exception as e:
        logging.exception(f"Migration error: {e}")
        return {
            "status": "error", 
            "message": str(e)
        }

@router.post("/debug-create-project")
async def debug_create_project(
    session: AsyncSession = Depends(get_async_session)
):
    """Emergency debugging endpoint to test project creation"""
    import uuid
    import logging
    from services.job_service import job_service
    
    test_email = "debug@test.com"
    test_project_id = str(uuid.uuid4())
    
    try:
        logging.info(f"🧪 DEBUG: Starting test project creation for {test_email}")
        
        # Test user creation first
        from services.user_service import user_service
        user = await user_service.get_or_create_user(test_email, session)
        logging.info(f"🧪 DEBUG: User created/found: {user.email}, verified: {user.email_verified}")
        
        # Test project creation
        project_id = await job_service.create_project_with_assumptions(
            user_email=test_email,
            project_label="Debug Test Project",
            filename="debug.pdf",
            file_size=1024,
            duct_config="ducted_attic",
            heating_fuel="gas",
            session=session
        )
        
        logging.info(f"🧪 DEBUG: Project created successfully: {project_id}")
        
        # Test immediate retrieval
        project = await job_service.get_project(project_id, session)
        if project:
            logging.info(f"🧪 DEBUG: Project retrieved successfully: {project.id}, status: {project.status}")
            return {
                "status": "success",
                "message": "Project creation and retrieval test passed",
                "project_id": project_id,
                "project_status": project.status.value,
                "user_email": project.user_email
            }
        else:
            logging.error(f"🧪 DEBUG: Project creation succeeded but retrieval failed for {project_id}")
            return {
                "status": "error",
                "message": f"Project created but not retrievable: {project_id}"
            }
            
    except Exception as e:
        logging.exception(f"🧪 DEBUG: Project creation test failed: {e}")
        return {
            "status": "error",
            "message": f"Debug test failed: {str(e)}",
            "error_type": type(e).__name__
        }

@router.get("/debug-db-health")
async def debug_db_health(
    session: AsyncSession = Depends(get_async_session)
):
    """Emergency database health check"""
    import logging
    from sqlmodel import select
    from models.db_models import User, Project
    
    try:
        logging.info("🧪 DEBUG: Starting database health check")
        
        # Test basic database connection
        result = await session.execute(select(User).limit(1))
        users = result.scalars().all()
        user_count = len(users)
        
        result = await session.execute(select(Project).limit(1)) 
        projects = result.scalars().all()
        project_count = len(projects)
        
        # Test table structure
        logging.info(f"🧪 DEBUG: Found {user_count} users, {project_count} projects")
        
        return {
            "status": "success",
            "message": "Database connection healthy",
            "users_found": user_count,
            "projects_found": project_count,
            "database_accessible": True
        }
        
    except Exception as e:
        logging.exception(f"🧪 DEBUG: Database health check failed: {e}")
        return {
            "status": "error", 
            "message": f"Database health check failed: {str(e)}",
            "error_type": type(e).__name__,
            "database_accessible": False
        }


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        logging.info(f"🔍 Fetching job status for job_id: {job_id}")
        project = await job_service.get_project(job_id, session)
        
        if not project:
            logging.warning(f"❌ Job not found in database: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        logging.info(f"✅ Successfully retrieved job status for {job_id}: status={project.status.value}, error={project.error}")
        
        # Return normal 200 response with job status (including failed jobs)
        return JobStatus(
            job_id=job_id,
            status=project.status.value,
            result=project.result,
            error=project.error,
            assumptions_collected=project.assumptions_collected
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as exc:
        logging.exception(f"Unexpected error fetching job status for {job_id}: {type(exc).__name__}: {str(exc)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(exc)}"
        )