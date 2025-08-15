from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import json

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


class JobStatus(str, Enum):
    """Job status enum for clear state management"""
    CREATED = "created"           # Job created, not started
    QUEUED = "queued"            # Queued for processing
    PROCESSING = "processing"     # Currently being processed
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"            # Failed with error
    CANCELLED = "cancelled"       # User cancelled
    PENDING_UPGRADE = "pending_upgrade"  # Waiting for user to upgrade
    EXPIRED = "expired"          # Job expired before processing


class JobPriority(str, Enum):
    """Job priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobModel(SQLModel, table=True):
    """
    Comprehensive job storage model for HVAC processing pipeline
    
    Features:
    - Full audit trail with state transitions
    - JSON storage for flexible data structures
    - User association for paywall enforcement
    - Priority and retry management
    - Performance monitoring
    """
    __tablename__ = "jobs"
    
    # Primary Identity
    id: str = Field(primary_key=True, description="UUID job identifier")
    user_email: str = Field(foreign_key="users.email", index=True, max_length=255)
    
    # Job Metadata
    filename: str = Field(max_length=500, description="Original uploaded filename")
    project_label: Optional[str] = Field(default=None, max_length=500)
    zip_code: str = Field(max_length=10, index=True)
    
    # State Management
    status: JobStatus = Field(default=JobStatus.CREATED, index=True)
    priority: JobPriority = Field(default=JobPriority.NORMAL)
    progress: int = Field(default=0, description="Progress percentage 0-100")
    
    # Processing Data (JSON fields for flexibility)
    user_inputs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    result_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    error_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # File Storage
    s3_upload_path: Optional[str] = Field(default=None, max_length=1000)
    s3_result_path: Optional[str] = Field(default=None, max_length=1000)
    
    # Timing & Performance
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="When job expires if not processed")
    
    # Processing Stats
    processing_time_seconds: Optional[float] = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Business Logic
    is_free_report: bool = Field(default=False, description="Was this the user's free report?")
    requires_upgrade: bool = Field(default=False, description="User needs to upgrade to process")
    
    # Audit Trail
    status_history: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    
    def update_status(self, new_status: JobStatus, message: Optional[str] = None, metadata: Optional[Dict] = None) -> None:
        """Update job status with full audit trail"""
        old_status = self.status
        
        # Add to audit trail
        status_change = {
            "from_status": old_status,
            "to_status": new_status,
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "metadata": metadata or {}
        }
        
        if not self.status_history:
            self.status_history = []
        self.status_history.append(status_change)
        
        # Update status and timestamp
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Set specific timestamps
        if new_status == JobStatus.PROCESSING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()
            if self.started_at:
                self.processing_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry counter"""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if job has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if self.processing_time_seconds:
            return self.processing_time_seconds
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def add_processing_metadata(self, key: str, value: Any) -> None:
        """Add metadata to processing_metadata"""
        if not self.processing_metadata:
            self.processing_metadata = {}
        self.processing_metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        return {
            "job_id": self.id,
            "status": self.status,
            "progress": self.progress,
            "filename": self.filename,
            "project_label": self.project_label,
            "zip_code": self.zip_code,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.get_processing_duration(),
            "result": self.result_data,
            "error": self.error_data.get("message") if self.error_data else None,
            "requires_upgrade": self.requires_upgrade,
            "retry_count": self.retry_count,
            "can_retry": self.can_retry()
        }


class JobLogEntry(SQLModel, table=True):
    """
    Detailed logging for job processing steps
    Separate table for high-volume log data
    """
    __tablename__ = "job_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    level: str = Field(max_length=20, description="DEBUG, INFO, WARNING, ERROR")
    stage: str = Field(max_length=100, description="Pipeline stage")
    message: str = Field(max_length=2000)
    log_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    def __repr__(self) -> str:
        return f"<JobLog {self.job_id} [{self.level}] {self.stage}: {self.message[:50]}...>"