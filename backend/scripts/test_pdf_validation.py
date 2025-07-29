#!/usr/bin/env python3
"""
Utility script to test PDF page-by-page validation outside the main pipeline

This script helps isolate whether PDF issues are due to file corruption 
or threading boundary problems by testing each page independently.

Usage:
    python test_pdf_validation.py <pdf_path>
    
Example:
    python test_pdf_validation.py /path/to/problematic_blueprint.pdf
"""

import sys
import os
import time
import logging
import traceback
from pathlib import Path

# Add the parent directory to Python path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

import pdfplumber
import fitz
from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_pdf_basic_access(pdf_path: str):
    """Test basic PDF access with both pdfplumber and PyMuPDF"""
    print(f"\n{'='*60}")
    print(f"BASIC PDF ACCESS TEST: {pdf_path}")
    print(f"{'='*60}")
    
    # Test file existence and size
    if not os.path.exists(pdf_path):
        print(f"❌ File does not exist: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    print(f"📁 File size: {file_size:.2f} MB")
    
    # Test pdfplumber access
    print(f"\n🔍 Testing pdfplumber access...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            print(f"✅ pdfplumber: Successfully opened PDF with {page_count} pages")
            
            if page_count > 0:
                page = pdf.pages[0]
                print(f"✅ pdfplumber: Can access first page ({page.width} x {page.height})")
            
    except Exception as e:
        print(f"❌ pdfplumber: Failed to open PDF: {type(e).__name__}: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False
    
    # Test PyMuPDF access
    print(f"\n🔍 Testing PyMuPDF access...")
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        print(f"✅ PyMuPDF: Successfully opened PDF with {page_count} pages")
        
        if page_count > 0:
            page = doc[0]
            rect = page.rect
            print(f"✅ PyMuPDF: Can access first page ({rect.width} x {rect.height})")
            
            # Test getting drawings
            drawings = page.get_drawings()
            print(f"✅ PyMuPDF: Found {len(drawings)} drawing elements on first page")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ PyMuPDF: Failed to open PDF: {type(e).__name__}: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False
    
    print(f"✅ Basic PDF access test PASSED")
    return True


def test_page_by_page_access(pdf_path: str, max_pages: int = 10):
    """Test accessing each page individually"""
    print(f"\n{'='*60}")
    print(f"PAGE-BY-PAGE ACCESS TEST: {pdf_path}")
    print(f"{'='*60}")
    
    # Get total page count
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
    except Exception as e:
        print(f"❌ Cannot determine page count: {e}")
        return False
    
    test_pages = min(total_pages, max_pages)
    print(f"📄 Testing first {test_pages} pages out of {total_pages} total")
    
    failed_pages = []
    
    for page_num in range(test_pages):
        page_display = page_num + 1
        print(f"\n🔍 Testing page {page_display}...")
        
        # Test pdfplumber page access
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num]
                words = page.extract_words()
                lines = page.lines
                rects = page.rects
                print(f"  ✅ pdfplumber page {page_display}: {len(words)} words, {len(lines)} lines, {len(rects)} rects")
                
        except Exception as e:
            print(f"  ❌ pdfplumber page {page_display}: {type(e).__name__}: {str(e)}")
            failed_pages.append((page_display, 'pdfplumber', str(e)))
        
        # Test PyMuPDF page access
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            drawings = page.get_drawings()
            text = page.get_text()
            print(f"  ✅ PyMuPDF page {page_display}: {len(drawings)} drawings, {len(text)} chars")
            doc.close()
            
        except Exception as e:
            print(f"  ❌ PyMuPDF page {page_display}: {type(e).__name__}: {str(e)}")
            failed_pages.append((page_display, 'PyMuPDF', str(e)))
    
    if failed_pages:
        print(f"\n❌ Failed pages:")
        for page_num, library, error in failed_pages:
            print(f"   Page {page_num} ({library}): {error}")
        return False
    else:
        print(f"\n✅ Page-by-page access test PASSED")
        return True


def test_parser_integration(pdf_path: str, test_pages: list = None):
    """Test our actual parser classes on specific pages"""
    print(f"\n{'='*60}")
    print(f"PARSER INTEGRATION TEST: {pdf_path}")
    print(f"{'='*60}")
    
    if test_pages is None:
        test_pages = [0]  # Test first page by default
    
    # Test GeometryParser
    print(f"\n🔍 Testing GeometryParser...")
    geometry_parser = GeometryParser()
    
    for page_num in test_pages:
        page_display = page_num + 1
        print(f"\n  Testing geometry parsing on page {page_display}...")
        
        try:
            start_time = time.time()
            
            # Create a single-page PDF for testing
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                print(f"    ⚠️  Page {page_display} does not exist (PDF has {len(doc)} pages)")
                doc.close()
                continue
                
            # Extract single page
            temp_doc = fitz.open()
            temp_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
            
            temp_doc.save(temp_path)
            temp_doc.close()
            doc.close()
            
            try:
                # Test geometry parsing
                geometry = geometry_parser.parse(temp_path)
                end_time = time.time()
                
                print(f"    ✅ Geometry parsing page {page_display}: {len(geometry.lines)} lines, "
                      f"{len(geometry.rectangles)} rects, {len(geometry.polylines)} polylines "
                      f"({end_time - start_time:.2f}s)")
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            print(f"    ❌ Geometry parsing page {page_display}: {type(e).__name__}: {str(e)}")
            if "document closed" in str(e).lower() or "seek of closed file" in str(e).lower():
                print(f"    🚨 DOCUMENT CLOSED ERROR detected!")
                print(f"    📍 This indicates a threading/file handle issue")
    
    # Test TextParser
    print(f"\n🔍 Testing TextParser...")
    text_parser = TextParser()
    
    for page_num in test_pages:
        page_display = page_num + 1
        print(f"\n  Testing text parsing on page {page_display}...")
        
        try:
            start_time = time.time()
            text_data = text_parser.parse(pdf_path, page_num)
            end_time = time.time()
            
            print(f"    ✅ Text parsing page {page_display}: {len(text_data.words)} words, "
                  f"{len(text_data.room_labels)} rooms, {len(text_data.dimensions)} dimensions "
                  f"({end_time - start_time:.2f}s)")
            
        except Exception as e:
            print(f"    ❌ Text parsing page {page_display}: {type(e).__name__}: {str(e)}")
            if "document closed" in str(e).lower() or "seek of closed file" in str(e).lower():
                print(f"    🚨 DOCUMENT CLOSED ERROR detected!")
                print(f"    📍 This indicates a threading/file handle issue")


def test_threading_stress(pdf_path: str, iterations: int = 3):
    """Test multiple sequential operations to stress test file handling"""
    print(f"\n{'='*60}")
    print(f"THREADING STRESS TEST: {pdf_path}")
    print(f"{'='*60}")
    
    print(f"🔄 Running {iterations} sequential parsing iterations...")
    
    geometry_parser = GeometryParser()
    text_parser = TextParser()
    
    for i in range(iterations):
        print(f"\n  Iteration {i + 1}/{iterations}...")
        
        try:
            # Geometry parsing
            geometry = geometry_parser.parse(pdf_path)
            print(f"    ✅ Geometry: {len(geometry.lines)} lines")
            
            # Text parsing
            text_data = text_parser.parse(pdf_path, 0)
            print(f"    ✅ Text: {len(text_data.words)} words")
            
            # Small delay between iterations
            time.sleep(0.1)
            
        except Exception as e:
            print(f"    ❌ Iteration {i + 1} failed: {type(e).__name__}: {str(e)}")
            if "document closed" in str(e).lower() or "seek of closed file" in str(e).lower():
                print(f"    🚨 DOCUMENT CLOSED ERROR on iteration {i + 1}!")
                return False
    
    print(f"\n✅ Threading stress test PASSED")
    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_pdf_validation.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"🧪 PDF VALIDATION TEST SUITE")
    print(f"📄 Testing: {pdf_path}")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    tests_passed = 0
    total_tests = 4
    
    if test_pdf_basic_access(pdf_path):
        tests_passed += 1
    
    if test_page_by_page_access(pdf_path, max_pages=5):
        tests_passed += 1
    
    test_parser_integration(pdf_path, test_pages=[0, 1, 2])  # Test first 3 pages
    tests_passed += 1  # This test is informational, always count as passed
    
    if test_threading_stress(pdf_path, iterations=3):
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Tests passed: {tests_passed}/{total_tests}")
    print(f"⏰ Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if tests_passed == total_tests:
        print(f"🎉 All tests PASSED - PDF appears to be valid and processable")
        sys.exit(0)
    else:
        print(f"⚠️  Some tests FAILED - PDF may have issues or corruption")
        sys.exit(1)


if __name__ == "__main__":
    main()