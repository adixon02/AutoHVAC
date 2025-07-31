import os
import stripe
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Determine if we're using test mode or live mode
# Set STRIPE_MODE=live in production, defaults to test
STRIPE_MODE = os.getenv("STRIPE_MODE", "test").lower()

# Use test keys by default, override with live keys if STRIPE_MODE=live
if STRIPE_MODE == "live":
    # Live mode - use live keys (without _LIVE suffix for backward compatibility)
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_live_...")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_live_...")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "price_...")
    logger.info("Stripe configured in LIVE mode")
else:
    # Test mode - use test keys explicitly
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY_TEST", "sk_test_...")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY_TEST", "pk_test_...")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET_TEST", "whsec_...")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID_TEST", "price_...")
    logger.info("Stripe configured in TEST mode")

# Log which keys are being used (masked for security)
logger.info(f"Using Stripe keys - Mode: {STRIPE_MODE}, API Key: {stripe.api_key[:10] if stripe.api_key else 'None'}..., Price ID: {STRIPE_PRICE_ID[:10] if STRIPE_PRICE_ID else 'None'}...")

# Verify we have valid API key
if not stripe.api_key or stripe.api_key.startswith("sk_test_...") or stripe.api_key.startswith("sk_live_..."):
    logger.warning("Stripe API key not properly configured - using placeholder")

def get_stripe_client():
    return stripe

def is_test_mode():
    """Check if Stripe is in test mode"""
    return STRIPE_MODE != "live"

def validate_stripe_config():
    """Validate Stripe configuration and return issues if any"""
    issues = []
    
    if not stripe.api_key or stripe.api_key.startswith("sk_test_...") or stripe.api_key.startswith("sk_live_..."):
        issues.append("Stripe API key not configured (using placeholder)")
    
    if not STRIPE_PRICE_ID or STRIPE_PRICE_ID.startswith("price_..."):
        issues.append("Stripe Price ID not configured (using placeholder)")
    
    if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET.startswith("whsec_..."):
        issues.append("Stripe Webhook Secret not configured (using placeholder)")
    
    # Log configuration status
    if issues:
        logger.warning(f"Stripe configuration issues: {', '.join(issues)}")
    else:
        logger.info(f"Stripe configuration valid - Mode: {STRIPE_MODE}")
    
    return issues