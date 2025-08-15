from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime
import uuid
import logging

# Import auth system helper
from .auth import create_user_in_auth_system

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["leads"])


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    status: Literal["new", "lead", "user"]
    free_report_used: bool
    has_account: bool
    has_password: bool = False
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
) -> CheckEmailResponse:
    """Check if an email is new, a lead, or an existing user"""
    try:
        # For now, simplified logic since we're building the new flow
        # In the new flow, we just capture the email and process
        # Real implementation would check database for user/lead status
        
        # For MVP: treat all emails as "new" to allow free reports
        # This enables the new conversion flow
        return CheckEmailResponse(
            status="new",
            free_report_used=False,
            has_account=False,
            has_password=False,
            has_subscription=False
        )
        
    except Exception as e:
        logger.error(f"Error checking email status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check email status")


@router.post("/capture")
async def capture_lead(
    request: CaptureLeadRequest,
) -> CaptureLeadResponse:
    """Capture a new lead (email-only user getting their first free report)"""
    try:
        # Generate lead ID for tracking
        lead_id = str(uuid.uuid4())
        
        # Log the lead capture
        logger.info(f"Lead captured: {request.email} (project: {request.project_id})")
        
        # In production, you'd save this to database
        # For now, just return success to unblock the frontend
        
        return CaptureLeadResponse(
            success=True,
            lead_id=lead_id
        )
        
    except Exception as e:
        logger.error(f"Error capturing lead: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to capture lead")


@router.post("/convert")
async def convert_lead_to_user(
    request: ConvertLeadRequest,
) -> ConvertLeadResponse:
    """Convert a lead to a full user account with password"""
    try:
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Create user in auth system
        success = create_user_in_auth_system(
            email=request.email,
            password=request.password,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create user account")
        
        logger.info(f"Lead converted to user: {request.email} -> {user_id}")
        
        return ConvertLeadResponse(
            user_id=user_id,
            email=request.email,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting lead to user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to convert lead to user")