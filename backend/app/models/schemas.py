from pydantic import BaseModel, EmailStr
from typing import Optional

class SubscribeRequest(BaseModel):
    """Request model for creating a subscription"""
    email: EmailStr

class SubscribeResponse(BaseModel):
    """Response model for subscription creation"""
    checkout_url: str

class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    """Response model for user login"""
    success: bool
    user_email: Optional[str] = None
    message: Optional[str] = None

class CheckoutSessionResponse(BaseModel):
    """Response model for checkout session creation"""
    success: bool
    checkout_url: str

class BillingPortalResponse(BaseModel):
    """Response model for billing portal session"""
    success: bool
    portal_url: str

class SubscriptionStatusResponse(BaseModel):
    """Response model for subscription status"""
    has_active_subscription: bool
    free_report_used: bool
    stripe_customer_id: Optional[str] = None
    email_verified: bool