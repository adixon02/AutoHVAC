"""
Memory monitoring utilities for AutoHVAC worker processes
Provides real-time memory tracking and circuit breaker functionality
"""

import psutil
import os
import logging
import time
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Memory thresholds (in MB)
WARNING_THRESHOLD_MB = 1200  # 1.2GB - warn when approaching limit
CRITICAL_THRESHOLD_MB = 1400  # 1.4GB - circuit breaker to prevent OOM
MAX_MEMORY_MB = 1536  # 1.5GB - absolute maximum set in worker config


class MemoryMonitor:
    """Monitor and manage memory usage for worker processes"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = self.get_memory_usage_mb()
        self.peak_memory = self.start_memory
        self.last_check_time = time.time()
        
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            # Use RSS (Resident Set Size) for actual memory usage
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return 0.0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        current_mb = self.get_memory_usage_mb()
        self.peak_memory = max(self.peak_memory, current_mb)
        
        return {
            'current_mb': round(current_mb, 2),
            'peak_mb': round(self.peak_memory, 2),
            'start_mb': round(self.start_memory, 2),
            'increase_mb': round(current_mb - self.start_memory, 2),
            'percentage_of_limit': round((current_mb / MAX_MEMORY_MB) * 100, 1),
            'is_warning': current_mb >= WARNING_THRESHOLD_MB,
            'is_critical': current_mb >= CRITICAL_THRESHOLD_MB
        }
    
    def check_memory_circuit_breaker(self) -> bool:
        """
        Check if memory usage exceeds critical threshold
        Returns True if processing should continue, False if it should stop
        """
        stats = self.get_memory_stats()
        
        # Log memory stats periodically (every 10 seconds)
        current_time = time.time()
        if current_time - self.last_check_time > 10:
            logger.info(f"Memory usage: {stats['current_mb']:.1f}MB / {MAX_MEMORY_MB}MB "
                       f"({stats['percentage_of_limit']:.1f}%)")
            self.last_check_time = current_time
        
        # Check critical threshold
        if stats['is_critical']:
            logger.error(f"CRITICAL: Memory usage {stats['current_mb']:.1f}MB exceeds "
                        f"critical threshold {CRITICAL_THRESHOLD_MB}MB")
            logger.error(f"Circuit breaker activated to prevent worker OOM kill")
            return False
        
        # Check warning threshold
        if stats['is_warning']:
            logger.warning(f"Memory usage {stats['current_mb']:.1f}MB approaching limit "
                          f"(warning at {WARNING_THRESHOLD_MB}MB)")
        
        return True
    
    def log_final_stats(self):
        """Log final memory statistics"""
        stats = self.get_memory_stats()
        logger.info(f"Final memory stats: Current={stats['current_mb']:.1f}MB, "
                   f"Peak={stats['peak_mb']:.1f}MB, "
                   f"Increase={stats['increase_mb']:.1f}MB")


def monitor_memory(func):
    """
    Decorator to monitor memory usage during function execution
    
    Usage:
        @monitor_memory
        def process_large_pdf(pdf_path):
            # ... processing logic ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = MemoryMonitor()
        func_name = func.__name__
        
        logger.info(f"[MEMORY] Starting {func_name} - Initial: {monitor.start_memory:.1f}MB")
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            stats = monitor.get_memory_stats()
            logger.info(f"[MEMORY] Completed {func_name} - "
                       f"Final: {stats['current_mb']:.1f}MB, "
                       f"Peak: {stats['peak_mb']:.1f}MB, "
                       f"Increase: {stats['increase_mb']:.1f}MB")
    
    return wrapper


def check_memory_available(required_mb: float = 500) -> bool:
    """
    Check if sufficient memory is available for an operation
    
    Args:
        required_mb: Estimated memory required in MB
        
    Returns:
        True if sufficient memory available, False otherwise
    """
    monitor = MemoryMonitor()
    current_mb = monitor.get_memory_usage_mb()
    available_mb = MAX_MEMORY_MB - current_mb
    
    if available_mb < required_mb:
        logger.warning(f"Insufficient memory: {available_mb:.1f}MB available, "
                      f"{required_mb:.1f}MB required")
        return False
    
    return True


# Example usage in text parser
def memory_safe_word_extraction(page, thread_id: str, thread_name: str) -> list:
    """
    Extract words with memory monitoring and circuit breaker
    
    This function can be used in text_parser.py to safely extract words
    while monitoring memory usage
    """
    monitor = MemoryMonitor()
    words = []
    
    try:
        raw_words = page.extract_words()
        total_words = len(raw_words)
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Extracting {total_words} words "
                   f"(Memory: {monitor.get_memory_usage_mb():.1f}MB)")
        
        # Process in batches with memory checks
        BATCH_SIZE = 1000
        
        for i in range(0, total_words, BATCH_SIZE):
            # Check memory circuit breaker
            if not monitor.check_memory_circuit_breaker():
                logger.warning(f"Memory circuit breaker triggered at word {i}/{total_words}")
                logger.warning(f"Returning {len(words)} words processed so far")
                break
            
            # Process batch
            batch = raw_words[i:i + BATCH_SIZE]
            for word in batch:
                height = float(word['bottom'] - word['top'])
                words.append({
                    'text': str(word['text']),
                    'x0': float(word['x0']),
                    'top': float(word['top']),
                    'x1': float(word['x1']),
                    'bottom': float(word['bottom']),
                    'width': float(word['x1'] - word['x0']),
                    'height': height,
                    'size': float(word.get('size', height)),
                    'font': word.get('fontname', ''),
                    'source': 'pdfplumber'
                })
            
            if (i + BATCH_SIZE) % 5000 == 0:
                stats = monitor.get_memory_stats()
                logger.info(f"Progress: {i + len(batch)}/{total_words} words, "
                           f"Memory: {stats['current_mb']:.1f}MB ({stats['percentage_of_limit']:.1f}%)")
        
        monitor.log_final_stats()
        return words
        
    except Exception as e:
        stats = monitor.get_memory_stats()
        logger.error(f"Error during word extraction at {stats['current_mb']:.1f}MB: {e}")
        raise


# Global monitor instance for worker-wide tracking
_global_monitor: Optional[MemoryMonitor] = None


def get_global_monitor() -> MemoryMonitor:
    """Get or create global memory monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = MemoryMonitor()
    return _global_monitor


def log_worker_memory_stats():
    """Log current worker memory statistics"""
    monitor = get_global_monitor()
    stats = monitor.get_memory_stats()
    
    logger.info(f"[WORKER MEMORY] Current: {stats['current_mb']:.1f}MB, "
               f"Peak: {stats['peak_mb']:.1f}MB, "
               f"Limit: {MAX_MEMORY_MB}MB ({stats['percentage_of_limit']:.1f}% used)")
    
    return stats