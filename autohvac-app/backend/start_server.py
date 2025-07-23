#!/usr/bin/env python3
"""Simple server starter with better error handling for debugging"""

import sys
import os

# Ensure the backend directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Starting AutoHVAC backend server...")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")  # Show first 3 paths
    
    # Try importing main app
    print("\nImporting main app...")
    from main import app
    print("✅ Main app imported successfully")
    
    # Start uvicorn
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\nStarting server on port {port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print(f"Failed to import: {e.name if hasattr(e, 'name') else 'unknown'}")
    print("\nTrying to diagnose the issue...")
    
    # List files in current directory
    print("\nFiles in current directory:")
    for f in os.listdir('.'):
        print(f"  - {f}")
    
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Startup error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)