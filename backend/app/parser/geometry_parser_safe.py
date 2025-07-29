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
    
    def __init__(self, timeout: int = 60, enable_complexity_checks: bool = True):
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
        start_time = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"Starting geometry parsing for page {page_number + 1} of {pdf_path}")
        logger.info(f"File size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Validate PDF and check page exists
        try:
            self._validate_pdf_and_page(pdf_path, page_number)
        except Exception as e:
            logger.error(f"PDF/page validation failed: {e}")
            raise ValueError(f"Invalid PDF or page: {str(e)}")
        
        # Pre-check page complexity if enabled
        if self.enable_complexity_checks:
            try:
                self._check_page_complexity(pdf_path, page_number)
            except GeometryParserComplexity as e:
                logger.error(f"Page complexity check failed: {e}")
                raise
        
        # Parse with timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            logger.info(f"Submitting page {page_number + 1} geometry parsing task with {self.timeout}s timeout")
            future = executor.submit(self._parse_page_with_monitoring, pdf_path, page_number)
            
            try:
                result = future.result(timeout=self.timeout)
                
                # Log success metrics
                end_time = time.time()
                final_memory = process.memory_info().rss / 1024 / 1024
                logger.info(f"Page {page_number + 1} geometry parsing completed successfully")
                logger.info(f"Duration: {end_time - start_time:.2f}s")
                logger.info(f"Memory delta: {final_memory - initial_memory:.2f} MB")
                
                return result
                
            except FutureTimeoutError:
                # Timeout occurred
                logger.error(f"Geometry parsing timed out after {self.timeout}s for page {page_number + 1}")
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
                    f"Geometry parsing exceeded {self.timeout}s timeout for page {page_number + 1}. "
                    f"Page may be too complex or corrupted."
                )
                
            except Exception as e:
                # Other exceptions from the parsing thread
                logger.error(f"Geometry parsing failed for page {page_number + 1}: {type(e).__name__}: {str(e)}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                
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
        
        logger.info(f"Page {page_number + 1} validation passed")
    
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
            
            logger.info(f"Page {page_number + 1} complexity check: {element_count} drawing elements")
            
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
            
            logger.info(f"Page {page_number + 1} estimated: {line_count} lines, {rect_count} rectangles")
            
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
            logger.info(f"Page {page_number + 1} complexity check passed")
            
        except GeometryParserComplexity:
            # Re-raise complexity errors
            raise
        except Exception as e:
            logger.warning(f"Complexity check failed for page {page_number + 1}: {e}")
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
            
            logger.info(f"Starting geometry extraction for page {page_number + 1} in worker thread")
            
            # Add checkpoints throughout parsing
            checkpoint_start = time.time()
            
            # Call the actual parser - we need to modify it to accept page numbers
            # For now, we'll use a temporary approach where we extract just one page
            # In production, you'd want to modify GeometryParser to support page selection
            
            # Create a temporary single-page PDF for parsing
            temp_single_page_path = self._extract_single_page(pdf_path, page_number)
            
            try:
                # Parse the single page
                result = self.parser.parse(temp_single_page_path)
                
                checkpoint_end = time.time()
                logger.info(f"Page {page_number + 1} geometry extraction completed in {checkpoint_end - checkpoint_start:.2f}s")
                
                # Validate result
                if not result:
                    raise ValueError("Parser returned None")
                
                if not hasattr(result, 'lines') or not hasattr(result, 'rectangles'):
                    raise ValueError("Parser returned incomplete geometry data")
                
                # Log extraction summary
                logger.info(f"Extracted geometry summary for page {page_number + 1}:")
                logger.info(f"  - Lines: {len(result.lines)}")
                logger.info(f"  - Rectangles: {len(result.rectangles)}")
                logger.info(f"  - Polylines: {len(result.polylines)}")
                logger.info(f"  - Page size: {result.page_width} x {result.page_height}")
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_single_page_path):
                    try:
                        os.unlink(temp_single_page_path)
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary file {temp_single_page_path}: {e}")
            
        except Exception as e:
            # Log any exception with full context
            logger.error(f"Exception in geometry parser thread for page {page_number + 1}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            # Add thread info
            logger.error(f"Thread: {threading.current_thread().name}")
            logger.error(f"PDF path: {pdf_path}")
            logger.error(f"Page number: {page_number + 1}")
            
            # Re-raise for the main thread to handle
            raise
    
    def _extract_single_page(self, pdf_path: str, page_number: int) -> str:
        """
        Extract a single page to a temporary PDF file
        
        Args:
            pdf_path: Original PDF path
            page_number: Zero-based page number
            
        Returns:
            Path to temporary single-page PDF
        """
        import tempfile
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix=f'page_{page_number + 1}_')
        os.close(temp_fd)
        
        try:
            # Open source document
            source_doc = fitz.open(pdf_path)
            
            # Create new document with just the target page
            target_doc = fitz.open()
            target_doc.insert_pdf(source_doc, from_page=page_number, to_page=page_number)
            
            # Save to temporary file
            target_doc.save(temp_path)
            
            # Clean up
            target_doc.close()
            source_doc.close()
            
            logger.debug(f"Extracted page {page_number + 1} to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise Exception(f"Failed to extract page {page_number + 1}: {str(e)}")


def create_safe_parser(timeout: int = 60, enable_complexity_checks: bool = True) -> GeometryParserSafe:
    """Factory function to create a safe geometry parser"""
    return GeometryParserSafe(timeout=timeout, enable_complexity_checks=enable_complexity_checks)