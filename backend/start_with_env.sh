#!/bin/bash
export DEBUG=true
export DEV_VERIFIED_EMAILS="${DEV_VERIFIED_EMAILS:-}"
export DISABLE_PDF=true
export STRIPE_SECRET_KEY=""
export STRIPE_PUBLISHABLE_KEY=""
export STRIPE_WEBHOOK_SECRET=""
export STRIPE_PRICE_ID=""

cd /Users/austindixon/Documents/AutoHVAC/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000