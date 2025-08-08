"""
Progressive extraction orchestrator for blueprint PDFs
Coordinates page classification, scale extraction, and geometry processing
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import fitz  # PyMuPDF

# Import our new components
from .scale_extractor import scale_extractor, ScaleResult
from .page_classifier import page_classifier, PageType

# Import existing components
try:
    from services.ocr_extractor import OCRExtractor
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPlan:
    """Plan for extracting data from PDF"""
    primary_page: int
    scale: ScaleResult
    extraction_mode: str  # "full", "sampled", "minimal"
    confidence: float
    secondary_pages: List[int]


class ProgressiveExtractor:
    """
    Orchestrates intelligent PDF extraction with progressive strategies
    Goal: Extract the right data from the right page with minimal processing
    """
    
    def __init__(self):
        self.ocr_extractor = OCRExtractor() if OCR_AVAILABLE else None
        self.max_ocr_time = 3.0  # Max seconds for OCR per page
        self.max_geometry_time = 5.0  # Max seconds for geometry extraction
    
    def extract_blueprint_data(
        self,
        pdf_path: str,
        quick_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point for progressive blueprint extraction
        
        Args:
            pdf_path: Path to PDF file
            quick_mode: If True, use fastest extraction methods
            
        Returns:
            Dictionary with extracted data and metadata
        """
        start_time = time.time()
        
        # Step 1: Quick page classification
        logger.info("Step 1: Classifying pages...")
        classifications = page_classifier.classify_pages(pdf_path, quick_mode=True)
        
        if not classifications:
            logger.error("Failed to classify pages")
            return self._create_error_result("Page classification failed")
        
        # Step 2: Find best floor plan page
        floor_plan_pages = page_classifier.get_pages_by_type(
            classifications, 
            PageType.FLOOR_PLAN,
            min_confidence=0.4
        )
        
        if not floor_plan_pages:
            logger.warning("No floor plan pages found, using first page")
            primary_page = 0
        else:
            primary_page = floor_plan_pages[0]
            logger.info(f"Step 2: Selected page {primary_page + 1} as primary floor plan")
        
        # Step 3: Targeted scale extraction
        logger.info("Step 3: Extracting scale from primary page...")
        scale = self._extract_scale_smart(pdf_path, primary_page, classifications)
        
        # Step 4: Create extraction plan based on confidence
        plan = self._create_extraction_plan(
            primary_page,
            scale,
            classifications,
            quick_mode
        )
        
        logger.info(f"Step 4: Extraction plan - Mode: {plan.extraction_mode}, "
                   f"Scale: {scale.pixels_per_foot:.1f} px/ft, "
                   f"Confidence: {plan.confidence:.2f}")
        
        # Step 5: Execute extraction plan
        result = self._execute_extraction_plan(pdf_path, plan)
        
        # Add metadata
        result['metadata'] = {
            'processing_time': time.time() - start_time,
            'primary_page': plan.primary_page + 1,  # 1-indexed for display
            'scale': {
                'value': scale.pixels_per_foot,
                'notation': scale.scale_notation,
                'confidence': scale.confidence,
                'source': scale.source
            },
            'extraction_mode': plan.extraction_mode,
            'overall_confidence': plan.confidence
        }
        
        logger.info(f"Extraction completed in {result['metadata']['processing_time']:.1f}s")
        
        return result
    
    def _extract_scale_smart(
        self,
        pdf_path: str,
        primary_page: int,
        classifications: List
    ) -> ScaleResult:
        """
        Smart scale extraction using OCR on the right page
        
        Args:
            pdf_path: Path to PDF
            primary_page: Primary floor plan page number
            classifications: Page classifications
            
        Returns:
            ScaleResult with detected scale
        """
        # If OCR not available, return default
        if not self.ocr_extractor:
            logger.warning("OCR not available, using default scale")
            return ScaleResult(
                pixels_per_foot=48.0,
                scale_notation="1/4\"=1'",
                confidence=0.3,
                source="default",
                page_num=primary_page
            )
        
        try:
            # Extract OCR text from primary page
            doc = fitz.open(pdf_path)
            page = doc[primary_page]
            
            # Quick OCR for scale detection
            ocr_text = ""
            if self.ocr_extractor:
                # Focus on regions where scale is typically found
                page_rect = page.rect
                
                # Title block area (bottom right)
                title_rect = fitz.Rect(
                    page_rect.width * 0.6,  # Right 40%
                    page_rect.height * 0.7,  # Bottom 30%
                    page_rect.width,
                    page_rect.height
                )
                
                # Extract text from specific region
                ocr_text = self._ocr_region(page, title_rect)
                
                # If no scale found, try full page
                if "SCALE" not in ocr_text.upper():
                    ocr_text = page.get_text()
            
            doc.close()
            
            # Extract scale using our new scale extractor
            scale = scale_extractor.extract_scale(ocr_text, primary_page)
            
            # Boost confidence if from floor plan page
            if classifications[primary_page].page_type == PageType.FLOOR_PLAN:
                scale.confidence = min(0.95, scale.confidence * 1.2)
            
            return scale
            
        except Exception as e:
            logger.error(f"Scale extraction failed: {e}")
            return ScaleResult(
                pixels_per_foot=48.0,
                scale_notation="1/4\"=1'",
                confidence=0.3,
                source="default",
                page_num=primary_page
            )
    
    def _ocr_region(self, page: fitz.Page, rect: fitz.Rect) -> str:
        """
        OCR a specific region of a page
        
        Args:
            page: PyMuPDF page object
            rect: Rectangle to OCR
            
        Returns:
            OCR text from region
        """
        try:
            # Get pixmap of region
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat, clip=rect)
            
            # Convert to image for OCR
            img_data = pix.tobytes("png")
            
            # Use OCR extractor if available
            if self.ocr_extractor and hasattr(self.ocr_extractor, 'extract_from_bytes'):
                text = self.ocr_extractor.extract_from_bytes(img_data)
            else:
                # Fallback to PyMuPDF text extraction
                text = page.get_textbox(rect)
            
            return text or ""
            
        except Exception as e:
            logger.debug(f"OCR region failed: {e}")
            return ""
    
    def _create_extraction_plan(
        self,
        primary_page: int,
        scale: ScaleResult,
        classifications: List,
        quick_mode: bool
    ) -> ExtractionPlan:
        """
        Create extraction plan based on confidence levels
        
        Args:
            primary_page: Primary page to extract
            scale: Detected scale
            classifications: Page classifications
            quick_mode: Whether to use quick extraction
            
        Returns:
            ExtractionPlan with strategy
        """
        # Calculate overall confidence
        page_confidence = classifications[primary_page].confidence if primary_page < len(classifications) else 0.5
        overall_confidence = (scale.confidence + page_confidence) / 2
        
        # Determine extraction mode based on confidence
        if overall_confidence > 0.7 and not quick_mode:
            extraction_mode = "full"
        elif overall_confidence > 0.5 or quick_mode:
            extraction_mode = "sampled"
        else:
            extraction_mode = "minimal"
        
        # Find secondary pages if needed
        secondary_pages = []
        if extraction_mode == "minimal":
            # Try to find additional floor plan pages
            for c in classifications:
                if (c.page_type == PageType.FLOOR_PLAN and 
                    c.page_num != primary_page and 
                    c.confidence > 0.3):
                    secondary_pages.append(c.page_num)
                    if len(secondary_pages) >= 2:
                        break
        
        return ExtractionPlan(
            primary_page=primary_page,
            scale=scale,
            extraction_mode=extraction_mode,
            confidence=overall_confidence,
            secondary_pages=secondary_pages
        )
    
    def _execute_extraction_plan(
        self,
        pdf_path: str,
        plan: ExtractionPlan
    ) -> Dict[str, Any]:
        """
        Execute the extraction plan
        
        Args:
            pdf_path: Path to PDF
            plan: Extraction plan
            
        Returns:
            Extracted data dictionary
        """
        result = {
            'rooms': [],
            'geometry': {},
            'text': {},
            'success': False
        }
        
        try:
            # Import geometry extractor dynamically
            from app.parser.smart_drawing_extractor import smart_extractor
            
            # Extract based on mode
            if plan.extraction_mode == "full":
                # Full extraction with high detail
                extraction = smart_extractor.extract_drawings(
                    pdf_path,
                    plan.primary_page
                )
                
                result['geometry'] = {
                    'drawings': extraction.drawings,
                    'polylines': extraction.polylines,
                    'quality': extraction.quality_factor,
                    'scale': plan.scale.pixels_per_foot
                }
                
            elif plan.extraction_mode == "sampled":
                # Sampled extraction for efficiency
                extraction = smart_extractor.extract_drawings(
                    pdf_path,
                    plan.primary_page
                )
                
                result['geometry'] = {
                    'drawings': extraction.drawings[:1000],  # Limit drawings
                    'polylines': extraction.polylines[:500],  # Limit lines
                    'quality': extraction.quality_factor * 0.7,
                    'scale': plan.scale.pixels_per_foot
                }
                
            else:  # minimal
                # Minimal extraction - just basics
                doc = fitz.open(pdf_path)
                page = doc[plan.primary_page]
                
                result['geometry'] = {
                    'page_bounds': [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1],
                    'scale': plan.scale.pixels_per_foot,
                    'quality': 0.3
                }
                
                doc.close()
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Extraction execution failed: {e}")
            result['error'] = str(e)
        
        return result
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result dictionary"""
        return {
            'success': False,
            'error': error_msg,
            'rooms': [],
            'geometry': {},
            'text': {},
            'metadata': {
                'processing_time': 0.0,
                'error': error_msg
            }
        }


# Global instance
progressive_extractor = ProgressiveExtractor()