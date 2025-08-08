# Environment Files Cleanup Plan

## Current State (MESSY)
```
/AutoHVAC/
├── .env                 ← FOR DOCKER (has your API key exposed!)
├── .env.example         ← Docker template
├── backend/
│   ├── .env            ← FOR BACKEND (has placeholders)
│   ├── .env.example    ← Backend template  
│   └── .env.local      ← Your secrets (good!)
└── frontend/
    ├── .env.example    ← Frontend template
    └── .env.local      ← Frontend config
```

## What Each Is For:

### ROOT Level (/AutoHVAC/)
- **`.env`** - Used by Docker Compose when running `docker-compose up`
- **`.env.example`** - Template for Docker setup
- **Issue**: Your API key is exposed in the root .env!

### BACKEND Level (/AutoHVAC/backend/)
- **`.env`** - Base defaults (safe to commit)
- **`.env.example`** - Documentation
- **`.env.local`** - Your actual secrets (gitignored)
- **This is what we use when running backend directly**

## Recommended Action:

1. **Keep backend/.env files** - These are properly organized
2. **Fix root .env** - Remove secrets, keep only Docker config
3. **Use .env.local for secrets** - Never commit real keys

## Which Files You Actually Need:

### For Local Development (WITHOUT Docker):
```
backend/.env        ← Base config (committed)
backend/.env.local  ← Your secrets (gitignored)
```

### For Docker Development:
```
.env                ← Docker config only (no secrets!)
backend/.env.local  ← Your secrets (gitignored)
```

### For Production (Render):
```
None! Set environment variables in Render dashboard
```