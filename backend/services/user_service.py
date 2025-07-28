from typing import Optional
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import User, EmailToken
from database import get_async_session
from app.config import DEBUG, DEV_VERIFIED_EMAILS
import secrets
from datetime import datetime, timezone, timedelta
import hashlib

class UserService:
    """PostgreSQL-backed user service replacing InMemoryUserStore"""
    
    @staticmethod
    async def get_or_create_user(email: str, session: AsyncSession) -> User:
        """Get existing user or create new one"""
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        user = result.scalars().first()
        
        if not user:
            user = User(email=email)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
    
    @staticmethod
    async def get_user_by_email(email: str, session: AsyncSession) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        return result.scalars().first()
    
    @staticmethod
    async def mark_free_report_used(email: str, session: AsyncSession) -> bool:
        """Mark that user has used their free report"""
        user = await UserService.get_user_by_email(email, session)
        if user:
            user.free_report_used = True
            session.add(user)
            await session.commit()
            return True
        return False
    
    @staticmethod
    async def can_use_free_report(email: str, session: AsyncSession) -> bool:
        """Check if user can still use free report"""
        user = await UserService.get_user_by_email(email, session)
        if not user:
            return True  # New users get free report
        return not user.free_report_used
    
    @staticmethod
    async def has_active_subscription(email: str, session: AsyncSession) -> bool:
        """Check if user has active subscription"""
        user = await UserService.get_user_by_email(email, session)
        if not user:
            return False
        return user.active_subscription
    
    @staticmethod
    async def activate_subscription(email: str, stripe_customer_id: str, session: AsyncSession) -> bool:
        """Activate user subscription"""
        user = await UserService.get_or_create_user(email, session)
        user.stripe_customer_id = stripe_customer_id
        user.active_subscription = True
        session.add(user)
        await session.commit()
        return True
    
    @staticmethod
    async def deactivate_subscription(email: str, session: AsyncSession) -> bool:
        """Deactivate user subscription"""
        user = await UserService.get_user_by_email(email, session)
        if user:
            user.active_subscription = False
            session.add(user)
            await session.commit()
            return True
        return False
    
    @staticmethod
    async def is_email_verified(email: str, session: AsyncSession) -> bool:
        """Check if user's email is verified"""
        user = await UserService.get_user_by_email(email, session)
        if not user:
            return False
        return user.email_verified
    
    @staticmethod
    async def verify_email(email: str, session: AsyncSession) -> bool:
        """Mark email as verified"""
        user = await UserService.get_or_create_user(email, session)
        user.email_verified = True
        session.add(user)
        await session.commit()
        return True
    
    @staticmethod
    async def create_email_token(email: str, session: AsyncSession) -> str:
        """Create email verification token"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # Ensure user exists
        await UserService.get_or_create_user(email, session)
        
        # Delete any existing tokens for this email
        statement = select(EmailToken).where(EmailToken.user_email == email)
        result = await session.execute(statement)
        for existing_token in result.scalars():
            await session.delete(existing_token)
        
        # Create new token
        email_token = EmailToken(
            token=token,
            user_email=email,
            expires_at=expires_at
        )
        session.add(email_token)
        await session.commit()
        
        return token
    
    @staticmethod
    async def verify_email_token(token: str, session: AsyncSession) -> Optional[str]:
        """Verify email token and return email if valid"""
        statement = select(EmailToken).where(EmailToken.token == token)
        result = await session.execute(statement)
        email_token = result.scalars().first()
        
        if not email_token:
            return None
        
        # Check if token is expired
        if email_token.expires_at < datetime.now(timezone.utc):
            await session.delete(email_token)
            await session.commit()
            return None
        
        # Token is valid - verify the email and delete the token
        email = email_token.user_email
        await UserService.verify_email(email, session)
        
        # Delete the used token
        await session.delete(email_token)
        await session.commit()
        
        return email
    
    @staticmethod
    async def cleanup_expired_tokens(session: AsyncSession) -> int:
        """Clean up expired email tokens"""
        statement = select(EmailToken).where(EmailToken.expires_at < datetime.now(timezone.utc))
        result = await session.execute(statement)
        expired_tokens = result.scalars().all()
        
        count = 0
        for token in expired_tokens:
            await session.delete(token)
            count += 1
        
        if count > 0:
            await session.commit()
        
        return count
    
    @staticmethod
    async def require_verified(email: str, session: AsyncSession) -> None:
        """Require email to be verified, with dev bypass for whitelisted emails"""
        # Dev shortcut - bypass if DEBUG mode OR email in whitelist
        if DEBUG or email in DEV_VERIFIED_EMAILS:
            return
        
        # Regular verification check
        if not await UserService.is_email_verified(email, session):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Email verification required. Check your email for verification link.",
                headers={"X-Verification-Required": "true"}
            )

# Global instance for easy access
user_service = UserService()