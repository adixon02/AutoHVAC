from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

class SubscriptionStatus(str, Enum):
    """Subscription status enum for clear state management"""
    NONE = "none"           # Never had subscription
    ACTIVE = "active"       # Currently paying
    CANCELED = "canceled"   # Subscription canceled but still active until period end
    EXPIRED = "expired"     # Subscription expired/failed payment
    TRIALING = "trialing"   # In trial period

class UserModel(SQLModel, table=True):
    """
    Core user model for AutoHVAC SaaS
    Tracks freemium usage and subscription state
    """
    __tablename__ = "users"
    
    # Identity
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255, description="User's email address")
    name: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, max_length=255)  # Hashed password
    email_verified: bool = Field(default=False)
    signup_method: Optional[str] = Field(default="email_only", max_length=50)  # "password" or "email_only"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Freemium Tracking - Core Business Logic
    free_report_used: bool = Field(default=False, description="Has user consumed their free report?")
    free_report_used_at: Optional[datetime] = Field(default=None, description="When was free report used?")
    total_reports_generated: int = Field(default=0, description="Total reports generated (free + paid)")
    
    # Anti-Fraud: Device Fingerprinting
    device_fingerprint: Optional[str] = Field(default=None, max_length=255, description="Browser/device fingerprint hash")
    ip_address: Optional[str] = Field(default=None, max_length=45, description="IP address at signup")  # IPv6 = 45 chars max
    
    # Subscription Management  
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255, description="Stripe customer ID")
    active_subscription: bool = Field(default=False)  # Keep for backward compatibility
    subscription_status: SubscriptionStatus = Field(default=SubscriptionStatus.NONE)
    stripe_subscription_id: Optional[str] = Field(default=None, description="Current Stripe subscription ID")
    subscription_started_at: Optional[datetime] = Field(default=None)
    subscription_expires_at: Optional[datetime] = Field(default=None, description="When current billing period ends")
    
    # Business Intelligence
    last_login_at: Optional[datetime] = Field(default=None)
    last_upload_attempt_at: Optional[datetime] = Field(default=None)
    conversion_source: Optional[str] = Field(default=None, description="How did they find us?")
    
    # Rate Limiting
    uploads_today: int = Field(default=0, description="Uploads attempted today (reset daily)")
    last_upload_date: Optional[datetime] = Field(default=None, description="Last upload date for daily reset")
    
    def can_upload_new_report(self) -> bool:
        """
        Core business logic: Can this user upload a new report?
        Compatible with archive UserService logic
        """
        # Paid subscribers get unlimited uploads (check both fields for compatibility)
        if self.subscription_status == SubscriptionStatus.ACTIVE or self.active_subscription:
            return True
            
        # Free users get exactly 1 report
        if not self.free_report_used:
            return True
            
        # Everyone else needs to pay
        return False
    
    def is_paying_customer(self) -> bool:
        """Is this user currently paying?"""
        return self.subscription_status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING] or self.active_subscription
    
    def mark_free_report_used(self) -> None:
        """Mark the free report as consumed"""
        self.free_report_used = True
        self.free_report_used_at = datetime.utcnow()
        self.total_reports_generated += 1
        self.updated_at = datetime.utcnow()
    
    def mark_paid_report_generated(self) -> None:
        """Track paid report generation"""
        self.total_reports_generated += 1
        self.updated_at = datetime.utcnow()
    
    def update_last_activity(self) -> None:
        """Update activity timestamps"""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def reset_daily_limits_if_needed(self) -> None:
        """Reset daily upload counter if new day"""
        today = datetime.utcnow().date()
        if not self.last_upload_date or self.last_upload_date.date() != today:
            self.uploads_today = 0
            self.last_upload_date = datetime.utcnow()
    
    def can_upload_today(self, daily_limit: int = 10) -> bool:
        """Check if user is under daily upload limit"""
        self.reset_daily_limits_if_needed()
        return self.uploads_today < daily_limit
    
    def record_upload_attempt(self) -> None:
        """Record an upload attempt for rate limiting"""
        self.reset_daily_limits_if_needed()
        self.uploads_today += 1
        self.last_upload_attempt_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class EmailToken(SQLModel, table=True):
    """Email verification tokens"""
    __tablename__ = "email_tokens"
    
    token: str = Field(primary_key=True, max_length=255)
    user_email: str = Field(foreign_key="users.email", index=True, max_length=255)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Alias for backward compatibility with archive UserService
User = UserModel