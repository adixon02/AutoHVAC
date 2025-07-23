#!/bin/bash

echo "Starting build process..."

# Install system dependencies if needed
if command -v apt-get >/dev/null; then
    echo "Installing system dependencies..."
    apt-get update
    apt-get install -y poppler-utils
fi

# Upgrade pip to avoid any compatibility issues
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads processed exports outputs logs

echo "Build process completed successfully!"