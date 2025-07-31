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
    # Live mode - use live keys
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY_LIVE", os.getenv("STRIPE_SECRET_KEY", "sk_test_..."))
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY_LIVE", os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_..."))
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET_LIVE", os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_..."))
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID_LIVE", os.getenv("STRIPE_PRICE_ID", "price_..."))
    logger.info("Stripe configured in LIVE mode")
else:
    # Test mode - use test keys
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY_TEST", os.getenv("STRIPE_SECRET_KEY", "sk_test_..."))
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY_TEST", os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_..."))
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET_TEST", os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_..."))
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID_TEST", os.getenv("STRIPE_PRICE_ID", "price_..."))
    logger.info("Stripe configured in TEST mode")

# Verify we have valid API key
if not stripe.api_key or stripe.api_key.startswith("sk_test_...") or stripe.api_key.startswith("sk_live_..."):
    logger.warning("Stripe API key not properly configured - using placeholder")

def get_stripe_client():
    return stripe

def is_test_mode():
    """Check if Stripe is in test mode"""
    return STRIPE_MODE != "live"