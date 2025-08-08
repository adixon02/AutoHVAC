# 🎯 AutoHVAC Environment Files - Simple Guide

## What You Actually Need to Know

### For Running Backend Locally (Most Common)

**Use these files:**
- `backend/.env` - Base configuration (already set up)
- `backend/.env.local` - Your API keys (already has your OpenAI key)

**Run from backend directory:**
```bash
cd backend
python3 -m uvicorn app.main:app --reload
```

Your secrets are loaded automatically from `.env.local`!

### For Running with Docker

**Use these files:**
- `.env` - Docker configuration (root directory)
- `backend/.env.local` - Your API keys

**Run from root directory:**
```bash
docker-compose up
```

### For Production (Render)

**Don't use any .env files!**

Set these in Render Dashboard:
- OPENAI_API_KEY = your-production-key
- ENV = production
- (Render auto-sets DATABASE_URL and REDIS_URL)

## File Locations Summary

```
/AutoHVAC/
├── .env                    ← Docker config (no secrets!)
├── .env.example            ← Docker template
│
├── backend/
│   ├── .env               ← Base defaults ✅ (safe to commit)
│   ├── .env.local         ← YOUR SECRETS HERE ✅ (never commits)
│   └── .env.example       ← Documentation
│
└── frontend/
    ├── .env.local         ← Frontend config
    └── .env.example       ← Frontend template
```

## ❌ Files to Ignore/Delete

None needed! Each serves a purpose:
- Root `.env` = Docker configuration
- Backend `.env` files = Python app configuration
- Frontend `.env` files = React app configuration

## ✅ Your Current Setup

1. **backend/.env.local** has your OpenAI API key ✅
2. **backend/.env** has safe defaults ✅
3. Root `.env` now has placeholders only (no secrets) ✅

You're ready to go! Just run from the backend directory:
```bash
cd backend
python3 test_local_env.py  # Verify setup
python3 -m uvicorn app.main:app --reload  # Start server
```