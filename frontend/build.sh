#!/bin/bash

# Build script for Render deployment
echo "Starting build process..."

# Debug: Show current directory structure
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Ensure prisma directory exists
if [ -f "prisma/schema.prisma" ]; then
    echo "✓ Prisma schema found at prisma/schema.prisma"
else
    echo "✗ Prisma schema not found!"
    echo "Looking for schema file..."
    find . -name "schema.prisma" -type f
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Generate Prisma client
echo "Generating Prisma client..."
npx prisma generate

# Build Next.js app
echo "Building Next.js application..."
npm run build

echo "Build process complete!"