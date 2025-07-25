#!/usr/bin/env python3
"""
Development startup script to run both API and Celery worker locally
"""
import os
import sys
import subprocess
import signal
import time
import logging
from multiprocessing import Process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

processes = []

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutting down all processes...")
    for process in processes:
        if process.is_alive():
            process.terminate()
    time.sleep(2)
    for process in processes:
        if process.is_alive():
            process.kill()
    sys.exit(0)

def start_redis():
    """Start Redis server for local development"""
    try:
        # Check if Redis is already running
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            logger.info("Redis is already running")
            return None
    except:
        pass
    
    # Start Redis
    logger.info("Starting Redis server...")
    process = subprocess.Popen(['redis-server', '--port', '6379', '--daemonize', 'yes'])
    time.sleep(2)  # Give Redis time to start
    return process

def start_api():
    """Start FastAPI server"""
    logger.info("Starting FastAPI server...")
    os.execvp('uvicorn', ['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'])

def start_worker():
    """Start Celery worker"""
    logger.info("Starting Celery worker...")
    os.execvp('python', ['python', 'start_worker.py'])

def main():
    """Main development startup"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set environment variables for local development
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
    os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    try:
        # Start Redis
        redis_process = start_redis()
        if redis_process:
            processes.append(redis_process)
        
        # Start API server
        api_process = Process(target=start_api)
        api_process.start()
        processes.append(api_process)
        
        # Start Celery worker
        worker_process = Process(target=start_worker)
        worker_process.start()
        processes.append(worker_process)
        
        logger.info("All services started successfully!")
        logger.info("API: http://localhost:8000")
        logger.info("Health check: http://localhost:8000/health")
        logger.info("Press Ctrl+C to stop all services")
        
        # Wait for processes
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == '__main__':
    main()