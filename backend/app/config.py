import os
import logging
import sys

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Comma-separated list of emails that bypass verification in dev
DEV_VERIFIED_EMAILS = set(
    e.strip() for e in os.getenv("DEV_VERIFIED_EMAILS", "").split(",") if e.strip()
)

# Logging configuration
def setup_logging():
    """Configure application logging"""
    log_level = logging.DEBUG if DEBUG else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add file handler if needed
            # logging.FileHandler('app.log')
        ]
    )
    
    # Configure specific loggers
    logger = logging.getLogger('autohvac')
    logger.setLevel(log_level)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    return logger

# Initialize logging
setup_logging()