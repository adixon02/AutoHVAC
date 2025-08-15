from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import os
import logging
from sqlmodel import Session
# Import stripe config first to ensure stripe is configured
from app.core.stripe_config import STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID, validate_stripe_config
import stripe
from app.services.user_service import user_service
from app.database import get_session
from app.models.schemas import SubscribeRequest, SubscribeResponse, CheckoutSessionResponse, BillingPortalResponse, SubscriptionStatusResponse
# from app.routes.auth import get_current_user  # TODO: Add proper JWT auth
from app.models.user import User
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/subscribe", response_model=SubscribeResponse)
async def create_subscription(
    request: SubscribeRequest,
    session: Session = Depends(get_session)
):
    try:
        logger.info(f"Creating subscription for email: {request.email}")
        
        # Ensure user exists in our database
        user_service.get_or_create_user(request.email, session)
        
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
        
        # In test mode, immediately activate subscription for better UX
        if os.getenv("STRIPE_MODE", "test") == "test":
            logger.info(f"Test mode detected - immediately activating subscription for {request.email}")
            user_service.activate_subscription(request.email, checkout_session.customer or "test_customer", session)
            
            # Auto-process any pending blueprints for this user after upgrade
            await _process_pending_blueprints_for_user(request.email)
        
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

@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    email: str,  # TODO: Replace with proper auth
    session: Session = Depends(get_session)
):
    """
    Create a Stripe checkout session for the authenticated user
    """
    try:
        # Get user from database
        current_user = user_service.get_user_by_email(email, session)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
            
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
            session.add(current_user)
            session.commit()
        
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
        
        return CheckoutSessionResponse(
            success=True,
            checkout_url=checkout_session.url
        )
        
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

@router.post("/billing-portal", response_model=BillingPortalResponse)
async def create_billing_portal_session(
    email: str,  # TODO: Replace with proper auth
    session: Session = Depends(get_session)
):
    """
    Create a Stripe billing portal session for the authenticated user
    """
    try:
        # Get user from database
        current_user = user_service.get_user_by_email(email, session)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
            
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
        
        return BillingPortalResponse(
            success=True,
            portal_url=portal_session.url
        )
        
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

@router.get("/subscription-status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    email: str,  # TODO: Replace with proper auth
    session: Session = Depends(get_session)
):
    """
    Get the subscription status for the authenticated user
    """
    try:
        # Get user from database
        current_user = user_service.get_user_by_email(email, session)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return SubscriptionStatusResponse(
            has_active_subscription=current_user.is_paying_customer(),
            free_report_used=current_user.free_report_used,
            stripe_customer_id=current_user.stripe_customer_id,
            email_verified=current_user.email_verified
        )
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
    
    try:
        with Session(get_session().__next__()) as session:
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

async def _handle_checkout_completed(session_obj: dict, session: Session):
    """Handle successful checkout session completion"""
    user_email = session_obj.get('metadata', {}).get('user_email')
    customer_id = session_obj.get('customer')
    
    if user_email and customer_id:
        logger.info(f"Activating subscription for {user_email}, customer: {customer_id}")
        user_service.activate_subscription(user_email, customer_id, session)
    else:
        logger.warning(f"Missing user_email or customer_id in checkout session: {session_obj.get('id')}")

async def _handle_invoice_paid(invoice_obj: dict, session: Session):
    """Handle successful invoice payment"""
    customer_id = invoice_obj.get('customer')
    
    if customer_id:
        # Find user by stripe customer ID and ensure subscription is active
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.info(f"Confirming active subscription for customer: {customer_id}")
            user_service.activate_subscription(user.email, customer_id, session)

async def _handle_subscription_deleted(subscription_obj: dict, session: Session):
    """Handle subscription cancellation"""
    customer_id = subscription_obj.get('customer')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.info(f"Deactivating subscription for customer: {customer_id}")
            user_service.deactivate_subscription(user.email, session)

async def _handle_payment_failed(invoice_obj: dict, session: Session):
    """Handle failed payment"""
    customer_id = invoice_obj.get('customer')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            logger.warning(f"Payment failed for customer: {customer_id}, deactivating subscription")
            user_service.deactivate_subscription(user.email, session)

async def _handle_subscription_updated(subscription_obj: dict, session: Session):
    """Handle subscription status changes"""
    customer_id = subscription_obj.get('customer')
    status = subscription_obj.get('status')
    
    if customer_id:
        user = await _get_user_by_stripe_customer_id(customer_id, session)
        if user:
            # Activate only if subscription is active or trialing
            if status in ['active', 'trialing']:
                logger.info(f"Subscription updated to {status} for customer: {customer_id}")
                user_service.activate_subscription(user.email, customer_id, session)
            else:
                logger.info(f"Subscription updated to {status} for customer: {customer_id}, deactivating")
                user_service.deactivate_subscription(user.email, session)

async def _get_user_by_stripe_customer_id(customer_id: str, session: Session):
    """Helper to find user by Stripe customer ID"""
    from sqlmodel import select
    from app.models.user import User
    
    statement = select(User).where(User.stripe_customer_id == customer_id)
    result = session.exec(statement)
    return result.first()

async def _process_pending_blueprints_for_user(email: str):
    """Process any pending/failed blueprints for a newly upgraded user"""
    try:
        logger.info(f"🔄 Checking for pending blueprints for upgraded user: {email}")
        
        # Import here to avoid circular imports
        from app.routes.blueprint import jobs, process_blueprint_async
        from app.database import get_session
        import os
        import asyncio
        
        # Find jobs for this user that are pending upgrade
        user_jobs = []
        for job_id, job in jobs.items():
            if (job.get("email") == email and 
                job.get("status") == "pending_upgrade" and
                job.get("needs_upgrade") == True):
                user_jobs.append((job_id, job))
        
        if user_jobs:
            logger.info(f"🚀 Found {len(user_jobs)} blocked jobs for {email} - processing now!")
            
            # Process each blocked job
            for job_id, job in user_jobs:
                try:
                    # Get API key from environment
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        logger.error(f"Cannot process job {job_id} - no OpenAI API key")
                        continue
                    
                    # Reset job status
                    jobs[job_id]["status"] = "processing"
                    jobs[job_id]["progress"] = 0
                    jobs[job_id]["error"] = None
                    
                    logger.info(f"🔄 Auto-processing job {job_id} for upgraded user {email}")
                    
                    # Download file from S3 and create temp file for processing
                    s3_path = job.get("saved_file_path")
                    if s3_path:
                        try:
                            # Get the file content from S3
                            from app.services.s3_storage import storage_service
                            import tempfile
                            
                            file_content = await storage_service.download_file(s3_path)
                            
                            # Create temporary file for processing
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                                temp_file.write(file_content)
                                temp_file_path = temp_file.name
                            
                            # Get a fresh database session
                            with Session(get_session().__next__()) as fresh_session:
                                # Start processing (this will create a new background task)
                                asyncio.create_task(process_blueprint_async(
                                    job_id=job_id,
                                    pdf_path=temp_file_path,
                                    zip_code=job.get("zip_code", "99006"),
                                    api_key=api_key,
                                    email=email,
                                    session=fresh_session,
                                    is_first_report=False,  # They're now a paying customer
                                    user_inputs=job.get("user_inputs", {}),
                                    project_label=job.get("project_label", "Upgraded User Project")
                                ))
                                
                        except Exception as download_error:
                            logger.error(f"Failed to download file for job {job_id}: {download_error}")
                            jobs[job_id]["status"] = "failed"
                            jobs[job_id]["error"] = f"Failed to retrieve saved file: {download_error}"
                    else:
                        logger.error(f"No saved file path for job {job_id}")
                        jobs[job_id]["status"] = "failed"
                        jobs[job_id]["error"] = "No saved file found for processing"
                        
                except Exception as e:
                    logger.error(f"Failed to auto-process job {job_id}: {e}")
                    
        else:
            logger.info(f"No blocked jobs found for {email}")
            
    except Exception as e:
        logger.error(f"Error checking pending blueprints for {email}: {e}")
        # Don't fail the upgrade process if this fails