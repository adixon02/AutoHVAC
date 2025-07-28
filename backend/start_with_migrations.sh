#!/bin/bash

# start_with_migrations.sh
# Startup script for Render deployment that runs Alembic migrations before starting the backend

set -e  # Exit on any error

echo "=========================================="
echo "🔄 AUTOHVAC BACKEND STARTUP WITH MIGRATIONS"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Environment: ${NODE_ENV:-development}"

# Ensure we're in the backend directory
cd "$(dirname "$0")"
echo "📍 Working directory: $(pwd)"
echo "📂 Contents: $(ls -la)"

# Use python or python3 depending on what's available
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo "❌ ERROR: Neither python nor python3 found in PATH"
        echo "PATH: $PATH"
        exit 1
    fi
fi

echo "🐍 Using Python: $PYTHON_CMD"
echo "🐍 Python version: $($PYTHON_CMD --version)"

# Check if Alembic is available 
if ! $PYTHON_CMD -c "import alembic" &> /dev/null; then
    echo "❌ ERROR: Alembic not found. Installing requirements may have failed."
    exit 1
fi

# Check database connectivity
echo "🔍 Checking database connection..."
if [ -n "$DATABASE_URL" ]; then
    echo "📊 Database URL configured: ${DATABASE_URL:0:20}..."
else
    echo "⚠️  WARNING: DATABASE_URL not set, using default SQLite"
fi

# Run Alembic migrations to ensure database schema is up to date
echo "🗄️  Running Alembic migrations..."
echo "Migration command: $PYTHON_CMD -m alembic upgrade head"

$PYTHON_CMD -m alembic upgrade head

MIGRATION_EXIT_CODE=$?
if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed with exit code: $MIGRATION_EXIT_CODE"
    echo "🔍 Alembic history:"
    $PYTHON_CMD -m alembic history --verbose || true
    echo "🔍 Current revision:"
    $PYTHON_CMD -m alembic current || true
    exit 1
fi

# Start the backend application
echo "🚀 Starting backend application..."
echo "Start command: $PYTHON_CMD -m backend"
echo "=========================================="

exec $PYTHON_CMD -m backend