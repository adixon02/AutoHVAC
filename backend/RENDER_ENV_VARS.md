# Render Environment Variables for Worker

Add these environment variables to your Render worker service:

## Required for Geometry-First Approach

```
PARSING_MODE=traditional_first
GEOMETRY_AUTHORITATIVE=true
```

## Full Recommended Configuration

```
# Core settings (existing - keep these)
OPENAI_API_KEY=<your-key>
DATABASE_URL=<your-postgres-url>
REDIS_URL=<your-redis-url>
AWS_ACCESS_KEY_ID=<your-aws-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret>
AWS_REGION=us-west-2
S3_BUCKET_NAME=<your-bucket>

# Parsing configuration (NEW - add these)
PARSING_MODE=traditional_first
GEOMETRY_AUTHORITATIVE=true
USE_GPT4_VISION=false  # Disabled - GPT-4V not accurate for measurements
MULTI_FLOOR_ENABLED=true
MIN_FLOOR_PLAN_SCORE=100

# HVAC calculation settings (add if not present)
ALLOW_GENERATED_SPACES=false
MIN_CONFIDENCE_THRESHOLD=0.3
MIN_QUALITY_SCORE=30

# Optional but recommended
DEBUG=true
LOG_LEVEL=INFO
```

## How to Add in Render Dashboard

1. Go to https://dashboard.render.com
2. Click on your worker service (usually named something like "autohvac-worker")
3. Go to "Environment" tab
4. Add each variable above
5. Click "Save Changes"
6. The worker will automatically redeploy with new settings

## Testing After Deployment

After the worker redeploys, test with job 7298134e-52a0-43a0-b243-d19120a940ab or submit a new blueprint to verify:
- HVAC loads should be closer to 74,000 BTU/hr heating
- Check logs for "GEOMETRY_AUTHORITATIVE mode" messages
- Verify areas are marked as "geometry_extracted" source