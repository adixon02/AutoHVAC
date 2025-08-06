#!/bin/bash
# Worker startup script with correct module path

cd /app/backend

echo "Starting Celery worker with calculate_hvac_loads module..."

celery -A tasks.calculate_hvac_loads worker \
  --loglevel=info \
  --concurrency=2 \
  --max-tasks-per-child=50 \
  --max-memory-per-child=1536000 \
  --time-limit=1800 \
  --soft-time-limit=1740 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat