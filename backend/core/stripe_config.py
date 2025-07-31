import os
import stripe
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Emergency debug logging
logger.error("=== STRIPE CONFIGURATION DEBUG ===")
logger.error(f"STRIPE_MODE env var: {os.getenv('STRIPE_MODE')}")
logger.error(f"STRIPE_SECRET_KEY_TEST env var: {os.getenv('STRIPE_SECRET_KEY_TEST', 'NOT SET')[:20]}..." if os.getenv('STRIPE_SECRET_KEY_TEST') else "STRIPE_SECRET_KEY_TEST: NOT SET")
logger.error(f"STRIPE_PRICE_ID_TEST env var: {os.getenv('STRIPE_PRICE_ID_TEST', 'NOT SET')}")
logger.error("==================================")

# Determine if we're using test mode or live mode
# Set STRIPE_MODE=live in production, defaults to test
STRIPE_MODE = os.getenv("STRIPE_MODE", "test").lower()

# Use test keys by default, override with live keys if STRIPE_MODE=live
if STRIPE_MODE == "live":
    # Live mode - use live keys (without _LIVE suffix for backward compatibility)
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
    logger.info("Stripe configured in LIVE mode")
else:
    # Test mode - use test keys explicitly
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY_TEST")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY_TEST")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET_TEST")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID_TEST")
    logger.info("Stripe configured in TEST mode")

# Log which keys are being used (masked for security)
logger.info(f"Using Stripe keys - Mode: {STRIPE_MODE}, API Key: {stripe.api_key[:10] if stripe.api_key else 'None'}..., Price ID: {STRIPE_PRICE_ID[:10] if STRIPE_PRICE_ID else 'None'}...")

# Verify we have valid API key
if not stripe.api_key:
    logger.error("CRITICAL: Stripe API key is not set! Stripe will not work.")
    logger.error(f"Looking for STRIPE_SECRET_KEY_TEST in test mode, got: {os.getenv('STRIPE_SECRET_KEY_TEST', 'NOT SET')}")
    stripe.api_key = None  # Explicitly set to None to cause clear errors
elif stripe.api_key.startswith("sk_test_...") or stripe.api_key.startswith("sk_live_..."):
    logger.error("CRITICAL: Stripe API key is using placeholder value! Stripe will not work.")
    stripe.api_key = None  # Explicitly set to None to cause clear errors

def get_stripe_client():
    """Get the configured stripe module - ensures it's properly initialized"""
    if not stripe.api_key:
        # Try to reinitialize if needed
        if STRIPE_MODE == "test":
            key = os.getenv("STRIPE_SECRET_KEY_TEST")
        else:
            key = os.getenv("STRIPE_SECRET_KEY")
        
        if key and not key.startswith("sk_test_...") and not key.startswith("sk_live_..."):
            stripe.api_key = key
            logger.info(f"Stripe API key reinitialized in get_stripe_client()")
        else:
            logger.error(f"CRITICAL: Cannot initialize Stripe! Key is: {key[:20] if key else 'None'}")
    
    return stripe

def is_test_mode():
    """Check if Stripe is in test mode"""
    return STRIPE_MODE != "live"

def validate_stripe_config():
    """Validate Stripe configuration and return issues if any"""
    issues = []
    
    if not stripe.api_key:
        issues.append("CRITICAL: Stripe API key not configured - Stripe will not work!")
    elif stripe.api_key and (stripe.api_key.startswith("sk_test_...") or stripe.api_key.startswith("sk_live_...")):
        issues.append("CRITICAL: Stripe API key using placeholder - Stripe will not work!")
    
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