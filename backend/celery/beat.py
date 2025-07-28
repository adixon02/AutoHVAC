import os
import asyncio
import stripe
import logging
from celery import Celery
from celery.schedules import crontab
from sqlmodel import select
from datetime import datetime, timezone
from database import get_async_session
from models.db_models import User
from services.user_service import user_service
from core.stripe_config import get_stripe_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery('autohvac_beat')

# Configure Celery
celery_app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'reconcile-stripe-subscriptions': {
            'task': 'celery.beat.reconcile_stripe_subscriptions',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
        },
        'cleanup-expired-tokens': {
            'task': 'celery.beat.cleanup_expired_tokens',
            'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM UTC
        },
    },
    task_routes={
        'celery.beat.*': {'queue': 'beat'},
    }
)

@celery_app.task(name='celery.beat.reconcile_stripe_subscriptions')
def reconcile_stripe_subscriptions():
    """
    Nightly job to reconcile subscription statuses with Stripe
    This ensures our database stays in sync with Stripe's records
    """
    try:
        logger.info("Starting Stripe subscription reconciliation")
        
        # Run the async reconciliation function
        asyncio.run(_reconcile_subscriptions_async())
        
        logger.info("Stripe subscription reconciliation completed successfully")
        return {"status": "success", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        logger.error(f"Error during Stripe subscription reconciliation: {str(e)}")
        return {"status": "error", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

@celery_app.task(name='celery.beat.cleanup_expired_tokens')
def cleanup_expired_tokens():
    """
    Daily job to clean up expired email verification tokens
    """
    try:
        logger.info("Starting expired token cleanup")
        
        # Run the async cleanup function
        count = asyncio.run(_cleanup_tokens_async())
        
        logger.info(f"Cleaned up {count} expired tokens")
        return {"status": "success", "tokens_cleaned": count, "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        logger.error(f"Error during token cleanup: {str(e)}")
        return {"status": "error", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

async def _reconcile_subscriptions_async():
    """Async function to reconcile subscriptions with Stripe"""
    stripe_client = get_stripe_client()
    reconciled_count = 0
    error_count = 0
    
    async with get_async_session() as session:
        # Get all users with stripe customer IDs
        statement = select(User).where(User.stripe_customer_id.isnot(None))
        result = await session.exec(statement)
        users = result.all()
        
        logger.info(f"Reconciling {len(users)} users with Stripe customer IDs")
        
        for user in users:
            try:
                # Get customer's active subscriptions from Stripe
                subscriptions = stripe_client.Subscription.list(
                    customer=user.stripe_customer_id,
                    status='all',
                    limit=10
                )
                
                # Check if user has any active subscriptions
                has_active_subscription = any(
                    sub.status in ['active', 'trialing'] 
                    for sub in subscriptions.data
                )
                
                # Update user status if it differs
                if user.active_subscription != has_active_subscription:
                    logger.info(
                        f"Updating subscription status for {user.email}: "
                        f"{user.active_subscription} -> {has_active_subscription}"
                    )
                    
                    if has_active_subscription:
                        await user_service.activate_subscription(user.email, user.stripe_customer_id, session)
                    else:
                        await user_service.deactivate_subscription(user.email, session)
                    
                    reconciled_count += 1
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error for user {user.email}: {str(e)}")
                error_count += 1
                continue
            except Exception as e:
                logger.error(f"Error reconciling user {user.email}: {str(e)}")
                error_count += 1
                continue
    
    logger.info(f"Reconciliation complete: {reconciled_count} updated, {error_count} errors")

async def _cleanup_tokens_async():
    """Async function to cleanup expired tokens"""
    async with get_async_session() as session:
        count = await user_service.cleanup_expired_tokens(session)
        return count

# Additional utility tasks
@celery_app.task(name='celery.beat.sync_user_subscription')
def sync_user_subscription(user_email: str):
    """
    Manual task to sync a specific user's subscription status
    Can be called on-demand when needed
    """
    try:
        logger.info(f"Syncing subscription for user: {user_email}")
        asyncio.run(_sync_single_user_async(user_email))
        return {"status": "success", "user": user_email}
    except Exception as e:
        logger.error(f"Error syncing user {user_email}: {str(e)}")
        return {"status": "error", "user": user_email, "error": str(e)}

async def _sync_single_user_async(user_email: str):
    """Sync a single user's subscription status"""
    stripe_client = get_stripe_client()
    
    async with get_async_session() as session:
        user = await user_service.get_user_by_email(user_email, session)
        
        if not user or not user.stripe_customer_id:
            logger.warning(f"User {user_email} has no Stripe customer ID")
            return
        
        # Get subscriptions from Stripe
        subscriptions = stripe_client.Subscription.list(
            customer=user.stripe_customer_id,
            status='all',
            limit=10
        )
        
        # Check if user has active subscriptions
        has_active_subscription = any(
            sub.status in ['active', 'trialing'] 
            for sub in subscriptions.data
        )
        
        # Update status if needed
        if user.active_subscription != has_active_subscription:
            if has_active_subscription:
                await user_service.activate_subscription(user_email, user.stripe_customer_id, session)
            else:
                await user_service.deactivate_subscription(user_email, session)
            
            logger.info(f"Updated subscription status for {user_email}: {has_active_subscription}")

if __name__ == '__main__':
    # For running the beat scheduler
    celery_app.start()