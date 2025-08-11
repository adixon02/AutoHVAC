from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from database import get_db
from models.db_models import User, Project, JobStatus
import bcrypt
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["leads"])


class Lead(BaseModel):
    """Lead model for database operations"""
    id: str
    email: str
    first_report_date: datetime
    project_id: Optional[str]
    marketing_consent: bool
    converted_to_user_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    status: Literal["new", "lead", "user"]
    free_report_used: bool
    has_account: bool
    has_subscription: bool = False


class CaptureLeadRequest(BaseModel):
    email: EmailStr
    marketing_consent: bool = False
    project_id: Optional[str] = None


class CaptureLeadResponse(BaseModel):
    success: bool
    lead_id: str


class ConvertLeadRequest(BaseModel):
    email: EmailStr
    password: str


class ConvertLeadResponse(BaseModel):
    user_id: str
    email: str
    success: bool


@router.post("/check")
async def check_email_status(
    request: CheckEmailRequest,
    db: Session = Depends(get_db)
) -> CheckEmailResponse:
    """Check if an email is new, a lead, or an existing user"""
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if user:
            # Check for active subscription (simplified - actual subscription check would use Stripe API)
            has_subscription = user.active_subscription if hasattr(user, 'active_subscription') else False
            
            return CheckEmailResponse(
                status="user",
                free_report_used=user.free_report_used,
                has_account=True,
                has_subscription=has_subscription
            )
        
        # Check if lead exists (using project table for now since Lead table might not be migrated yet)
        lead_project = db.query(Project).filter(
            Project.lead_email == request.email
        ).first()
        
        if lead_project:
            return CheckEmailResponse(
                status="lead",
                free_report_used=True,
                has_account=False,
                has_subscription=False
            )
        
        # New email
        return CheckEmailResponse(
            status="new",
            free_report_used=False,
            has_account=False,
            has_subscription=False
        )
        
    except Exception as e:
        logger.error(f"Error checking email status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check email status")


@router.post("/capture")
async def capture_lead(
    request: CaptureLeadRequest,
    db: Session = Depends(get_db)
) -> CaptureLeadResponse:
    """Capture a new lead (email-only user getting their first free report)"""
    try:
        # Check if email already exists as user or lead
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered as user")
        
        # For now, we'll track leads via the Project table with lead_email
        # (Since the Lead table might not be migrated to the backend database yet)
        # In production, you'd create a proper Lead record here
        
        lead_id = str(uuid.uuid4())
        
        # Log the lead capture
        logger.info(f"Lead captured: {request.email} (project: {request.project_id})")
        
        return CaptureLeadResponse(
            success=True,
            lead_id=lead_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error capturing lead: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to capture lead")


@router.post("/convert")
async def convert_lead_to_user(
    request: ConvertLeadRequest,
    db: Session = Depends(get_db)
) -> ConvertLeadResponse:
    """Convert a lead to a full user account with password"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            if existing_user.password:
                raise HTTPException(status_code=400, detail="Account already exists with password")
            
            # Update existing email-only user with password
            hashed_password = bcrypt.hashpw(
                request.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            existing_user.password = hashed_password
            existing_user.signup_method = "password"
            db.commit()
            
            return ConvertLeadResponse(
                user_id=existing_user.id,
                email=existing_user.email,
                success=True
            )
        
        # Create new user from lead
        hashed_password = bcrypt.hashpw(
            request.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        new_user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            password=hashed_password,
            signup_method="password",
            free_report_used=True,  # They already used their free report as a lead
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        
        # Transfer any lead projects to the new user
        lead_projects = db.query(Project).filter(
            Project.lead_email == request.email
        ).all()
        
        for project in lead_projects:
            project.user_id = new_user.id
            project.lead_email = None
            project.claimed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Lead converted to user: {request.email} -> {new_user.id}")
        
        return ConvertLeadResponse(
            user_id=new_user.id,
            email=new_user.email,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting lead to user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to convert lead to user")