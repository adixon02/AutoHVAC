import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Comma-separated list of emails that bypass verification in dev
DEV_VERIFIED_EMAILS = set(
    e.strip() for e in os.getenv("DEV_VERIFIED_EMAILS", "austind02@gmail.com").split(",") if e
)