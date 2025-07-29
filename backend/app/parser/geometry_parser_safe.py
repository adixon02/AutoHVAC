"""
Safe geometry parser with timeout protection and comprehensive error handling
Prevents hanging on problematic PDFs and provides detailed diagnostics
"""

import os
import time
import logging
import traceback
import psutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Dict, Any
import fitz  # PyMuPDF

from .geometry_parser import GeometryParser
from .schema import RawGeometry

logger = logging.getLogger(__name__)


class GeometryParserTimeout(Exception):
    """Raised when geometry parsing exceeds timeout"""
    pass


class GeometryParserSafe:
    """Thread-safe geometry parser with timeout and resource monitoring"""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.parser = GeometryParser()
    
    def parse(self, pdf_path: str) -> RawGeometry:
        """
        Parse PDF geometry with timeout protection and comprehensive error handling
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            RawGeometry object
            
        Raises:
            GeometryParserTimeout: If parsing exceeds timeout
            ValueError: If PDF is invalid or unsupported
            Exception: For other parsing failures
        """
        start_time = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"Starting geometry parsing for {pdf_path}")
        logger.info(f"File size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Validate PDF before processing
        try:
            self._validate_pdf(pdf_path)
        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            raise ValueError(f"Invalid PDF file: {str(e)}")
        
        # Parse with timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            logger.info(f"Submitting geometry parsing task with {self.timeout}s timeout")
            future = executor.submit(self._parse_with_monitoring, pdf_path)
            
            try:
                result = future.result(timeout=self.timeout)
                
                # Log success metrics
                end_time = time.time()
                final_memory = process.memory_info().rss / 1024 / 1024
                logger.info(f"Geometry parsing completed successfully")
                logger.info(f"Duration: {end_time - start_time:.2f}s")
                logger.info(f"Memory delta: {final_memory - initial_memory:.2f} MB")
                
                return result
                
            except FutureTimeoutError:
                # Timeout occurred
                logger.error(f"Geometry parsing timed out after {self.timeout}s")
                logger.error(f"PDF file: {pdf_path}")
                
                # Try to get current memory usage
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    logger.error(f"Memory at timeout: {current_memory:.2f} MB (delta: {current_memory - initial_memory:.2f} MB)")
                except:
                    pass
                
                # Cancel the future and shut down executor
                future.cancel()
                executor.shutdown(wait=False)
                
                raise GeometryParserTimeout(
                    f"Geometry parsing exceeded {self.timeout}s timeout. "
                    f"PDF may be too complex or corrupted."
                )
                
            except Exception as e:
                # Other exceptions from the parsing thread
                logger.error(f"Geometry parsing failed with exception: {type(e).__name__}: {str(e)}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                
                # Re-raise with additional context
                raise Exception(f"Geometry parsing failed: {str(e)}") from e
    
    def _validate_pdf(self, pdf_path: str) -> None:
        """
        Validate PDF file before processing
        
        Raises:
            ValueError: If PDF is invalid or unsupported
        """
        # Check file exists
        if not os.path.exists(pdf_path):
            raise ValueError("PDF file does not exist")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            raise ValueError("PDF file is empty")
        
        # Check PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                raise ValueError("File is not a valid PDF")
        
        # Try to open with PyMuPDF for basic validation
        try:
            doc = fitz.open(pdf_path)
            
            # Check if encrypted
            if doc.is_encrypted:
                doc.close()
                raise ValueError("PDF is encrypted/password protected")
            
            # Check page count
            page_count = len(doc)
            if page_count == 0:
                doc.close()
                raise ValueError("PDF has no pages")
            
            if page_count > 100:
                logger.warning(f"PDF has {page_count} pages - processing only first page")
            
            # Check if we can access first page
            try:
                page = doc[0]
                _ = page.rect  # Try to access page rectangle
            except Exception as e:
                doc.close()
                raise ValueError(f"Cannot access PDF page: {str(e)}")
            
            doc.close()
            
        except fitz.FileDataError as e:
            raise ValueError(f"PyMuPDF cannot read PDF: {str(e)}")
        except Exception as e:
            raise ValueError(f"PDF validation failed: {str(e)}")
        
        logger.info(f"PDF validation passed: {page_count} pages")
    
    def _parse_with_monitoring(self, pdf_path: str) -> RawGeometry:
        """
        Execute parsing with detailed monitoring and error handling
        This runs in the thread pool executor
        """
        try:
            # Set thread name for debugging
            import threading
            threading.current_thread().name = "GeometryParser"
            
            logger.info("Starting geometry extraction in worker thread")
            
            # Add checkpoints throughout parsing
            checkpoint_start = time.time()
            
            # Call the actual parser
            result = self.parser.parse(pdf_path)
            
            checkpoint_end = time.time()
            logger.info(f"Geometry extraction completed in {checkpoint_end - checkpoint_start:.2f}s")
            
            # Validate result
            if not result:
                raise ValueError("Parser returned None")
            
            if not hasattr(result, 'lines') or not hasattr(result, 'rectangles'):
                raise ValueError("Parser returned incomplete geometry data")
            
            # Log extraction summary
            logger.info(f"Extracted geometry summary:")
            logger.info(f"  - Lines: {len(result.lines)}")
            logger.info(f"  - Rectangles: {len(result.rectangles)}")
            logger.info(f"  - Polylines: {len(result.polylines)}")
            logger.info(f"  - Page size: {result.page_width} x {result.page_height}")
            
            return result
            
        except Exception as e:
            # Log any exception with full context
            logger.error(f"Exception in geometry parser thread: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            # Add thread info
            logger.error(f"Thread: {threading.current_thread().name}")
            logger.error(f"PDF path: {pdf_path}")
            
            # Re-raise for the main thread to handle
            raise


def create_safe_parser(timeout: int = 60) -> GeometryParserSafe:
    """Factory function to create a safe geometry parser"""
    return GeometryParserSafe(timeout=timeout)