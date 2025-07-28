#!/bin/bash

# start_with_migrations.sh
# Startup script for Render deployment that runs Alembic migrations before starting the backend

set -e  # Exit on any error

echo "🔄 Starting AutoHVAC Backend with migrations..."

# Ensure we're in the backend directory
cd "$(dirname "$0")"

echo "📍 Current directory: $(pwd)"

# Use python or python3 depending on what's available
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo "❌ Neither python nor python3 found"
        exit 1
    fi
fi

# Run Alembic migrations to ensure database schema is up to date
echo "🗄️  Running Alembic migrations with $PYTHON_CMD..."
$PYTHON_CMD -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed - exiting"
    exit 1
fi

# Start the backend application
echo "🚀 Starting backend application with $PYTHON_CMD..."
exec $PYTHON_CMD -m backend