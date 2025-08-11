from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
# Import stripe config first to ensure stripe is configured
from core.stripe_config import STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID, validate_stripe_config
import stripe
from services.user_service import user_service
from database import get_async_session
from models.schemas import SubscribeRequest, SubscribeResponse
from routes.auth import get_current_user
from models.db_models import User
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/subscribe", response_model=SubscribeResponse)
async def create_subscription(
    request: SubscribeRequest,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        logger.info(f"Creating subscription for email: {request.email}")
        
        # Ensure user exists in our database
        await user_service.get_or_create_user(request.email, session)
        
        # Validate Stripe configuration
        config_issues = validate_stripe_config()
        if config_issues:
            logger.error(f"Stripe configuration issues found: {config_issues}")
            raise HTTPException(
                status_code=503,
                detail=f"Payment system configuration error: {', '.join(config_issues)}. Please contact support."
            )
        
        # Log Stripe configuration (masked for security)
        stripe_mode = os.getenv("STRIPE_MODE", "test")
        logger.info(f"Stripe configuration check - Mode: {stripe_mode}, Price ID: {STRIPE_PRICE_ID[:10]}..., API Key: {stripe.api_key[:10] if stripe.api_key else 'None'}...")
        
        # Get environment URLs or use defaults
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/payment/cancel"
        
        logger.info(f"Creating Stripe checkout session with URLs - Success: {success_url}, Cancel: {cancel_url}")
        
        # Verify stripe.checkout is available
        if not hasattr(stripe, 'checkout') or not hasattr(stripe.checkout, 'Session'):
            logger.error("CRITICAL: stripe.checkout.Session not available!")
            logger.error(f"stripe module: {type(stripe)}, has checkout: {hasattr(stripe, 'checkout')}")
            if hasattr(stripe, 'checkout'):
                logger.error(f"stripe.checkout: {type(stripe.checkout)}, has Session: {hasattr(stripe.checkout, 'Session')}")
            raise HTTPException(
                status_code=503,
                detail="Payment system initialization error. Please try again later."
            )
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
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
        
        logger.info(f"Successfully created Stripe checkout session for {request.email}: {checkout_session.id}")
        logger.info(f"Checkout URL: {checkout_session.url}")
        
        return SubscribeResponse(checkout_url=checkout_session.url)
        
    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe authentication error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Payment system authentication failed. Please contact support."
        )
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe invalid request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Invalid payment configuration: {str(e)}. Please contact support."
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Payment system error: {str(e)}. Please try again later."
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )

@router.post("/checkout")
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a Stripe checkout session for the authenticated user
    """
    try:
        logger.info(f"Creating checkout session for user: {current_user.email}")
        
        # Validate Stripe configuration
        config_issues = validate_stripe_config()
        if config_issues:
            logger.error(f"Stripe configuration issues found: {config_issues}")
            raise HTTPException(
                status_code=503,
                detail=f"Payment system configuration error: {', '.join(config_issues)}. Please contact support."
            )
        
        # Check if email is verified
        if not current_user.email_verified:
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before subscribing"
            )
        
        # Get environment URLs or use defaults
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend_url}/dashboard?subscription=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/pricing"
        
        logger.info(f"Creating Stripe checkout session with URLs - Success: {success_url}, Cancel: {cancel_url}")
        
        # Create or get Stripe customer ID
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={
                    'user_id': str(current_user.id),
                    'user_email': current_user.email
                }
            )
            customer_id = customer.id
            
            # Update user with customer ID
            current_user.stripe_customer_id = customer_id
            await session.commit()
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(current_user.id),
                'user_email': current_user.email
            },
            allow_promotion_codes=True,
            billing_address_collection='auto',
            customer_update={
                'address': 'auto'
            }
        )
        
        logger.info(f"Successfully created Stripe checkout session for {current_user.email}: {checkout_session.id}")
        
        return {
            "success": True,
            "checkout_url": checkout_session.url
        }
        
    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Payment system error: {str(e)}. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )

@router.post("/billing-portal")
async def create_billing_portal_session(
    current_user: User = Depends(get_current_user)
):
    """
    Create a Stripe billing portal session for the authenticated user
    """
    try:
        logger.info(f"Creating billing portal session for user: {current_user.email}")
        
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=404,
                detail="No billing account found. Please subscribe first."
            )
        
        # Get return URL
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return_url = f"{frontend_url}/account"
        
        # Create billing portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=return_url,
        )
        
        logger.info(f"Successfully created billing portal session for {current_user.email}")
        
        return {
            "success": True,
            "portal_url": portal_session.url
        }
        
    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating billing portal session: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Payment system error: {str(e)}. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error creating billing portal session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create billing portal session: {str(e)}"
        )

@router.get("/subscription-status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get the subscription status for the authenticated user
    """
    try:
        return {
            "has_active_subscription": current_user.active_subscription,
            "free_report_used": current_user.free_report_used,
            "stripe_customer_id": current_user.stripe_customer_id,
            "email_verified": current_user.email_verified
        }
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get subscription status: {str(e)}"
        )

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