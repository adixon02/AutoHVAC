"""
Safe geometry parser with timeout protection and comprehensive error handling
Prevents hanging on problematic PDFs and provides detailed diagnostics
"""

import os
import time
import logging
import traceback
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Dict, Any
import fitz  # PyMuPDF

from .geometry_parser import GeometryParser
from .schema import RawGeometry

logger = logging.getLogger(__name__)

# Complexity limits for multi-page processing
MAX_ELEMENTS_PER_PAGE = 20000
MAX_LINES_PER_PAGE = 15000
MAX_RECTANGLES_PER_PAGE = 5000


class GeometryParserTimeout(Exception):
    """Raised when geometry parsing exceeds timeout"""
    pass


class GeometryParserComplexity(Exception):
    """Raised when geometry is too complex to process safely"""
    pass


class GeometryParserSafe:
    """Thread-safe geometry parser with timeout and resource monitoring"""
    
    def __init__(self, timeout: int = 300, enable_complexity_checks: bool = True):
        self.timeout = timeout
        self.enable_complexity_checks = enable_complexity_checks
        self.parser = GeometryParser()
    
    def parse(self, pdf_path: str, page_number: Optional[int] = None) -> RawGeometry:
        """
        Parse PDF geometry with optional page selection
        
        Args:
            pdf_path: Path to PDF file
            page_number: Optional zero-based page number (if None, parses first page)
            
        Returns:
            RawGeometry object for specified page
        """
        if page_number is not None:
            return self.parse_specific_page(pdf_path, page_number)
        else:
            return self.parse_first_page(pdf_path)
    
    def parse_first_page(self, pdf_path: str) -> RawGeometry:
        """
        Parse first page of PDF geometry (legacy method for backward compatibility)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            RawGeometry object
            
        Raises:
            GeometryParserTimeout: If parsing exceeds timeout
            GeometryParserComplexity: If page is too complex
            ValueError: If PDF is invalid or unsupported
            Exception: For other parsing failures
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        start_time = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting geometry parsing for {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] File size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
        logger.info(f"[Thread {thread_name}:{thread_id}] Initial memory usage: {initial_memory:.2f} MB")
        
        # Validate PDF before processing
        try:
            self._validate_pdf(pdf_path)
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] PDF validation failed: {e}")
            raise ValueError(f"Invalid PDF file: {str(e)}")
        
        # Parse with timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            logger.info(f"[Thread {thread_name}:{thread_id}] Submitting geometry parsing task with {self.timeout}s timeout")
            future = executor.submit(self._parse_with_monitoring, pdf_path)
            
            try:
                result = future.result(timeout=self.timeout)
                
                # Log success metrics
                end_time = time.time()
                final_memory = process.memory_info().rss / 1024 / 1024
                logger.info(f"[Thread {thread_name}:{thread_id}] Geometry parsing completed successfully")
                logger.info(f"[Thread {thread_name}:{thread_id}] Duration: {end_time - start_time:.2f}s")
                logger.info(f"[Thread {thread_name}:{thread_id}] Memory delta: {final_memory - initial_memory:.2f} MB")
                
                return result
                
            except FutureTimeoutError:
                # Timeout occurred
                logger.error(f"[Thread {thread_name}:{thread_id}] Geometry parsing timed out after {self.timeout}s")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                
                # Try to get current memory usage
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    logger.error(f"[Thread {thread_name}:{thread_id}] Memory at timeout: {current_memory:.2f} MB (delta: {current_memory - initial_memory:.2f} MB)")
                except:
                    pass
                
                # Cancel the future and shut down executor
                future.cancel()
                executor.shutdown(wait=False)
                
                raise GeometryParserTimeout(
                    f"Geometry parsing exceeded {self.timeout}s timeout (5 minutes). "
                    f"PDF may be too complex or corrupted."
                )
                
            except Exception as e:
                # Other exceptions from the parsing thread
                logger.error(f"[Thread {thread_name}:{thread_id}] Geometry parsing failed with exception: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
                
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
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF validation passed: {page_count} pages")
    
    def parse_specific_page(self, pdf_path: str, page_number: int) -> RawGeometry:
        """
        Parse specific page of PDF with complexity pre-checks
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number to parse
            
        Returns:
            RawGeometry object for the specified page
            
        Raises:
            GeometryParserTimeout: If parsing exceeds timeout
            GeometryParserComplexity: If page is too complex
            ValueError: If PDF is invalid or page doesn't exist
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        start_time = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting geometry parsing for page {page_number + 1} of {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] File size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
        logger.info(f"[Thread {thread_name}:{thread_id}] Initial memory usage: {initial_memory:.2f} MB")
        
        # Validate PDF and check page exists
        try:
            self._validate_pdf_and_page(pdf_path, page_number)
        except Exception as e:
            logger.error(f"[Thread {thread_name}:{thread_id}] PDF/page validation failed: {e}")
            raise ValueError(f"Invalid PDF or page: {str(e)}")
        
        # Pre-check page complexity if enabled
        if self.enable_complexity_checks:
            try:
                self._check_page_complexity(pdf_path, page_number)
            except GeometryParserComplexity as e:
                logger.error(f"[Thread {thread_name}:{thread_id}] Page complexity check failed: {e}")
                raise
        
        # Parse with timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            logger.info(f"[Thread {thread_name}:{thread_id}] Submitting page {page_number + 1} geometry parsing task with {self.timeout}s timeout")
            future = executor.submit(self._parse_page_with_monitoring, pdf_path, page_number)
            
            try:
                result = future.result(timeout=self.timeout)
                
                # Log success metrics
                end_time = time.time()
                final_memory = process.memory_info().rss / 1024 / 1024
                logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} geometry parsing completed successfully")
                logger.info(f"[Thread {thread_name}:{thread_id}] Duration: {end_time - start_time:.2f}s")
                logger.info(f"[Thread {thread_name}:{thread_id}] Memory delta: {final_memory - initial_memory:.2f} MB")
                
                return result
                
            except FutureTimeoutError:
                # Timeout occurred
                logger.error(f"[Thread {thread_name}:{thread_id}] Geometry parsing timed out after {self.timeout}s for page {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                
                # Try to get current memory usage
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    logger.error(f"[Thread {thread_name}:{thread_id}] Memory at timeout: {current_memory:.2f} MB (delta: {current_memory - initial_memory:.2f} MB)")
                except:
                    pass
                
                # Cancel the future and shut down executor
                future.cancel()
                executor.shutdown(wait=False)
                
                raise GeometryParserTimeout(
                    f"Geometry parsing exceeded {self.timeout}s timeout (5 minutes) for page {page_number + 1}. "
                    f"Page may be too complex or corrupted."
                )
                
            except Exception as e:
                # Other exceptions from the parsing thread
                logger.error(f"[Thread {thread_name}:{thread_id}] Geometry parsing failed for page {page_number + 1}: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
                
                # Re-raise with additional context
                raise Exception(f"Geometry parsing failed for page {page_number + 1}: {str(e)}") from e
    
    def _validate_pdf_and_page(self, pdf_path: str, page_number: int) -> None:
        """
        Validate PDF file and check that specified page exists
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number
            
        Raises:
            ValueError: If PDF is invalid or page doesn't exist
        """
        # First do basic PDF validation
        self._validate_pdf(pdf_path)
        
        # Check specific page exists
        try:
            doc = fitz.open(pdf_path)
            
            if page_number >= len(doc) or page_number < 0:
                doc.close()
                raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(doc)} pages)")
            
            # Try to access the specific page
            try:
                page = doc[page_number]
                _ = page.rect  # Try to access page rectangle
            except Exception as e:
                doc.close()
                raise ValueError(f"Cannot access page {page_number + 1}: {str(e)}")
            
            doc.close()
            
        except fitz.FileDataError as e:
            raise ValueError(f"PyMuPDF cannot read PDF: {str(e)}")
        except Exception as e:
            raise ValueError(f"Page validation failed: {str(e)}")
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} validation passed")
    
    def _check_page_complexity(self, pdf_path: str, page_number: int) -> None:
        """
        Pre-check page complexity before attempting full parsing
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number
            
        Raises:
            GeometryParserComplexity: If page is too complex to process safely
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_number]
            
            # Quick complexity assessment using PyMuPDF
            drawings = page.get_drawings()
            element_count = len(drawings)
            
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} complexity check: {element_count} drawing elements")
            
            if element_count > MAX_ELEMENTS_PER_PAGE:
                doc.close()
                raise GeometryParserComplexity(
                    f"Page {page_number + 1} has {element_count} elements, "
                    f"exceeding limit of {MAX_ELEMENTS_PER_PAGE}. "
                    f"This page is too complex to process safely."
                )
            
            # Additional complexity checks
            line_count = 0
            rect_count = 0
            
            for drawing in drawings[:1000]:  # Sample first 1000 elements for speed
                if 'items' in drawing:
                    for item in drawing['items']:
                        if item[0] == 'l':  # Line
                            line_count += 1
                        elif item[0] == 're':  # Rectangle
                            rect_count += 1
            
            # Extrapolate counts
            if len(drawings) > 1000:
                scale_factor = len(drawings) / 1000
                line_count = int(line_count * scale_factor)
                rect_count = int(rect_count * scale_factor)
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} estimated: {line_count} lines, {rect_count} rectangles")
            
            if line_count > MAX_LINES_PER_PAGE:
                doc.close()
                raise GeometryParserComplexity(
                    f"Page {page_number + 1} has approximately {line_count} lines, "
                    f"exceeding limit of {MAX_LINES_PER_PAGE}."
                )
            
            if rect_count > MAX_RECTANGLES_PER_PAGE:
                doc.close()
                raise GeometryParserComplexity(
                    f"Page {page_number + 1} has approximately {rect_count} rectangles, "
                    f"exceeding limit of {MAX_RECTANGLES_PER_PAGE}."
                )
            
            doc.close()
            logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} complexity check passed")
            
        except GeometryParserComplexity:
            # Re-raise complexity errors
            raise
        except Exception as e:
            logger.warning(f"[Thread {thread_name}:{thread_id}] Complexity check failed for page {page_number + 1}: {e}")
            # Don't fail on complexity check errors, just log and continue
    
    def _parse_with_monitoring(self, pdf_path: str) -> RawGeometry:
        """
        Execute parsing with detailed monitoring and error handling
        This runs in the thread pool executor
        """
        try:
            # Set thread name for debugging
            import threading
            threading.current_thread().name = "GeometryParser"
            
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            logger.info(f"[Thread {thread_name}:{thread_id}] Starting geometry extraction in worker thread")
            
            # Add checkpoints throughout parsing
            checkpoint_start = time.time()
            
            # Call the actual parser
            result = self.parser.parse(pdf_path)
            
            checkpoint_end = time.time()
            logger.info(f"[Thread {thread_name}:{thread_id}] Geometry extraction completed in {checkpoint_end - checkpoint_start:.2f}s")
            
            # Validate result
            if not result:
                raise ValueError("Parser returned None")
            
            if not hasattr(result, 'lines') or not hasattr(result, 'rectangles'):
                raise ValueError("Parser returned incomplete geometry data")
            
            # Log extraction summary
            logger.info(f"[Thread {thread_name}:{thread_id}] Extracted geometry summary:")
            logger.info(f"[Thread {thread_name}:{thread_id}]   - Lines: {len(result.lines)}")
            logger.info(f"[Thread {thread_name}:{thread_id}]   - Rectangles: {len(result.rectangles)}")
            logger.info(f"[Thread {thread_name}:{thread_id}]   - Polylines: {len(result.polylines)}")
            logger.info(f"[Thread {thread_name}:{thread_id}]   - Page size: {result.page_width} x {result.page_height}")
            
            return result
            
        except Exception as e:
            # Log any exception with full context
            logger.error(f"[Thread {thread_name}:{thread_id}] Exception in geometry parser thread: {type(e).__name__}: {str(e)}")
            logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            logger.error(f"[Thread {thread_name}:{thread_id}] PDF path: {pdf_path}")
            
            # Re-raise for the main thread to handle
            raise
    
    def _parse_page_with_monitoring(self, pdf_path: str, page_number: int) -> RawGeometry:
        """
        Execute page-specific parsing with detailed monitoring and error handling
        This runs in the thread pool executor
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number to parse
            
        Returns:
            RawGeometry object for the specified page
        """
        try:
            # Set thread name for debugging
            import threading
            threading.current_thread().name = f"GeometryParser-Page{page_number + 1}"
            
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            logger.info(f"[Thread {thread_name}:{thread_id}] Starting geometry extraction for page {page_number + 1} in worker thread")
            logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
            
            # Add checkpoints throughout parsing
            checkpoint_start = time.time()
            
            # CRITICAL: All PDF operations (create temp file, parse, cleanup) happen in this worker thread
            # Create a temporary single-page PDF for parsing - ENTIRELY IN THIS THREAD
            temp_single_page_path = self._extract_single_page_in_worker(pdf_path, page_number)
            
            try:
                logger.info(f"[Thread {thread_name}:{thread_id}] Parsing single-page PDF: {temp_single_page_path}")
                # Parse the single page
                result = self.parser.parse(temp_single_page_path)
                
                checkpoint_end = time.time()
                logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} geometry extraction completed in {checkpoint_end - checkpoint_start:.2f}s")
                
                # Validate result
                if not result:
                    raise ValueError("Parser returned None")
                
                if not hasattr(result, 'lines') or not hasattr(result, 'rectangles'):
                    raise ValueError("Parser returned incomplete geometry data")
                
                # Log extraction summary
                logger.info(f"[Thread {thread_name}:{thread_id}] Extracted geometry summary for page {page_number + 1}:")
                logger.info(f"[Thread {thread_name}:{thread_id}]   - Lines: {len(result.lines)}")
                logger.info(f"[Thread {thread_name}:{thread_id}]   - Rectangles: {len(result.rectangles)}")
                logger.info(f"[Thread {thread_name}:{thread_id}]   - Polylines: {len(result.polylines)}")
                logger.info(f"[Thread {thread_name}:{thread_id}]   - Page size: {result.page_width} x {result.page_height}")
                
                return result
                
            finally:
                # CRITICAL: Clean up temporary file in the SAME THREAD that created it
                if os.path.exists(temp_single_page_path):
                    try:
                        print(f"[Thread {thread_name}:{thread_id}] DELETING temporary file: {temp_single_page_path}")
                        logger.info(f"[Thread {thread_name}:{thread_id}] Cleaning up temporary file in worker thread: {temp_single_page_path}")
                        os.unlink(temp_single_page_path)
                        print(f"[Thread {thread_name}:{thread_id}] Successfully DELETED temporary file")
                        logger.info(f"[Thread {thread_name}:{thread_id}] Successfully cleaned up temporary file")
                    except Exception as cleanup_error:
                        print(f"[Thread {thread_name}:{thread_id}] ERROR deleting temporary file: {cleanup_error}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Failed to clean up temporary file {temp_single_page_path}: {cleanup_error}")
            
        except Exception as e:
            error_str = str(e).lower()
            
            # CRITICAL: Check for document closed errors and log full context
            if any(error_phrase in error_str for error_phrase in [
                "document closed", 
                "seek of closed file", 
                "closed file", 
                "bad file descriptor",
                "document has been closed"
            ]):
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in page parsing for page {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                # Log any other exception with full context
                logger.error(f"[Thread {thread_name}:{thread_id}] Exception in geometry parser thread for page {page_number + 1}: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            
            # Re-raise for the main thread to handle
            raise
    
    def _extract_single_page_in_worker(self, pdf_path: str, page_number: int) -> str:
        """
        Extract a single page to a temporary PDF file
        CRITICAL: This runs ENTIRELY in the worker thread - create temp file, process, return path
        The calling function is responsible for cleanup in the same thread
        
        Args:
            pdf_path: Original PDF path
            page_number: Zero-based page number
            
        Returns:
            Path to temporary single-page PDF (to be cleaned up by caller in same thread)
        """
        import tempfile
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting single-page extraction for page {page_number + 1}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Source PDF: {pdf_path}")
        
        # CRITICAL: Create temporary file in worker thread
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix=f'page_{page_number + 1}_')
        os.close(temp_fd)
        print(f"[Thread {thread_name}:{thread_id}] CREATED temporary file: {temp_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Created temporary file: {temp_path}")
        
        source_doc = None
        target_doc = None
        
        try:
            logger.info(f"[Thread {thread_name}:{thread_id}] Opening source PDF in worker thread: {pdf_path}")
            # CRITICAL: Open source document in worker thread - NEVER pass to another thread
            source_doc = fitz.open(pdf_path)
            logger.info(f"[Thread {thread_name}:{thread_id}] Source document opened successfully, pages: {len(source_doc)}")
            
            # Validate page number
            if page_number >= len(source_doc) or page_number < 0:
                raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(source_doc)} pages)")
            
            # Create new document with just the target page
            logger.info(f"[Thread {thread_name}:{thread_id}] Creating single-page document for page {page_number + 1}")
            target_doc = fitz.open()  # Create empty document
            target_doc.insert_pdf(source_doc, from_page=page_number, to_page=page_number)
            logger.info(f"[Thread {thread_name}:{thread_id}] Inserted page {page_number + 1} into target document")
            
            # Save to temporary file
            logger.info(f"[Thread {thread_name}:{thread_id}] Saving single page to: {temp_path}")
            target_doc.save(temp_path)
            
            # Verify file was created
            if not os.path.exists(temp_path):
                raise Exception(f"Temporary file was not created: {temp_path}")
            
            file_size = os.path.getsize(temp_path)
            logger.info(f"[Thread {thread_name}:{thread_id}] Page {page_number + 1} extracted successfully to temporary file, size: {file_size} bytes")
            return temp_path
            
        except Exception as e:
            error_str = str(e).lower()
            
            # CRITICAL: Check for document closed errors and log full context
            if any(error_phrase in error_str for error_phrase in [
                "document closed", 
                "seek of closed file", 
                "closed file", 
                "bad file descriptor",
                "document has been closed"
            ]):
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in page extraction")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Source PDF: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Temp file: {temp_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                logger.error(f"[Thread {thread_name}:{thread_id}] Failed to extract page {page_number + 1}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF path: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Temp path: {temp_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            
            # Clean up temp file on failure in the same thread
            if os.path.exists(temp_path):
                try:
                    print(f"[Thread {thread_name}:{thread_id}] CLEANING UP failed temp file: {temp_path}")
                    logger.info(f"[Thread {thread_name}:{thread_id}] Cleaning up failed temp file: {temp_path}")
                    os.unlink(temp_path)
                    print(f"[Thread {thread_name}:{thread_id}] Failed temp file CLEANED UP successfully")
                except Exception as cleanup_error:
                    print(f"[Thread {thread_name}:{thread_id}] ERROR cleaning up failed temp file: {cleanup_error}")
                    logger.error(f"[Thread {thread_name}:{thread_id}] Failed to cleanup temp file: {cleanup_error}")
            
            raise Exception(f"Failed to extract page {page_number + 1}: {str(e)}")
            
        finally:
            # CRITICAL: Clean up PDF documents in the same thread that opened them
            if target_doc is not None:
                try:
                    logger.info(f"[Thread {thread_name}:{thread_id}] Closing target document")
                    target_doc.close()
                    logger.info(f"[Thread {thread_name}:{thread_id}] Target document closed successfully")
                except Exception as e:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Error closing target document: {e}")
                    
            if source_doc is not None:
                try:
                    logger.info(f"[Thread {thread_name}:{thread_id}] Closing source document")
                    source_doc.close()
                    logger.info(f"[Thread {thread_name}:{thread_id}] Source document closed successfully")
                except Exception as e:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Error closing source document: {e}")


def create_safe_parser(timeout: int = 300, enable_complexity_checks: bool = True) -> GeometryParserSafe:
    """Factory function to create a safe geometry parser"""
    return GeometryParserSafe(timeout=timeout, enable_complexity_checks=enable_complexity_checks)