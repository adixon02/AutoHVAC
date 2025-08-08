#!/bin/bash
# Worker startup script with correct module path

# Fix: Use the actual project path on Render
cd /opt/render/project/src/backend || {
    echo "ERROR: Failed to change to backend directory"
    echo "Current directory: $(pwd)"
    echo "Looking for backend in: /opt/render/project/src/backend"
    exit 1
}

echo "Starting Celery worker with calculate_hvac_loads module..."
echo "Working directory: $(pwd)"

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