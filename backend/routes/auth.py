from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.user_service import user_service
from core.email import email_service
from pydantic import BaseModel, EmailStr
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class SendVerificationRequest(BaseModel):
    email: EmailStr

class VerificationResponse(BaseModel):
    message: str
    email: str

@router.post("/send-verification")
async def send_verification_email(
    request: SendVerificationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Send email verification link to user"""
    try:
        # Check if email is already verified
        if await user_service.is_email_verified(request.email, session):
            return JSONResponse({
                "message": "Email is already verified",
                "already_verified": True
            })
        
        # Create verification token
        token = await user_service.create_email_token(request.email, session)
        
        # Send verification email
        success = await email_service.send_verification_email(request.email, token)
        
        if success:
            return JSONResponse({
                "message": "Verification email sent successfully",
                "email": request.email
            })
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send verification email"
            )
    
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/verify")
async def verify_email(
    token: str = Query(..., description="Email verification token"),
    session: AsyncSession = Depends(get_async_session)
):
    """Verify email using token and redirect to frontend"""
    try:
        # Verify the token
        email = await user_service.verify_email_token(token, session)
        
        if not email:
            # Invalid or expired token - redirect to error page
            frontend_url = "http://localhost:3000"  # Should come from env
            return RedirectResponse(
                url=f"{frontend_url}/?verification=failed",
                status_code=302
            )
        
        # Success - redirect to success page
        frontend_url = "http://localhost:3000"  # Should come from env
        return RedirectResponse(
            url=f"{frontend_url}/?verification=success&email={email}",
            status_code=302
        )
    
    except Exception as e:
        logger.error(f"Error verifying email token: {str(e)}")
        frontend_url = "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/?verification=error",
            status_code=302
        )

@router.get("/verify-status/{email}")
async def check_verification_status(
    email: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Check if an email is verified"""
    try:
        is_verified = await user_service.is_email_verified(email, session)
        return JSONResponse({
            "email": email,
            "verified": is_verified
        })
    
    except Exception as e:
        logger.error(f"Error checking verification status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    session: AsyncSession = Depends(get_async_session)
):
    """Manual endpoint to cleanup expired tokens (usually called by cron job)"""
    try:
        count = await user_service.cleanup_expired_tokens(session)
        return JSONResponse({
            "message": f"Cleaned up {count} expired tokens"
        })
    
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )