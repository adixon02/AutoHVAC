#!/bin/bash
# Worker startup script for Pipeline V3

echo "🚀 Starting Pipeline V3 Worker..."
echo "Working directory: $(pwd)"

# For now, pipeline_v3 runs synchronously in the web process
# In the future, we can add Celery workers here if needed
echo "✅ Pipeline V3 uses direct execution - no separate worker needed"
echo "Web API handles processing asynchronously using asyncio"

# Keep the worker process alive (required by Render)
while true; do
    echo "⏰ Worker heartbeat: $(date)"
    sleep 300  # 5 minutes
done