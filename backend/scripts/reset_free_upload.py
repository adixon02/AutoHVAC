#!/usr/bin/env python3
"""
Utility script to reset the free upload flag for testing the paywall flow.

Usage:
    python scripts/reset_free_upload.py <email>
    
Example:
    python scripts/reset_free_upload.py test@example.com
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from models.db_models import User
from services.user_service import user_service
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/autohvac")


async def reset_free_upload(email: str):
    """Reset the free upload flag for a specific email"""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get user
        user = await user_service.get_user_by_email(email, session)
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        # Reset free report flag
        user.free_report_used = False
        session.add(user)
        await session.commit()
        
        print(f"✅ Reset free upload flag for {email}")
        print(f"   - Email verified: {user.email_verified}")
        print(f"   - Has subscription: {user.active_subscription}")
        print(f"   - Stripe customer ID: {user.stripe_customer_id or 'None'}")
        print(f"   - Created at: {user.created_at}")
        
        return True


async def check_user_status(email: str):
    """Check the current status of a user"""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get user
        user = await user_service.get_user_by_email(email, session)
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"\n📊 User Status for {email}:")
        print(f"   - Free report used: {user.free_report_used}")
        print(f"   - Email verified: {user.email_verified}")
        print(f"   - Has subscription: {user.active_subscription}")
        print(f"   - Stripe customer ID: {user.stripe_customer_id or 'None'}")
        print(f"   - Created at: {user.created_at}")
        
        # Check upload eligibility
        can_use_free = await user_service.can_use_free_report(email, session)
        can_upload = await user_service.can_upload_new_report(email, session)
        
        print(f"\n   - Can use free report: {can_use_free}")
        print(f"   - Can upload new report: {can_upload}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_free_upload.py <email> [--check-only]")
        print("\nExamples:")
        print("  python scripts/reset_free_upload.py test@example.com")
        print("  python scripts/reset_free_upload.py test@example.com --check-only")
        sys.exit(1)
    
    email = sys.argv[1]
    check_only = "--check-only" in sys.argv
    
    if check_only:
        print(f"Checking status for {email}...")
        asyncio.run(check_user_status(email))
    else:
        print(f"Resetting free upload flag for {email}...")
        asyncio.run(reset_free_upload(email))
        print("\nNew status:")
        asyncio.run(check_user_status(email))


if __name__ == "__main__":
    main()