# Environment Configuration Guide

## Overview

AutoHVAC uses a three-tier environment configuration system:

1. **`.env`** - Base configuration with safe defaults (committed to git)
2. **`.env.local`** - Local overrides with your secrets (gitignored) 
3. **Render Environment Variables** - Production secrets (set in Render dashboard)

## File Structure

```
backend/
├── .env              # ✅ Committed - Safe defaults only
├── .env.example      # ✅ Committed - Complete template with docs
├── .env.local        # ❌ Gitignored - Your actual secrets
└── .gitignore        # ✅ Committed - Ensures .env.local is ignored
```

## Quick Start

### Local Development

1. **Run the setup script:**
   ```bash
   cd backend
   chmod +x setup_local_env.sh
   ./setup_local_env.sh
   ```

2. **Edit `.env.local` with your actual API keys:**
   ```bash
   nano .env.local  # or use your preferred editor
   ```

3. **Add your keys:**
   ```env
   # Required for AI blueprint parsing
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   
   # Optional for payments
   STRIPE_SECRET_KEY=sk_test_your-actual-test-key
   ```

4. **Test your setup:**
   ```bash
   python3 test_local_env.py
   ```

### Production (Render)

**DO NOT** upload `.env.local` to production!

Instead, set these environment variables in Render's dashboard:

#### Required Variables:
```env
OPENAI_API_KEY=sk-proj-your-production-key
ENV=production
```

#### Automatically Set by Render:
```env
DATABASE_URL=postgresql://...  # From Render PostgreSQL
REDIS_URL=redis://...          # From Render Redis add-on
RENDER_DISK_PATH=/var/data     # From persistent disk
```

#### Optional Production Variables:
```env
# Stripe (for payments)
STRIPE_MODE=live
STRIPE_SECRET_KEY=sk_live_your-production-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-production-key
STRIPE_WEBHOOK_SECRET=whsec_your-production-webhook
STRIPE_PRICE_ID=price_your-production-price

# Email (SendGrid)
SENDGRID_API_KEY=SG.your-production-key
FROM_EMAIL=no-reply@yourdomain.com

# Frontend
FRONTEND_URL=https://your-frontend-domain.com
```

## Environment Loading Order

The application loads environment variables in this priority:

1. **System environment variables** (highest priority)
2. **`.env.local`** (local overrides)
3. **`.env`** (base defaults)

This means:
- In local development: `.env.local` overrides `.env`
- In production: Render variables override everything

## Testing Your Configuration

### Check if environment is loaded correctly:
```python
# test_local_env.py
from dotenv import load_dotenv
import os

# Load environment
load_dotenv('.env.local')
load_dotenv('.env')

# Check critical variables
api_key = os.getenv('OPENAI_API_KEY')
if api_key and api_key != 'your-openai-api-key-here':
    print("✅ OpenAI API key configured")
else:
    print("❌ OpenAI API key not set")

# Check environment
env = os.getenv('ENV', 'development')
print(f"📍 Environment: {env}")

# Check OCR settings
ocr = os.getenv('ENABLE_PADDLE_OCR', 'false')
print(f"🔍 PaddleOCR: {'enabled' if ocr == 'true' else 'disabled'}")
```

### Test blueprint parsing:
```bash
export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env.local | cut -d'=' -f2)
python3 -c "from services.blueprint_parser import BlueprintParser; print('✅ Parser ready')"
```

## Common Issues

### API Key Not Working
```bash
# Check if key is loaded
python3 -c "import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print(os.getenv('OPENAI_API_KEY')[:10] + '...' if os.getenv('OPENAI_API_KEY') else 'Not set')"
```

### Redis Connection Failed
```bash
# Start Redis locally
redis-server

# Or run without Redis (will use in-memory cache)
REDIS_URL=redis://localhost:6379/0 python3 app.py
```

### Database Issues
```bash
# Use SQLite for local development
DATABASE_URL=sqlite:///./autohvac.db python3 app.py
```

## Security Best Practices

1. **NEVER commit `.env.local`** - It should always be gitignored
2. **NEVER put real API keys in `.env`** - Only placeholders
3. **ALWAYS use test keys locally** - Never use production keys
4. **ROTATE keys regularly** - Especially if exposed
5. **USE environment-specific keys** - Different keys for dev/staging/prod

## File Purposes

| File | Purpose | Git Status | Contains Secrets |
|------|---------|------------|------------------|
| `.env` | Base defaults | ✅ Committed | ❌ No |
| `.env.example` | Documentation | ✅ Committed | ❌ No |
| `.env.local` | Local secrets | ❌ Gitignored | ✅ Yes |
| Render vars | Production | N/A | ✅ Yes |

## Questions?

- Check `.env.example` for all available variables
- Run `./setup_local_env.sh` for automated setup
- Set production variables in Render dashboard, not in files