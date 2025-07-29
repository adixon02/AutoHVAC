#!/bin/bash
# AutoHVAC Health Check Script
# Usage: ./health_check.sh [API_URL]
# Example: ./health_check.sh https://autohvac-backend.onrender.com

API_URL=${1:-"https://autohvac-backend.onrender.com"}

echo "🏥 Running health checks for $API_URL"
echo "========================================="

# Basic health check
echo -n "1. Basic health check: "
if curl -s -f "$API_URL/healthz" > /dev/null; then
    echo "✅ OK"
    curl -s "$API_URL/healthz" | jq '.' 2>/dev/null || curl -s "$API_URL/healthz"
else
    echo "❌ FAILED"
fi

echo ""

# Check specific components
echo "2. Component Status:"
echo -n "   - Database: "
curl -s "$API_URL/healthz" | jq -r '.checks.database.status' 2>/dev/null || echo "Unable to parse"

echo -n "   - Redis: "
curl -s "$API_URL/healthz" | jq -r '.checks.redis.status' 2>/dev/null || echo "Unable to parse"

echo -n "   - Celery Workers: "
WORKERS=$(curl -s "$API_URL/healthz" | jq -r '.checks.celery_workers.workers' 2>/dev/null)
if [ "$WORKERS" != "null" ] && [ -n "$WORKERS" ]; then
    echo "$WORKERS worker(s) active"
else
    STATUS=$(curl -s "$API_URL/healthz" | jq -r '.checks.celery_workers.status' 2>/dev/null)
    echo "$STATUS"
fi

echo ""

# API endpoint check
echo -n "3. API root endpoint: "
if curl -s -f "$API_URL/" > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Upload endpoint OPTIONS (CORS)
echo -n "4. CORS preflight check: "
if curl -s -f -X OPTIONS "$API_URL/api/v1/blueprint/upload" \
    -H "Origin: https://autohvac-frontend.onrender.com" \
    -H "Access-Control-Request-Method: POST" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Legacy health endpoint
echo -n "5. Legacy health endpoint: "
if curl -s -f "$API_URL/health" > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

echo ""
echo "========================================="

# Overall status
OVERALL_STATUS=$(curl -s "$API_URL/healthz" | jq -r '.status' 2>/dev/null)
if [ "$OVERALL_STATUS" = "ok" ]; then
    echo "✅ Overall Status: HEALTHY"
    exit 0
elif [ "$OVERALL_STATUS" = "degraded" ]; then
    echo "⚠️  Overall Status: DEGRADED"
    exit 1
else
    echo "❌ Overall Status: UNHEALTHY or UNREACHABLE"
    exit 2
fi