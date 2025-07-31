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
elif stripe.api_key == "sk_test_..." or stripe.api_key == "sk_live_...":
    # Only treat exact placeholder strings as invalid, not real keys that start with sk_test_ or sk_live_
    logger.error("CRITICAL: Stripe API key is using placeholder value! Stripe will not work.")
    logger.error("Please set a real Stripe API key in your environment variables.")
else:
    # Log success if we have what looks like a real key
    logger.info(f"Stripe API key configured successfully (starts with: {stripe.api_key[:12]}...)")

def get_stripe_client():
    """Get the configured stripe module"""
    # Simply return the stripe module - it should already be configured
    # Don't try to reinitialize as this can cause issues
    if not stripe.api_key:
        logger.error("WARNING: Stripe API key is not set when get_stripe_client() was called")
    return stripe

def is_test_mode():
    """Check if Stripe is in test mode"""
    return STRIPE_MODE != "live"

def validate_stripe_config():
    """Validate Stripe configuration and return issues if any"""
    issues = []
    
    if not stripe.api_key:
        issues.append("CRITICAL: Stripe API key not configured - Stripe will not work!")
    elif stripe.api_key in ["sk_test_...", "sk_live_..."]:
        # Only exact placeholder strings are invalid
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