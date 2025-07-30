#!/usr/bin/env python3
"""
Test script for multi-page PDF processing pipeline
Tests the complete flow: page analysis -> page selection -> geometry/text extraction -> AI processing
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_page_analyzer():
    """Test the PDF page analyzer with a sample PDF"""
    from services.pdf_page_analyzer import PDFPageAnalyzer
    
    logger.info("=== Testing PDF Page Analyzer ===")
    
    # Look for sample PDFs in the test directory
    sample_pdf_path = backend_dir / "tests" / "sample_blueprints" / "blueprint-example-99206.pdf"
    
    if not sample_pdf_path.exists():
        logger.warning(f"Sample PDF not found at {sample_pdf_path}")
        logger.info("Creating a minimal test PDF for testing...")
        
        # Create a simple test PDF with multiple pages
        import fitz
        doc = fitz.open()
        
        # Page 1 - Simple page with some text
        page1 = doc.new_page()
        page1.insert_text((50, 50), "This is page 1 - not a floor plan")
        
        # Page 2 - More complex page that looks like a floor plan
        page2 = doc.new_page()
        page2.insert_text((100, 100), "Living Room")
        page2.insert_text((200, 200), "12' x 15'")
        page2.insert_text((100, 300), "Kitchen")
        page2.insert_text((300, 100), "Bedroom")
        
        # Add some rectangles to simulate rooms
        rect1 = fitz.Rect(80, 80, 180, 180)
        page2.draw_rect(rect1)
        rect2 = fitz.Rect(180, 180, 280, 280)
        page2.draw_rect(rect2)
        
        # Page 3 - Another simple page
        page3 = doc.new_page()
        page3.insert_text((50, 50), "This is page 3 - also not a floor plan")
        
        # Save to temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='test_multipage_')
        os.close(temp_fd)
        doc.save(temp_path)
        doc.close()
        
        sample_pdf_path = temp_path
        logger.info(f"Created test PDF at: {sample_pdf_path}")
    
    try:
        # Test page analysis
        analyzer = PDFPageAnalyzer(timeout_per_page=10, max_pages=10)
        best_page, analyses = analyzer.analyze_pdf_pages(str(sample_pdf_path))
        
        logger.info(f"✅ PDF Analysis completed successfully")
        logger.info(f"Best page selected: {best_page}")
        logger.info(f"Total pages analyzed: {len(analyses)}")
        
        # Print analysis results
        for i, analysis in enumerate(analyses):
            logger.info(f"Page {analysis.page_number}: Score={analysis.score}, "
                       f"Rectangles={analysis.rectangle_count}, "
                       f"Room labels={analysis.room_label_count}, "
                       f"Dimensions={analysis.dimension_count}")
        
        # Generate summary
        summary = analyzer.get_analysis_summary(analyses)
        logger.info(f"Analysis summary: {summary}")
        
        return True, str(sample_pdf_path), best_page - 1  # Convert to 0-based
        
    except Exception as e:
        logger.error(f"❌ PDF Page Analysis failed: {str(e)}")
        return False, None, None
    
    finally:
        # Clean up temporary PDF if we created one
        if str(sample_pdf_path).startswith('/tmp/') or str(sample_pdf_path).startswith('/var/'):
            try:
                os.unlink(sample_pdf_path)
                logger.info("Cleaned up temporary test PDF")
            except Exception:
                pass

def test_geometry_parser_multipage(pdf_path: str, page_number: int):
    """Test the enhanced geometry parser with page selection"""
    from app.parser.geometry_parser_safe import create_safe_parser, GeometryParserTimeout, GeometryParserComplexity
    
    logger.info("=== Testing Multi-page Geometry Parser ===")
    
    try:
        # Test parsing specific page
        parser = create_safe_parser(timeout=30, enable_complexity_checks=True)
        raw_geometry = parser.parse(pdf_path, page_number=page_number)
        
        logger.info(f"✅ Geometry parsing completed successfully for page {page_number + 1}")
        logger.info(f"Lines extracted: {len(raw_geometry.lines)}")
        logger.info(f"Rectangles extracted: {len(raw_geometry.rectangles)}")
        logger.info(f"Page dimensions: {raw_geometry.page_width} x {raw_geometry.page_height}")
        
        return True, raw_geometry
        
    except GeometryParserTimeout as e:
        logger.error(f"❌ Geometry parsing timed out: {str(e)}")
        return False, None
    except GeometryParserComplexity as e:
        logger.error(f"❌ Page too complex: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"❌ Geometry parsing failed: {str(e)}")
        return False, None

def test_text_parser_multipage(pdf_path: str, page_number: int):
    """Test the enhanced text parser with page selection"""
    from app.parser.text_parser import TextParser
    
    logger.info("=== Testing Multi-page Text Parser ===")
    
    try:
        # Test parsing specific page
        parser = TextParser()
        raw_text = parser.parse(pdf_path, page_number=page_number)
        
        logger.info(f"✅ Text parsing completed successfully for page {page_number + 1}")
        logger.info(f"Words extracted: {len(raw_text.words)}")
        logger.info(f"Room labels found: {len(raw_text.room_labels)}")
        logger.info(f"Dimensions found: {len(raw_text.dimensions)}")
        
        # Test floor plan analysis
        analysis = parser.analyze_text_for_floor_plan(pdf_path, page_number)
        logger.info(f"Floor plan probability: {analysis['floor_plan_probability']}")
        
        return True, raw_text
        
    except Exception as e:
        logger.error(f"❌ Text parsing failed: {str(e)}")
        return False, None

def test_page_scoring(pdf_path: str, page_number: int):
    """Test the advanced page scoring algorithms"""
    from services.page_scoring import score_page_for_floor_plan
    
    logger.info("=== Testing Page Scoring Algorithms ===")
    
    try:
        # Test page scoring
        scoring = score_page_for_floor_plan(pdf_path, page_number)
        
        logger.info(f"✅ Page scoring completed successfully for page {page_number + 1}")
        logger.info(f"Total score: {scoring.total_score}")
        logger.info(f"Floor plan probability: {scoring.floor_plan_probability}")
        logger.info(f"Geometric score: {scoring.geometric_score}")
        logger.info(f"Text score: {scoring.text_score}")
        logger.info(f"Layout score: {scoring.layout_score}")
        logger.info(f"Confidence score: {scoring.confidence_score}")
        
        # Print reasoning
        logger.info("Scoring reasoning:")
        for reason in scoring.reasoning:
            logger.info(f"  - {reason}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Page scoring failed: {str(e)}")
        return False

def main():
    """Run all multi-page pipeline tests"""
    logger.info("🚀 Starting Multi-page PDF Processing Pipeline Tests")
    
    # Test 1: PDF Page Analysis
    success, pdf_path, best_page = test_pdf_page_analyzer()
    if not success:
        logger.error("❌ Pipeline test failed at page analysis stage")
        return False
    
    # Test 2: Enhanced Geometry Parser
    success, raw_geometry = test_geometry_parser_multipage(pdf_path, best_page)
    if not success:
        logger.error("❌ Pipeline test failed at geometry parsing stage")
        return False
    
    # Test 3: Enhanced Text Parser
    success, raw_text = test_text_parser_multipage(pdf_path, best_page)
    if not success:
        logger.error("❌ Pipeline test failed at text parsing stage")
        return False
    
    # Test 4: Page Scoring
    success = test_page_scoring(pdf_path, best_page)
    if not success:
        logger.error("❌ Pipeline test failed at page scoring stage")
        return False
    
    # Test 5: AI Cleanup (optional - requires OpenAI API key)
    if os.getenv("OPENAI_API_KEY"):
        logger.info("=== Testing AI Cleanup with Multi-page Data ===")
        try:
            from app.parser.ai_cleanup import cleanup
            import asyncio
            
            # Test AI cleanup
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                blueprint_schema = loop.run_until_complete(cleanup(raw_geometry, raw_text))
                logger.info(f"✅ AI cleanup completed successfully")
                logger.info(f"Rooms identified: {len(blueprint_schema.rooms)}")
                logger.info(f"Total area: {blueprint_schema.sqft_total} sqft")
            finally:
                loop.close()
                
        except Exception as e:
            logger.warning(f"⚠️ AI cleanup test failed (non-critical): {str(e)}")
    else:
        logger.info("ℹ️ Skipping AI cleanup test (no OPENAI_API_KEY)")
    
    logger.info("🎉 All multi-page pipeline tests completed successfully!")
    logger.info("✅ Multi-page PDF processing pipeline is working correctly")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)