from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_async_session
from services.user_service import user_service
from core.email import email_service
from models.db_models import User
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import logging
import os
import jwt
import bcrypt
import secrets

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

class SendVerificationRequest(BaseModel):
    email: EmailStr

class VerificationResponse(BaseModel):
    message: str
    email: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None  # Optional for email-only login

class SignupRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    name: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

def create_jwt_token(user_id: int, email: str, expires_delta: timedelta = None) -> str:
    """Create a JWT token for a user"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    user_id = int(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Login endpoint - supports both password and email-only authentication
    Used by NextAuth as the credentials provider
    """
    email = request.email.lower()
    
    # Get or create user
    user = await user_service.get_or_create_user(email, session)
    
    # If password provided, verify it
    if request.password:
        if not user.password:
            # User exists but no password set
            raise HTTPException(
                status_code=401,
                detail="Please use email-only login or set a password first"
            )
        # Verify password
        if not bcrypt.checkpw(
            request.password.encode('utf-8'),
            user.password.encode('utf-8')
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
    
    # Create JWT token
    access_token = create_jwt_token(user.id, user.email)
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": getattr(user, 'name', None),
            "image": getattr(user, 'image', None),
            "emailVerified": user.email_verified,
            "freeReportUsed": user.free_report_used,
            "stripeCustomerId": user.stripe_customer_id,
            "hasActiveSubscription": user.active_subscription
        }
    )

@router.post("/signup", response_model=AuthResponse)
async def signup(
    request: SignupRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Signup endpoint - creates a new user account
    """
    email = request.email.lower()
    
    # Check if user already exists
    result = await session.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # If user exists but no password, allow setting password
        if not existing_user.password and request.password:
            hashed_password = bcrypt.hashpw(
                request.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            existing_user.password = hashed_password
            existing_user.signup_method = "password"
            if request.name:
                existing_user.name = request.name
            await session.commit()
            
            # Create JWT token
            access_token = create_jwt_token(existing_user.id, existing_user.email)
            
            return AuthResponse(
                access_token=access_token,
                user={
                    "id": str(existing_user.id),
                    "email": existing_user.email,
                    "name": getattr(existing_user, 'name', None),
                    "image": getattr(existing_user, 'image', None),
                    "emailVerified": existing_user.email_verified,
                    "freeReportUsed": existing_user.free_report_used,
                    "stripeCustomerId": existing_user.stripe_customer_id,
                    "hasActiveSubscription": existing_user.active_subscription
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="User already exists with this email"
            )
    
    # Hash password if provided
    hashed_password = None
    if request.password:
        hashed_password = bcrypt.hashpw(
            request.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    
    # Create new user
    user = User(
        email=email,
        name=request.name if request.name else None,
        password=hashed_password,
        email_verified=False,
        free_report_used=False,
        active_subscription=False,
        signup_method="password" if request.password else "email_only",
        created_at=datetime.utcnow()
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Create JWT token
    access_token = create_jwt_token(user.id, user.email)
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": getattr(user, 'name', None),
            "image": getattr(user, 'image', None),
            "emailVerified": user.email_verified,
            "freeReportUsed": user.free_report_used,
            "stripeCustomerId": user.stripe_customer_id,
            "hasActiveSubscription": user.active_subscription
        }
    )

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": getattr(current_user, 'name', None),
        "image": getattr(current_user, 'image', None),
        "emailVerified": current_user.email_verified,
        "freeReportUsed": current_user.free_report_used,
        "stripeCustomerId": current_user.stripe_customer_id,
        "hasActiveSubscription": current_user.active_subscription
    }

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
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return RedirectResponse(
                url=f"{frontend_url}/?verification=failed",
                status_code=302
            )
        
        # Success - redirect to success page
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(
            url=f"{frontend_url}/?verification=success&email={email}",
            status_code=302
        )
    
    except Exception as e:
        logger.error(f"Error verifying email token: {str(e)}")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
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