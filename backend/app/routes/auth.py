import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

# Simple user storage (in production, use a proper database)
USERS_FILE = "/tmp/autohvac_users.json"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

def load_users():
    """Load users from file"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading users: {e}")
    return {}

def save_users(users):
    """Save users to file"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving users: {e}")

def hash_password(password: str) -> str:
    """Hash a password using SHA256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, hash_part = hashed_password.split(':')
        test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return test_hash == hash_part
    except:
        return False

def create_access_token(user_id: str) -> str:
    """Create a simple access token"""
    return f"token_{user_id}_{secrets.token_hex(16)}"

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password
    """
    try:
        users = load_users()
        user_key = request.email.lower()
        
        if user_key not in users:
            logger.info(f"Login failed: User not found - {request.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = users[user_key]
        
        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            logger.info(f"Login failed: Invalid password - {request.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create access token
        access_token = create_access_token(user["id"])
        
        # Update last login
        user["last_login"] = datetime.utcnow().isoformat()
        save_users(users)
        
        logger.info(f"Login successful: {request.email}")
        
        return LoginResponse(
            access_token=access_token,
            user={
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name"),
                "image": user.get("image"),
                "emailVerified": user.get("email_verified", True),
                "freeReportUsed": user.get("free_report_used", False),
                "stripeCustomerId": user.get("stripe_customer_id"),
                "createdAt": user.get("created_at"),
                "lastLogin": user.get("last_login")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get("/user/{user_id}")
async def get_user(user_id: str):
    """
    Get user by ID (for verification)
    """
    try:
        users = load_users()
        
        # Find user by ID
        for email, user in users.items():
            if user["id"] == user_id:
                return {
                    "id": user["id"],
                    "email": user["email"],
                    "name": user.get("name"),
                    "emailVerified": user.get("email_verified", True),
                    "freeReportUsed": user.get("free_report_used", False),
                    "stripeCustomerId": user.get("stripe_customer_id")
                }
        
        raise HTTPException(status_code=404, detail="User not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")

def create_user_in_auth_system(email: str, password: str, user_id: str) -> bool:
    """
    Create user in the auth system (called by leads.py)
    """
    try:
        users = load_users()
        user_key = email.lower()
        
        if user_key in users:
            logger.info(f"User already exists in auth system: {email}")
            return True
        
        # Create user record
        user_data = {
            "id": user_id,
            "email": email.lower(),
            "password_hash": hash_password(password),
            "name": None,
            "image": None,
            "email_verified": True,  # Auto-verify for converted leads
            "free_report_used": True,  # They used their free report to convert
            "stripe_customer_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
        
        users[user_key] = user_data
        save_users(users)
        
        logger.info(f"User created in auth system: {email} -> {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating user in auth system: {e}")
        return False