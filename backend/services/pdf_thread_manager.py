"""
Thread-safe PDF handling service for AutoHVAC
Ensures PDF files are opened, processed, and closed within the same worker thread
Includes retry logic for document closed errors
"""

import os
import time
import logging
import threading
import traceback
from typing import Callable, TypeVar, Any, Dict, Optional
from contextlib import contextmanager
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PDFThreadError(Exception):
    """Custom exception for PDF threading issues"""
    pass

class PDFDocumentClosedError(PDFThreadError):
    """Exception for document closed errors"""
    pass

class PDFProcessingTimeoutError(PDFThreadError):
    """Exception for processing timeouts"""
    pass


class PDFThreadManager:
    """
    Manages PDF operations to prevent threading issues
    
    Key principles:
    1. Never pass PDF objects between threads
    2. Always open, use, and close PDF in the same thread
    3. Retry operations that fail due to document closed errors
    4. Provide clear error messages and logging
    """
    
    def __init__(self, max_workers: int = 4, default_timeout: int = 300):
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PDF_Worker")
        
    def retry_on_document_closed(
        self, 
        operation_func: Callable[[], T], 
        operation_name: str,
        max_retries: int = 2,
        retry_delay: float = 0.1
    ) -> T:
        """
        Retry wrapper for operations that might fail due to document closed errors
        
        Args:
            operation_func: Function to execute
            operation_name: Name of operation for logging
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Result of operation_func
            
        Raises:
            PDFDocumentClosedError: If max retries exceeded
            Exception: Any non-document-closed errors
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"[Thread {thread_name}:{thread_id}] Executing {operation_name} (attempt {attempt + 1}/{max_retries + 1})")
                return operation_func()
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for document closed errors - comprehensive pattern matching
                if any(error_phrase in error_str for error_phrase in [
                    "document closed", 
                    "seek of closed file", 
                    "closed file", 
                    "bad file descriptor",
                    "document has been closed",
                    "i/o operation on closed file",
                    "cannot access closed file",
                    "file is closed",
                    "invalid file descriptor",
                    "pdf document closed",
                    "stream closed"
                ]):
                    logger.error(
                        f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR on attempt {attempt + 1}/{max_retries + 1} "
                        f"in {operation_name}: {type(e).__name__}: {str(e)}"
                    )
                    logger.error(f"[Thread {thread_name}:{thread_id}] Call stack:\n{traceback.format_exc()}")
                    
                    if attempt < max_retries:
                        logger.info(f"[Thread {thread_name}:{thread_id}] Retrying {operation_name} in {retry_delay}s")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"[Thread {thread_name}:{thread_id}] Max retries ({max_retries}) exceeded for {operation_name}")
                        raise PDFDocumentClosedError(f"Max retries exceeded for {operation_name}: {str(e)}")
                else:
                    # Not a document closed error, re-raise immediately
                    logger.error(f"[Thread {thread_name}:{thread_id}] Non-retryable error in {operation_name}: {type(e).__name__}: {str(e)}")
                    raise
    
    def execute_in_worker_thread(
        self, 
        operation_func: Callable[[], T], 
        operation_name: str,
        timeout_seconds: Optional[int] = None
    ) -> T:
        """
        Execute PDF operation in a dedicated worker thread with timeout
        
        Args:
            operation_func: Function to execute in worker thread
            operation_name: Name of operation for logging
            timeout_seconds: Timeout in seconds (uses default if None)
            
        Returns:
            Result of operation_func
            
        Raises:
            PDFProcessingTimeoutError: If operation times out
            Exception: Any other errors from operation_func
        """
        timeout = timeout_seconds or self.default_timeout
        
        try:
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Submitting {operation_name} to worker thread pool (timeout: {timeout}s)")
            future = self._executor.submit(operation_func)
            result = future.result(timeout=timeout)
            logger.info(f"[Thread {thread_name}:{thread_id}] Successfully completed {operation_name} in worker thread")
            return result
            
        except FutureTimeoutError:
            error_msg = f"{operation_name} timed out after {timeout} seconds"
            logger.error(f"[Thread {thread_name}:{thread_id}] {error_msg}")
            raise PDFProcessingTimeoutError(error_msg)
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] Error in worker thread executing {operation_name}: {type(e).__name__}: {str(e)}")
            raise
    
    @contextmanager
    def safe_pdf_operation(self, pdf_path: str, operation_name: str):
        """
        Context manager for safe PDF operations
        
        Args:
            pdf_path: Path to PDF file
            operation_name: Name of operation for logging
            
        Yields:
            PDF path (to be opened by the operation)
            
        Example:
            with pdf_manager.safe_pdf_operation("/path/to/file.pdf", "text_extraction") as pdf_path:
                # Open PDF here, use it, then close it
                with pdfplumber.open(pdf_path) as pdf:
                    # Use pdf object
                    pass
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        start_time = time.time()
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting safe PDF operation: {operation_name}")
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
        
        try:
            # CRITICAL: Comprehensive file validation before PDF operations
            logger.info(f"[Thread {thread_name}:{thread_id}] Validating PDF file access")
            
            if not os.path.exists(pdf_path):
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file not found: {pdf_path}")
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            if not os.access(pdf_path, os.R_OK):
                logger.error(f"[Thread {thread_name}:{thread_id}] Cannot read PDF file: {pdf_path}")
                raise PermissionError(f"Cannot read PDF file: {pdf_path}")
            
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file is empty: {pdf_path}")
                raise ValueError(f"PDF file is empty: {pdf_path}")
            
            logger.info(f"[Thread {thread_name}:{thread_id}] PDF file validation passed - size: {file_size} bytes")
            logger.info(f"[Thread {thread_name}:{thread_id}] PDF file path: {pdf_path}")
            
            yield pdf_path
            
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] Error in safe PDF operation {operation_name}: {type(e).__name__}: {str(e)}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"[Thread {thread_name}:{thread_id}] Completed PDF operation {operation_name} in {elapsed_time:.2f}s")
    
    def process_pdf_with_retry(
        self, 
        pdf_path: str,
        processor_func: Callable[[str], T],
        operation_name: str,
        max_retries: int = 2,
        timeout_seconds: Optional[int] = None
    ) -> T:
        """
        Process PDF with retry logic and thread safety
        
        Args:
            pdf_path: Path to PDF file
            processor_func: Function that takes pdf_path and returns result
            operation_name: Name of operation for logging
            max_retries: Maximum retry attempts
            timeout_seconds: Timeout in seconds
            
        Returns:
            Result from processor_func
            
        Example:
            def extract_text(pdf_path: str) -> List[str]:
                with pdfplumber.open(pdf_path) as pdf:
                    return [page.extract_text() for page in pdf.pages]
            
            result = pdf_manager.process_pdf_with_retry(
                "/path/to/file.pdf",
                extract_text,
                "text_extraction"
            )
        """
        def wrapped_operation():
            return self.retry_on_document_closed(
                lambda: processor_func(pdf_path),
                operation_name,
                max_retries=max_retries
            )
        
        return self.execute_in_worker_thread(
            wrapped_operation,
            operation_name,
            timeout_seconds=timeout_seconds
        )
    
    def close(self):
        """Clean shutdown of thread pool"""
        logger.info("Shutting down PDF thread manager")
        self._executor.shutdown(wait=True)
        logger.info("PDF thread manager shutdown complete")


# Global instance
pdf_thread_manager = PDFThreadManager()


def pdf_operation(operation_name: str, max_retries: int = 2, timeout_seconds: Optional[int] = None):
    """
    Decorator for PDF operations that need thread safety and retry logic
    
    Args:
        operation_name: Name of operation for logging
        max_retries: Maximum retry attempts
        timeout_seconds: Timeout in seconds
        
    Example:
        @pdf_operation("geometry_extraction", max_retries=3, timeout_seconds=120)
        def extract_geometry(pdf_path: str) -> Dict[str, Any]:
            # This function will be executed with thread safety and retry logic
            with pdfplumber.open(pdf_path) as pdf:
                # Extract geometry
                return result
    """
    def decorator(func: Callable[[str], T]) -> Callable[[str], T]:
        @wraps(func)
        def wrapper(pdf_path: str) -> T:
            return pdf_thread_manager.process_pdf_with_retry(
                pdf_path=pdf_path,
                processor_func=func,
                operation_name=operation_name,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds
            )
        return wrapper
    return decorator


# Convenience functions for common operations
def safe_pdfplumber_operation(pdf_path: str, operation_func: Callable, operation_name: str, max_retries: int = 2) -> Any:
    """
    Execute pdfplumber operation with thread safety
    
    Args:
        pdf_path: Path to PDF file
        operation_func: Function that takes pdfplumber PDF object
        operation_name: Name for logging
        max_retries: Retry attempts
        
    Returns:
        Result from operation_func
    """
    def processor(path: str):
        import pdfplumber
        import threading
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF with pdfplumber: {path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Operation: {operation_name}")
        
        try:
            print(f"[Thread {thread_name}:{thread_id}] OPENING pdfplumber PDF: {path}")
            logger.info(f"[Thread {thread_name}:{thread_id}] OPENING pdfplumber PDF: {path}")
            
            with pdfplumber.open(path) as pdf:
                print(f"[Thread {thread_name}:{thread_id}] pdfplumber PDF OPENED successfully, pages: {len(pdf.pages)}")
                logger.info(f"[Thread {thread_name}:{thread_id}] pdfplumber PDF opened successfully, pages: {len(pdf.pages)}")
                
                result = operation_func(pdf)
                
                print(f"[Thread {thread_name}:{thread_id}] pdfplumber operation completed successfully")
                logger.info(f"[Thread {thread_name}:{thread_id}] pdfplumber operation completed successfully")
                return result
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] pdfplumber operation failed: {type(e).__name__}: {str(e)}")
            logger.error(f"[Thread {thread_name}:{thread_id}] PDF path: {path}")
            raise
        finally:
            print(f"[Thread {thread_name}:{thread_id}] pdfplumber PDF CLOSED automatically by context manager")
            logger.info(f"[Thread {thread_name}:{thread_id}] pdfplumber PDF closed automatically by context manager")
    
    return pdf_thread_manager.process_pdf_with_retry(
        pdf_path=pdf_path,
        processor_func=processor,
        operation_name=operation_name,
        max_retries=max_retries
    )


def safe_pymupdf_operation(pdf_path: str, operation_func: Callable, operation_name: str, max_retries: int = 2) -> Any:
    """
    Execute PyMuPDF operation with thread safety
    
    Args:
        pdf_path: Path to PDF file
        operation_func: Function that takes PyMuPDF document object
        operation_name: Name for logging
        max_retries: Retry attempts
        
    Returns:
        Result from operation_func
    """
    def processor(path: str):
        import fitz
        import threading
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF with PyMuPDF: {path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Operation: {operation_name}")
        
        doc = None
        try:
            print(f"[Thread {thread_name}:{thread_id}] OPENING PyMuPDF document: {path}")
            logger.info(f"[Thread {thread_name}:{thread_id}] OPENING PyMuPDF document: {path}")
            
            doc = fitz.open(path)
            
            print(f"[Thread {thread_name}:{thread_id}] PyMuPDF document OPENED successfully, pages: {len(doc)}")
            logger.info(f"[Thread {thread_name}:{thread_id}] PyMuPDF document opened successfully, pages: {len(doc)}")
            
            result = operation_func(doc)
            
            print(f"[Thread {thread_name}:{thread_id}] PyMuPDF operation completed successfully")
            logger.info(f"[Thread {thread_name}:{thread_id}] PyMuPDF operation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] PyMuPDF operation failed: {type(e).__name__}: {str(e)}")
            logger.error(f"[Thread {thread_name}:{thread_id}] PDF path: {path}")
            raise
        finally:
            if doc is not None:
                try:
                    print(f"[Thread {thread_name}:{thread_id}] CLOSING PyMuPDF document")
                    logger.info(f"[Thread {thread_name}:{thread_id}] Closing PyMuPDF document")
                    doc.close()
                    print(f"[Thread {thread_name}:{thread_id}] PyMuPDF document CLOSED successfully")
                    logger.info(f"[Thread {thread_name}:{thread_id}] PyMuPDF document closed successfully")
                except Exception as close_error:
                    print(f"[Thread {thread_name}:{thread_id}] ERROR closing PyMuPDF document: {close_error}")
                    logger.error(f"[Thread {thread_name}:{thread_id}] Error closing PyMuPDF document: {close_error}")
    
    return pdf_thread_manager.process_pdf_with_retry(
        pdf_path=pdf_path,
        processor_func=processor,
        operation_name=operation_name,
        max_retries=max_retries
    )


# Test functions
def test_pdf_thread_manager():
    """Test function for PDF thread manager"""
    import tempfile
    
    # Create a test PDF
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000110 00000 n\n trailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n180\n%%EOF"
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(test_pdf_content)
        temp_pdf_path = temp_file.name
    
    try:
        # Test safe operation
        def test_operation(pdf_path: str):
            # Simulate PDF processing
            time.sleep(0.1)
            return {"test": "success", "file_size": os.path.getsize(pdf_path)}
        
        result = pdf_thread_manager.process_pdf_with_retry(
            temp_pdf_path,
            test_operation,
            "test_operation"
        )
        
        logger.info(f"Test result: {result}")
        return result
        
    finally:
        # Cleanup
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)


if __name__ == "__main__":
    # Run test
    logging.basicConfig(level=logging.INFO)
    test_pdf_thread_manager()