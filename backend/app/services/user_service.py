from typing import Optional
from sqlmodel import Session, select
from app.models.user import User, UserModel, EmailToken
from app.database import get_session
import secrets
from datetime import datetime, timezone, timedelta
import hashlib
import re

class UserService:
    """Production-proven user service with paywall enforcement"""
    
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
    def get_or_create_user(email: str, session: Session) -> User:
        """Get existing user or create new one"""
        statement = select(User).where(User.email == email)
        result = session.exec(statement)
        user = result.first()
        
        if not user:
            user = User(email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
        
        return user
    
    @staticmethod
    def get_user_by_email(email: str, session: Session) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = session.exec(statement)
        return result.first()
    
    @staticmethod
    def mark_free_report_used(email: str, session: Session) -> bool:
        """Mark that user has used their free report"""
        user = UserService.get_user_by_email(email, session)
        if user:
            user.free_report_used = True
            user.mark_free_report_used()  # Uses the model method
            session.add(user)
            session.commit()
            return True
        return False
    
    @staticmethod
    def can_use_free_report(email: str, session: Session) -> bool:
        """Check if user can still use free report"""
        user = UserService.get_user_by_email(email, session)
        if not user:
            return True  # New users get free report
        return not user.free_report_used
    
    @staticmethod
    def can_upload_new_report(email: str, session: Session) -> bool:
        """
        CRITICAL PAYWALL ENFORCEMENT: Check if user can upload a new report
        This is the core business logic that prevents revenue leakage
        """
        user = UserService.get_user_by_email(email, session)
        if not user:
            return True  # New users can upload their first report
        
        # Use the model's proven business logic
        return user.can_upload_new_report()
    
    @staticmethod
    def has_active_subscription(email: str, session: Session) -> bool:
        """Check if user has active subscription"""
        user = UserService.get_user_by_email(email, session)
        if not user:
            return False
        # Check both fields for backward compatibility
        return user.active_subscription or user.is_paying_customer()
    
    @staticmethod
    def activate_subscription(email: str, stripe_customer_id: str, session: Session) -> bool:
        """Activate user subscription"""
        user = UserService.get_or_create_user(email, session)
        user.stripe_customer_id = stripe_customer_id
        user.active_subscription = True
        # Update the enum status as well
        from app.models.user import SubscriptionStatus
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.subscription_started_at = datetime.utcnow()
        session.add(user)
        session.commit()
        return True
    
    @staticmethod
    def deactivate_subscription(email: str, session: Session) -> bool:
        """Deactivate user subscription"""
        user = UserService.get_user_by_email(email, session)
        if user:
            user.active_subscription = False
            from app.models.user import SubscriptionStatus
            user.subscription_status = SubscriptionStatus.EXPIRED
            session.add(user)
            session.commit()
            return True
        return False
    
    @staticmethod
    def is_email_verified(email: str, session: Session) -> bool:
        """Check if user's email is verified"""
        user = UserService.get_user_by_email(email, session)
        if not user:
            return False
        return user.email_verified
    
    @staticmethod
    def verify_email(email: str, session: Session) -> bool:
        """Mark email as verified"""
        user = UserService.get_or_create_user(email, session)
        user.email_verified = True
        session.add(user)
        session.commit()
        return True
    
    @staticmethod
    def create_email_token(email: str, session: Session) -> str:
        """Create email verification token"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Ensure user exists
        UserService.get_or_create_user(email, session)
        
        # Delete any existing tokens for this email
        statement = select(EmailToken).where(EmailToken.user_email == email)
        result = session.exec(statement)
        for existing_token in result:
            session.delete(existing_token)
        
        # Create new token
        email_token = EmailToken(
            token=token,
            user_email=email,
            expires_at=expires_at
        )
        session.add(email_token)
        session.commit()
        
        return token
    
    @staticmethod
    def verify_email_token(token: str, session: Session) -> Optional[str]:
        """Verify email token and return email if valid"""
        statement = select(EmailToken).where(EmailToken.token == token)
        result = session.exec(statement)
        email_token = result.first()
        
        if not email_token:
            return None
        
        # Check if token is expired
        if email_token.expires_at < datetime.utcnow():
            session.delete(email_token)
            session.commit()
            return None
        
        # Token is valid - verify the email and delete the token
        email = email_token.user_email
        UserService.verify_email(email, session)
        
        # Delete the used token
        session.delete(email_token)
        session.commit()
        
        return email
    
    @staticmethod
    def cleanup_expired_tokens(session: Session) -> int:
        """Clean up expired email tokens"""
        statement = select(EmailToken).where(EmailToken.expires_at < datetime.utcnow())
        result = session.exec(statement)
        expired_tokens = result.all()
        
        count = 0
        for token in expired_tokens:
            session.delete(token)
            count += 1
        
        if count > 0:
            session.commit()
        
        return count
    
    @staticmethod
    def check_free_report_eligibility(email: str, session: Session) -> dict:
        """
        Comprehensive check for free report eligibility
        Returns detailed status about the user's eligibility
        """
        user = UserService.get_user_by_email(email, session)
        
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
            "has_subscription": user.is_paying_customer(),
            "user_created_at": user.created_at.isoformat()
        }


# Global instance for easy access
user_service = UserService()