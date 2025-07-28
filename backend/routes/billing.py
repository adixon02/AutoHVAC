from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import stripe
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from core.stripe_config import get_stripe_client, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID
from services.user_service import user_service
from database import get_async_session
from models.schemas import SubscribeRequest, SubscribeResponse
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/subscribe", response_model=SubscribeResponse)
async def create_subscription(
    request: SubscribeRequest,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        # Ensure user exists in our database
        await user_service.get_or_create_user(request.email, session)
        
        stripe_client = get_stripe_client()
        
        # Get environment URLs or use defaults
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/payment/cancel"
        
        # Create Stripe checkout session
        checkout_session = stripe_client.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.email,
            metadata={
                'user_email': request.email
            },
            allow_promotion_codes=True,
            billing_address_collection='auto',
            automatic_tax={'enabled': False}
        )
        
        logger.info(f"Created Stripe checkout session for {request.email}: {checkout_session.id}")
        
        return SubscribeResponse(session_url=checkout_session.url)
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment system error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    logger.info(f"Received Stripe webhook: {event['type']}")
    
    async with get_async_session() as session:
        try:
            if event['type'] == 'checkout.session.completed':
                await _handle_checkout_completed(event['data']['object'], session)
            
            elif event['type'] == 'invoice.paid':
                await _handle_invoice_paid(event['data']['object'], session)
            
            elif event['type'] == 'customer.subscription.deleted':
                await _handle_subscription_deleted(event['data']['object'], session)
            
            elif event['type'] == 'invoice.payment_failed':
                await _handle_payment_failed(event['data']['object'], session)
            
            elif event['type'] == 'customer.subscription.updated':
                await _handle_subscription_updated(event['data']['object'], session)
            
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
        
        except Exception as e:
            logger.error(f"Error processing webhook {event['type']}: {str(e)}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")
    
    return JSONResponse(content={"status": "success"})

async def _handle_checkout_completed(session_obj: dict, session: AsyncSession):
    """Handle successful checkout session completion"""
    user_email = session_obj.get('metadata', {}).get('user_email')
    customer_id = session_obj.get('customer')
    
    if user_email and customer_id:
        logger.info(f"Activating subscription for {user_email}, customer: {customer_id}")
        await user_service.activate_subscription(user_email, customer_id, session)
    else:
        logger.warning(f"Missing user_email or customer_id in checkout session: {session_obj.get('id')}")

async def _handle_invoice_paid(invoice_obj: dict, session: AsyncSession):
    """Handle successful invoice payment"""
    customer_id = invoice_obj.get('customer')
    
    if customer_id:
        # Find user by stripe customer ID and ensure subscription is active
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.info(f"Confirming active subscription for customer: {customer_id}")
            await user_service.activate_subscription(user.email, customer_id, session)

async def _handle_subscription_deleted(subscription_obj: dict, session: AsyncSession):
    """Handle subscription cancellation"""
    customer_id = subscription_obj.get('customer')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.info(f"Deactivating subscription for customer: {customer_id}")
            await user_service.deactivate_subscription(user.email, session)

async def _handle_payment_failed(invoice_obj: dict, session: AsyncSession):
    """Handle failed payment"""
    customer_id = invoice_obj.get('customer')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.warning(f"Payment failed for customer: {customer_id}, deactivating subscription")
            await user_service.deactivate_subscription(user.email, session)

async def _handle_subscription_updated(subscription_obj: dict, session: AsyncSession):
    """Handle subscription status changes"""
    customer_id = subscription_obj.get('customer')
    status = subscription_obj.get('status')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            # Activate only if subscription is active or trialing
            if status in ['active', 'trialing']:
                logger.info(f"Subscription updated to {status} for customer: {customer_id}")
                await user_service.activate_subscription(user.email, customer_id, session)
            else:
                logger.info(f"Subscription updated to {status} for customer: {customer_id}, deactivating")
                await user_service.deactivate_subscription(user.email, session)

async def _get_user_by_stripe_customer_id(customer_id: str, session: AsyncSession):
    """Helper to find user by Stripe customer ID"""
    from sqlmodel import select
    from models.db_models import User
    
    statement = select(User).where(User.stripe_customer_id == customer_id)
    result = await session.exec(statement)
    return result.first()