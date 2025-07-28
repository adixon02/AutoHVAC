from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON, Integer, String
from typing import Optional, List, Any
from datetime import datetime, timezone
from pydantic import EmailStr
import uuid
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    email_verified: bool = Field(default=False)
    free_report_used: bool = Field(default=False)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255)
    active_subscription: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    projects: List["Project"] = Relationship(back_populates="user")
    email_tokens: List["EmailToken"] = Relationship(back_populates="user")

class EmailToken(SQLModel, table=True):
    __tablename__ = "email_tokens"
    
    token: str = Field(primary_key=True, max_length=255)
    user_email: str = Field(foreign_key="users.email", index=True, max_length=255)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="email_tokens")

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_email: str = Field(foreign_key="users.email", index=True, max_length=255)
    project_label: str = Field(max_length=255)
    filename: str = Field(max_length=255)
    file_size: Optional[int] = Field(default=None)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error: Optional[str] = Field(default=None)
    pdf_report_path: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Manual J assumptions
    duct_config: Optional[str] = Field(default=None)
    heating_fuel: Optional[str] = Field(default=None)
    assumptions_collected: bool = Field(default=False)
    
    # Parsed blueprint data
    parsed_schema_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Progress tracking (optional for backward compatibility)
    progress_percent: Optional[int] = Field(
        default=0,
        sa_column=Column(Integer, nullable=True, server_default="0")
    )
    current_stage: Optional[str] = Field(
        default="initializing",
        max_length=64,
        sa_column=Column(String(64), nullable=True, server_default="'initializing'")
    )
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="projects")

# Additional models for future features
class RateLimit(SQLModel, table=True):
    __tablename__ = "rate_limits"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True, max_length=255)
    endpoint: str = Field(max_length=100)
    count: int = Field(default=1)
    window_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime