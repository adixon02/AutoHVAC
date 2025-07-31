from typing import Optional
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession
from models.db_models import User, EmailToken
from database import get_async_session
from app.config import DEBUG, DEV_VERIFIED_EMAILS
import secrets
from datetime import datetime, timezone, timedelta
import hashlib
import re

class UserService:
    """PostgreSQL-backed user service replacing InMemoryUserStore"""
    
    # Spam email patterns and domains
    SPAM_DOMAINS = [
        'mailinator.com', 'guerrillamail.com', '10minutemail.com',
        'throwawaymail.com', 'yopmail.com', 'trashmail.com',
        'tempmail.com', 'disposablemail.com', 'fakeinbox.com',
        'temp-mail.org', 'tempmailo.com', 'sharklasers.com'
    ]
    
    SPAM_PATTERNS = [
        r'^test@test\.',
        r'^asdf@asdf\.',
        r'^aaa+@',
        r'^123+@',
        r'^xxx+@',
        r'^fuck',
        r'^shit',
        r'^spam',
        r'^fake@fake\.',
        r'^user@user\.',
        r'^email@email\.',
        r'^abc+@',
        r'^qwerty@'
    ]
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Enhanced email validation to prevent spam"""
        # Basic regex pattern for email validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        if not email_pattern.match(email):
            return False
        
        email_lower = email.lower()
        
        # Check against spam domains
        domain = email_lower.split('@')[1] if '@' in email_lower else ''
        if domain in UserService.SPAM_DOMAINS:
            return False
        
        # Check against spam patterns
        for pattern in UserService.SPAM_PATTERNS:
            if re.search(pattern, email_lower):
                return False
        
        return True
    
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
    async def can_upload_new_report(email: str, session: AsyncSession) -> bool:
        """Check if user can upload a new report (either has free report or active subscription)"""
        user = await UserService.get_user_by_email(email, session)
        if not user:
            return True  # New users can upload their first report
        
        # Can upload if they haven't used free report OR have active subscription
        return not user.free_report_used or user.active_subscription
    
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
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
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
        if email_token.expires_at < datetime.utcnow():
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
        statement = select(EmailToken).where(EmailToken.expires_at < datetime.utcnow())
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
    def sync_check_is_first_report(email: str, session: SyncSession) -> bool:
        """Synchronous version to check if this is user's first report (for Celery)"""
        statement = select(User).where(User.email == email)
        result = session.execute(statement)
        user = result.scalars().first()
        
        if not user:
            return True  # New user, definitely first report
        
        # If free_report_used is False, this is their first report
        return not user.free_report_used
    
    @staticmethod
    async def check_free_report_eligibility(email: str, session: AsyncSession) -> dict:
        """
        Comprehensive check for free report eligibility
        Returns detailed status about the user's eligibility
        """
        user = await UserService.get_user_by_email(email, session)
        
        if not user:
            # New user - eligible for free report
            return {
                "eligible": True,
                "reason": "new_user",
                "email_exists": False,
                "email_verified": False,
                "free_report_used": False,
                "has_subscription": False
            }
        
        # Existing user - check their status
        return {
            "eligible": not user.free_report_used,
            "reason": "existing_user",
            "email_exists": True,
            "email_verified": user.email_verified,
            "free_report_used": user.free_report_used,
            "has_subscription": user.active_subscription,
            "user_created_at": user.created_at.isoformat()
        }
    
    @staticmethod
    async def require_verified(email: str, session: AsyncSession) -> None:
        """DEPRECATED: Email verification no longer required for free users"""
        # This method is kept for backward compatibility but does nothing
        # Email verification is completely removed from the flow
        return

# Global instance for easy access
user_service = UserService()