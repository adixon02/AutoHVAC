#!/bin/bash

echo "🚀 Starting AutoHVAC Backend (Simple Mode)..."
echo ""
echo "⚠️  Running without Redis/Celery - using in-memory job processing"
echo "⚠️  This is suitable for development and testing only"
echo ""

cd "$(dirname "$0")"

# Start the server
python3 -c "
import subprocess
import sys

print('🔍 Checking Python version...')
print(f'Python {sys.version}')

try:
    import uvicorn
    print('✅ Uvicorn is installed')
except ImportError:
    print('❌ Uvicorn not found. Installing...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uvicorn[standard]'])

print('')
print('🌐 Starting server on http://localhost:8000')
print('📖 API docs: http://localhost:8000/docs')
print('🔍 Health check: http://localhost:8000/healthz')
print('')
print('Press Ctrl+C to stop')
print('')

subprocess.run([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'])
"