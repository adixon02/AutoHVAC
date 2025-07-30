#!/usr/bin/env python3
"""
Standalone PDF validation test script
Tests the exact validation logic used in the upload route
"""

import sys
import os
import argparse
import hashlib
import traceback
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pdf_thread_manager import pdf_thread_manager

# Check AI-first configuration
AI_PARSING_ENABLED = os.getenv("AI_PARSING_ENABLED", "true").lower() != "false"
LEGACY_ELEMENT_LIMIT = int(os.getenv("LEGACY_ELEMENT_LIMIT", "20000"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_file_info(file_path: str) -> dict:
    """Get detailed file information"""
    info = {
        "path": file_path,
        "exists": os.path.exists(file_path)
    }
    
    if info["exists"]:
        try:
            info["size"] = os.path.getsize(file_path)
            with open(file_path, 'rb') as f:
                # First 16 bytes
                first_bytes = f.read(16)
                info["first_16_bytes"] = first_bytes.hex()
                info["pdf_header"] = first_bytes[:4] == b'%PDF'
                
                # SHA1 of first 64KB
                f.seek(0)
                chunk = f.read(65536)
                info["sha1_first_64k"] = hashlib.sha1(chunk).hexdigest()
                
                # Full file SHA1
                f.seek(0)
                sha1 = hashlib.sha1()
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    sha1.update(data)
                info["sha1_full"] = sha1.hexdigest()
                
        except Exception as e:
            info["read_error"] = f"{type(e).__name__}: {str(e)}"
    
    return info

def validate_pdf_from_disk(pdf_path: str, verbose: bool = False):
    """Validate PDF using the exact logic from blueprint.py"""
    import fitz
    
    print(f"\n{'='*60}")
    print(f"VALIDATING PDF: {pdf_path}")
    print(f"{'='*60}\n")
    
    # File info before validation
    file_info = get_file_info(pdf_path)
    print(f"File Info:")
    for key, value in file_info.items():
        print(f"  {key}: {value}")
    print()
    
    if not file_info["exists"]:
        return False, "File does not exist", 0
    
    if not file_info.get("pdf_header"):
        return False, "File does not have PDF header (%PDF)", 0
    
    error_msg = None
    page_count = 0
    
    try:
        print("Opening PDF with PyMuPDF (fitz)...")
        doc = fitz.open(pdf_path)
        
        try:
            print(f"PDF opened successfully")
            print(f"  Pages: {len(doc)}")
            print(f"  Encrypted: {doc.is_encrypted}")
            print(f"  Metadata: {doc.metadata}")
            
            if doc.is_encrypted:
                error_msg = "PDF is password protected. Please upload an unprotected version."
                return False, error_msg, 0
            
            page_count = len(doc)
            if page_count == 0:
                error_msg = "PDF contains no pages"
                return False, error_msg, 0
            
            if page_count > 100:
                error_msg = f"PDF has {page_count} pages. Please limit to 100 pages or fewer for processing."
                return False, error_msg, page_count
            
            # Quick complexity check on first few pages
            print("\nChecking page complexity...")
            total_elements = 0
            for page_num in range(min(3, page_count)):
                try:
                    print(f"\n  Page {page_num + 1}:")
                    page = doc[page_num]
                    
                    # Get page dimensions
                    rect = page.rect
                    print(f"    Dimensions: {rect.width} x {rect.height}")
                    
                    # Get drawings
                    drawings = page.get_drawings()
                    print(f"    Drawing elements: {len(drawings)}")
                    
                    if verbose and len(drawings) > 0:
                        print(f"    First 5 drawing elements:")
                        for i, drawing in enumerate(drawings[:5]):
                            print(f"      {i+1}: {drawing}")
                    
                    # Get text
                    text = page.get_text()
                    print(f"    Text length: {len(text)} chars")
                    if verbose and text:
                        print(f"    First 200 chars: {text[:200]}...")
                    
                    total_elements += len(drawings)
                    
                    if not AI_PARSING_ENABLED and len(drawings) > LEGACY_ELEMENT_LIMIT:
                        error_msg = f"Blueprint is too complex for traditional parsing (page {page_num + 1} has {len(drawings)} elements). AI parsing is recommended for complex blueprints."
                        return False, error_msg, page_count
                    elif AI_PARSING_ENABLED and len(drawings) > LEGACY_ELEMENT_LIMIT:
                        print(f"    Note: Page has {len(drawings)} elements (exceeds legacy limit of {LEGACY_ELEMENT_LIMIT})")
                        print(f"    AI parsing enabled - complexity check skipped")
                        
                except Exception as page_error:
                    print(f"    ERROR processing page: {type(page_error).__name__}: {str(page_error)}")
                    if verbose:
                        traceback.print_exc()
                    # Continue with other pages
            
            print(f"\nTotal elements in first {min(3, page_count)} pages: {total_elements}")
            
            if AI_PARSING_ENABLED:
                print(f"\nAI-first mode: ENABLED")
                print("PDF validation PASSED ✅ (no complexity limits for AI parsing)")
            else:
                print(f"\nAI-first mode: DISABLED")
                print(f"Legacy parser limit: {LEGACY_ELEMENT_LIMIT} elements per page")
                print("PDF validation PASSED ✅")
            
            return True, None, page_count
            
        finally:
            # ALWAYS close the document
            print("\nClosing PDF document...")
            doc.close()
            print("PDF document closed")
            
    except Exception as e:
        # Store error as string BEFORE any cleanup
        error_msg = f"Cannot process this PDF file. It may be corrupted or in an unsupported format: {str(e)[:100]}"
        print(f"\nERROR: {type(e).__name__}: {str(e)}")
        if verbose:
            print("\nFull traceback:")
            traceback.print_exc()
        return False, error_msg, 0

def test_with_thread_manager(pdf_path: str, verbose: bool = False):
    """Test PDF validation using the thread manager"""
    print(f"\n{'='*60}")
    print("TESTING WITH PDF THREAD MANAGER")
    print(f"{'='*60}\n")
    
    try:
        # Validate using thread-safe operation
        is_valid, error_message, pages = pdf_thread_manager.process_pdf_with_retry(
            pdf_path=pdf_path,
            processor_func=lambda path: validate_pdf_from_disk(path, verbose),
            operation_name="pdf_validation",
            max_retries=2
        )
        
        print(f"\nThread Manager Result:")
        print(f"  Valid: {is_valid}")
        print(f"  Error: {error_message}")
        print(f"  Pages: {pages}")
        
        return is_valid, error_message, pages
        
    except Exception as e:
        print(f"\nThread Manager Error: {type(e).__name__}: {str(e)}")
        if verbose:
            traceback.print_exc()
        return False, str(e), 0

def create_dummy_pdf(output_path: str):
    """Create a simple dummy PDF for testing"""
    try:
        import fitz
        
        print(f"\nCreating dummy PDF at: {output_path}")
        
        # Create new PDF
        doc = fitz.new()
        
        # Add a page with some text
        page = doc.new_page()
        text = "This is a test PDF document.\nIt has some text on it.\nPage 1 of 1."
        text_point = fitz.Point(50, 50)
        page.insert_text(text_point, text, fontsize=12)
        
        # Add a simple rectangle
        rect = fitz.Rect(100, 100, 200, 200)
        page.draw_rect(rect, color=(0, 0, 1), width=2)
        
        # Save
        doc.save(output_path)
        doc.close()
        
        file_info = get_file_info(output_path)
        print(f"Dummy PDF created:")
        for key, value in file_info.items():
            print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"Failed to create dummy PDF: {type(e).__name__}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test PDF validation')
    parser.add_argument('pdf_path', help='Path to PDF file to validate')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--create-dummy', action='store_true', help='Create a dummy PDF for testing')
    parser.add_argument('--skip-thread-manager', action='store_true', help='Skip thread manager test')
    
    args = parser.parse_args()
    
    if args.create_dummy:
        dummy_path = "test_dummy.pdf"
        if create_dummy_pdf(dummy_path):
            print(f"\nNow testing with dummy PDF...")
            args.pdf_path = dummy_path
        else:
            sys.exit(1)
    
    # Direct validation
    print("\n" + "="*60)
    print("DIRECT VALIDATION TEST")
    print("="*60)
    
    is_valid, error_message, pages = validate_pdf_from_disk(args.pdf_path, args.verbose)
    
    print(f"\nDirect Validation Result:")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error_message}")
    print(f"  Pages: {pages}")
    
    # Thread manager validation
    if not args.skip_thread_manager:
        is_valid_tm, error_message_tm, pages_tm = test_with_thread_manager(args.pdf_path, args.verbose)
        
        # Compare results
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}\n")
        
        print(f"Direct vs Thread Manager:")
        print(f"  Valid: {is_valid} vs {is_valid_tm} {'✅' if is_valid == is_valid_tm else '❌'}")
        print(f"  Error: {error_message} vs {error_message_tm} {'✅' if error_message == error_message_tm else '❌'}")
        print(f"  Pages: {pages} vs {pages_tm} {'✅' if pages == pages_tm else '❌'}")
    
    # Exit code
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()