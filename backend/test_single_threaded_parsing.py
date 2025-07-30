#!/usr/bin/env python3
"""
Single-Threaded PDF Parser Test Utility
Created to debug "document closed" errors by running parsing entirely in main thread

This script bypasses all threading and runs PDF parsing operations directly
in the main thread for comparison with threaded operations.

Usage:
    python test_single_threaded_parsing.py /path/to/test.pdf [page_number]
"""

import os
import sys
import time
import logging
import traceback
import threading
from typing import Optional, Dict, Any

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import parsers directly
from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser
from app.parser.schema import RawGeometry, RawText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SingleThreadedPDFTester:
    """
    Test utility that runs PDF parsing entirely in the main thread
    No threading, no thread managers, no worker pools - just direct operations
    """
    
    def __init__(self):
        self.geometry_parser = GeometryParser()
        self.text_parser = TextParser()
    
    def test_geometry_parsing(self, pdf_path: str, page_number: int = 0) -> Optional[RawGeometry]:
        """
        Test geometry parsing in main thread only
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number
            
        Returns:
            RawGeometry object or None if failed
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Testing geometry parsing in main thread")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Page number: {page_number + 1}")
        
        start_time = time.time()
        
        try:
            # DIRECT CALL - no threading, no thread manager
            result = self._parse_geometry_direct(pdf_path, page_number)
            
            end_time = time.time()
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Geometry parsing completed in {end_time - start_time:.2f}s")
            
            if result:
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Results: {len(result.lines)} lines, {len(result.rectangles)} rectangles, {len(result.polylines)} polylines")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Geometry parsing failed after {end_time - start_time:.2f}s")
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Error: {type(e).__name__}: {str(e)}")
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Full traceback:\\n{traceback.format_exc()}")
            return None
    
    def test_text_parsing(self, pdf_path: str, page_number: int = 0) -> Optional[RawText]:
        """
        Test text parsing in main thread only
        
        Args:
            pdf_path: Path to PDF file  
            page_number: Zero-based page number
            
        Returns:
            RawText object or None if failed
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Testing text parsing in main thread")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Page number: {page_number + 1}")
        
        start_time = time.time()
        
        try:
            # DIRECT CALL - no threading, no thread manager
            result = self._parse_text_direct(pdf_path, page_number)
            
            end_time = time.time()
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Text parsing completed in {end_time - start_time:.2f}s")
            
            if result:
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Results: {len(result.words)} words, {len(result.room_labels)} rooms, {len(result.dimensions)} dimensions")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Text parsing failed after {end_time - start_time:.2f}s")
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Error: {type(e).__name__}: {str(e)}")
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Full traceback:\\n{traceback.format_exc()}")
            return None
    
    def _parse_geometry_direct(self, pdf_path: str, page_number: int) -> RawGeometry:
        """
        Parse geometry directly using raw pdfplumber and PyMuPDF operations
        NO thread safety wrappers, NO retry logic, NO thread pools
        """
        import pdfplumber
        import fitz
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Starting direct geometry parsing")
        
        # Direct pdfplumber operation
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Opening PDF with pdfplumber: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] pdfplumber opened, pages: {len(pdf.pages)}")
            
            if page_number >= len(pdf.pages) or page_number < 0:
                raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(pdf.pages)} pages)")
            
            page = pdf.pages[page_number]
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Processing page {page_number + 1}")
            
            # Get page dimensions
            page_width = float(page.width)
            page_height = float(page.height)
            
            # Extract lines
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Extracting lines...")
            lines = self.geometry_parser._extract_lines(page)
            
            # Extract rectangles
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Extracting rectangles...")
            rectangles = self.geometry_parser._extract_rectangles(page)
            
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] pdfplumber extraction complete: {len(lines)} lines, {len(rectangles)} rectangles")
        
        # Direct PyMuPDF operation for polylines
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Opening PDF with PyMuPDF: {pdf_path}")
        
        polylines = []
        doc = fitz.open(pdf_path)
        try:
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PyMuPDF opened, pages: {len(doc)}")
            
            if page_number < len(doc):
                page = doc[page_number]
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Getting drawings from PyMuPDF page {page_number + 1}")
                
                drawings = page.get_drawings()
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Found {len(drawings)} drawings")
                
                for i, drawing in enumerate(drawings[:1000]):  # Limit for safety
                    if 'items' in drawing and len(drawing['items']) > 2:
                        points = []
                        for item in drawing['items']:
                            if len(item) >= 3:
                                try:
                                    x, y = item[1], item[2]
                                    if x is not None and y is not None:
                                        points.extend([float(x), float(y)])
                                except (TypeError, ValueError):
                                    continue
                        
                        if len(points) >= 6:
                            polylines.append({
                                'points': points,
                                'stroke_width': float(drawing.get('width', 1.0)),
                                'color': 0,
                                'closed': bool(drawing.get('closePath', False)),
                                'duct_probability': 0.5
                            })
                
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Processed {len(polylines)} polylines")
        finally:
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Closing PyMuPDF document")
            doc.close()
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PyMuPDF document closed")
        
        # Create result
        result = RawGeometry(
            page_width=page_width,
            page_height=page_height,
            scale_factor=None,
            lines=lines,
            rectangles=rectangles,
            polylines=polylines
        )
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Direct geometry parsing completed successfully")
        return result
    
    def _parse_text_direct(self, pdf_path: str, page_number: int) -> RawText:
        """
        Parse text directly using raw pdfplumber operations
        NO thread safety wrappers, NO retry logic, NO thread pools
        """
        import pdfplumber
        
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Starting direct text parsing")
        
        # Direct pdfplumber operation
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Opening PDF with pdfplumber: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] pdfplumber opened, pages: {len(pdf.pages)}")
            
            if page_number >= len(pdf.pages) or page_number < 0:
                raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(pdf.pages)} pages)")
            
            page = pdf.pages[page_number]
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Processing page {page_number + 1}")
            
            # Extract words directly
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Extracting words...")
            words = self.text_parser._extract_words_pdfplumber(page)
            
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] pdfplumber text extraction complete: {len(words)} words")
        
        # Identify text elements
        room_labels = self.text_parser._identify_room_labels(words)
        dimensions = self.text_parser._identify_dimensions(words)
        notes = self.text_parser._identify_notes(words)
        
        # Create result
        result = RawText(
            words=words,
            room_labels=room_labels,
            dimensions=dimensions,
            notes=notes
        )
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Direct text parsing completed successfully")
        return result
    
    def run_comprehensive_test(self, pdf_path: str, page_number: int = 0) -> Dict[str, Any]:
        """
        Run comprehensive single-threaded test of both geometry and text parsing
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number
            
        Returns:
            Dictionary with test results
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ===== STARTING COMPREHENSIVE SINGLE-THREADED TEST =====")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Page number: {page_number + 1}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Thread ID: {thread_id}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Thread name: {thread_name}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Process ID: {os.getpid()}")
        
        test_start = time.time()
        results = {
            'pdf_path': pdf_path,
            'page_number': page_number + 1,
            'thread_id': thread_id,
            'thread_name': thread_name,
            'process_id': os.getpid(),
            'test_start_time': test_start,
            'geometry_result': None,
            'text_result': None,
            'geometry_success': False,
            'text_success': False,
            'total_duration': 0.0,
            'errors': []
        }
        
        try:
            # Validate PDF file first
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            file_size = os.path.getsize(pdf_path)
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] PDF file size: {file_size} bytes")
            
            # Test geometry parsing
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ----- Testing Geometry Parsing -----")
            geometry_result = self.test_geometry_parsing(pdf_path, page_number)
            
            if geometry_result:
                results['geometry_result'] = {
                    'lines': len(geometry_result.lines),
                    'rectangles': len(geometry_result.rectangles),
                    'polylines': len(geometry_result.polylines),
                    'page_width': geometry_result.page_width,
                    'page_height': geometry_result.page_height
                }
                results['geometry_success'] = True
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ✅ Geometry parsing succeeded")
            else:
                results['errors'].append("Geometry parsing returned None")
                logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] ❌ Geometry parsing failed")
            
            # Test text parsing
            logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ----- Testing Text Parsing -----")
            text_result = self.test_text_parsing(pdf_path, page_number)
            
            if text_result:
                results['text_result'] = {
                    'words': len(text_result.words),
                    'room_labels': len(text_result.room_labels),
                    'dimensions': len(text_result.dimensions),
                    'notes': len(text_result.notes)
                }
                results['text_success'] = True
                logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ✅ Text parsing succeeded")
            else:
                results['errors'].append("Text parsing returned None")
                logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] ❌ Text parsing failed")
            
        except Exception as e:
            error_msg = f"Comprehensive test failed: {type(e).__name__}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] ❌ {error_msg}")
            logger.error(f"[MAIN-THREAD {thread_name}:{thread_id}] Full traceback:\\n{traceback.format_exc()}")
        
        # Final results
        test_end = time.time()
        results['total_duration'] = test_end - test_start
        
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] ===== COMPREHENSIVE TEST COMPLETED =====")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Total duration: {results['total_duration']:.2f}s")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Geometry success: {results['geometry_success']}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Text success: {results['text_success']}")
        logger.info(f"[MAIN-THREAD {thread_name}:{thread_id}] Errors: {len(results['errors'])}")
        
        return results


def main():
    """Main entry point for the test script"""
    if len(sys.argv) < 2:
        print("Usage: python test_single_threaded_parsing.py <pdf_path> [page_number]")
        print("Example: python test_single_threaded_parsing.py /tmp/test.pdf 0")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    page_number = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    
    print(f"🔍 Single-Threaded PDF Parser Test")
    print(f"📄 PDF: {pdf_path}")
    print(f"📖 Page: {page_number + 1}")
    print(f"🧵 Thread: {threading.current_thread().name}")
    print(f"🆔 Process: {os.getpid()}")
    print("=" * 60)
    
    tester = SingleThreadedPDFTester()
    results = tester.run_comprehensive_test(pdf_path, page_number)
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"⏱️  Duration: {results['total_duration']:.2f}s")
    print(f"📐 Geometry: {'✅ SUCCESS' if results['geometry_success'] else '❌ FAILED'}")
    print(f"📝 Text: {'✅ SUCCESS' if results['text_success'] else '❌ FAILED'}")
    
    if results['geometry_result']:
        gr = results['geometry_result']
        print(f"   📐 Lines: {gr['lines']}, Rectangles: {gr['rectangles']}, Polylines: {gr['polylines']}")
    
    if results['text_result']:
        tr = results['text_result']
        print(f"   📝 Words: {tr['words']}, Rooms: {tr['room_labels']}, Dimensions: {tr['dimensions']}")
    
    if results['errors']:
        print(f"❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"   • {error}")
    
    print("=" * 60)
    
    # Exit with error code if any parsing failed
    if not results['geometry_success'] or not results['text_success']:
        sys.exit(1)
    
    print("🎉 All tests passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()