#!/bin/bash

# AutoHVAC Backend Development Server

echo "🚀 Starting AutoHVAC Backend Server..."

# Change to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Set environment variables for development
export PYTHONPATH=$PYTHONPATH:$(pwd)
export ENV=development

# Start the FastAPI server with uvicorn
echo "🌐 Starting server on http://localhost:8000"
echo "📖 API documentation available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run with reload for development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload