#!/bin/bash
# Setup local environment for AutoHVAC development
# This script helps configure local API keys without committing them to git

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════╗"
echo "║        AutoHVAC Local Environment Setup                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "🔍 Checking Python environment..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  ✅ Python $PYTHON_VERSION found"
else
    echo "  ❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check if .env.example exists
if [ ! -f .env.example ]; then
    echo "⚠️  .env.example not found. Creating from template..."
    # This would normally copy from a template
fi

# Create or update .env.local
if [ -f .env.local ]; then
    echo ""
    echo "📄 .env.local already exists"
    echo "  Would you like to update it with latest variables? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Backup existing .env.local
        cp .env.local .env.local.backup
        echo "  ✅ Backed up existing .env.local to .env.local.backup"
        
        # Merge new variables from .env.example
        if [ -f .env.example ]; then
            # Copy .env.example and preserve existing values from .env.local
            cp .env.example .env.local.tmp
            
            # Read each line from backup and update tmp file
            while IFS='=' read -r key value; do
                if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
                    # Update the value in tmp file if it exists
                    sed -i.bak "s|^$key=.*|$key=$value|" .env.local.tmp 2>/dev/null || true
                fi
            done < .env.local.backup
            
            mv .env.local.tmp .env.local
            rm -f .env.local.tmp.bak
            echo "  ✅ Updated .env.local with new variables"
        fi
    fi
else
    echo ""
    echo "📄 Creating .env.local file..."
    
    if [ -f .env.example ]; then
        cp .env.example .env.local
        echo "  ✅ Created .env.local from .env.example"
    else
        cp .env .env.local
        echo "  ✅ Created .env.local from .env"
    fi
fi

# Check if .gitignore includes .env.local
if [ -f .gitignore ]; then
    if grep -q ".env.local" .gitignore; then
        echo "  ✅ .env.local is already in .gitignore"
    else
        echo "  Adding .env.local to .gitignore..."
        echo -e "\n# Local environment overrides\n.env.local" >> .gitignore
        echo "  ✅ Added .env.local to .gitignore"
    fi
else
    echo ".env.local" > .gitignore
    echo "  ✅ Created .gitignore with .env.local"
fi

# Check for required services
echo ""
echo "🔍 Checking local services..."

# Check Redis
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        echo "  ✅ Redis is running"
    else
        echo "  ⚠️  Redis is installed but not running"
        echo "     Start with: redis-server"
    fi
else
    echo "  ⚠️  Redis not found (optional for local development)"
    echo "     Install with: brew install redis (macOS) or apt-get install redis-server (Linux)"
fi

# Check PostgreSQL (optional)
if command_exists psql; then
    echo "  ✅ PostgreSQL is installed"
else
    echo "  ℹ️  PostgreSQL not found (using SQLite for local development)"
fi

# Instructions for setting up API keys
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📝 NEXT STEPS:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "1. Edit .env.local and add your API keys:"
echo "   ${EDITOR:-nano} .env.local"
echo ""
echo "2. Required keys for full functionality:"
echo "   • OPENAI_API_KEY    - For AI blueprint parsing (required)"
echo "   • STRIPE_SECRET_KEY - For payment processing (optional)"
echo "   • SENDGRID_API_KEY  - For email sending (optional)"
echo ""
echo "3. The .env file loading order is:"
echo "   • .env.local (highest priority - your secrets)"
echo "   • .env       (base configuration - safe defaults)"
echo ""
echo "4. Test your configuration:"
echo "   python3 -c \"from dotenv import load_dotenv; import os; load_dotenv('.env.local'); print('✅ OpenAI key configured' if os.getenv('OPENAI_API_KEY') != 'your-openai-api-key-here' else '❌ OpenAI key not set')\""
echo ""
echo "5. For production (Render):"
echo "   Set all secret keys directly in Render's environment variables"
echo "   Do NOT upload .env.local to production"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Setup complete! Your local environment is ready."
echo "═══════════════════════════════════════════════════════════"