"""
Smart drawing extraction with progressive degradation
Never blocks - always returns the best possible extraction
"""

import logging
import time
import os
import multiprocessing
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of drawing extraction with quality metrics"""
    drawings: List[Dict[str, Any]]
    polylines: List[List[Tuple[float, float]]]
    quality_factor: float  # 1.0 = full, 0.5 = sampled, 0.25 = bbox only
    extraction_method: str
    processing_time: float
    element_count: int


class SmartDrawingExtractor:
    """
    Intelligent drawing extraction that never fails
    Uses progressive degradation to always return results
    """
    
    def __init__(self):
        self.full_timeout = 5.0  # seconds for full extraction
        self.sample_timeout = 3.0  # seconds for sampling
        self.bbox_timeout = 1.0  # seconds for bbox fallback
        
    def extract_drawings(
        self,
        pdf_path: str,
        page_num: int
    ) -> ExtractionResult:
        """
        Extract drawings with progressive degradation
        Never blocks or fails - always returns something
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            ExtractionResult with best possible extraction
        """
        start_time = time.time()
        
        # Try full extraction first
        logger.info(f"Attempting full drawing extraction for page {page_num + 1}")
        result = self._try_full_extraction(pdf_path, page_num)
        if result:
            result.processing_time = time.time() - start_time
            logger.info(f"Full extraction successful: {result.element_count} elements in {result.processing_time:.2f}s")
            return result
            
        # Fall back to sampling
        logger.warning("Full extraction timed out, trying sampling approach")
        result = self._try_sampled_extraction(pdf_path, page_num)
        if result:
            result.processing_time = time.time() - start_time
            logger.info(f"Sampled extraction successful: {result.element_count} elements in {result.processing_time:.2f}s")
            return result
            
        # Last resort - bounding boxes only
        logger.warning("Sampling timed out, using bounding box fallback")
        result = self._extract_bounding_boxes(pdf_path, page_num)
        result.processing_time = time.time() - start_time
        logger.info(f"Bbox extraction completed: {result.element_count} elements in {result.processing_time:.2f}s")
        return result
    
    def _try_full_extraction(self, pdf_path: str, page_num: int) -> Optional[ExtractionResult]:
        """
        Try full drawing extraction with timeout
        """
        try:
            # Check if file exists first
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found: {pdf_path}")
                return None
                
            # Use multiprocessing for true timeout capability
            with multiprocessing.Pool(1) as pool:
                async_result = pool.apply_async(
                    _extract_drawings_worker,
                    (pdf_path, page_num, "full")
                )
                
                try:
                    drawings, polylines = async_result.get(timeout=self.full_timeout)
                    
                    return ExtractionResult(
                        drawings=drawings,
                        polylines=polylines,
                        quality_factor=1.0,
                        extraction_method="full",
                        processing_time=0.0,  # Will be set by caller
                        element_count=len(drawings) + len(polylines)
                    )
                except multiprocessing.TimeoutError:
                    logger.warning(f"Full extraction timed out after {self.full_timeout}s")
                    pool.terminate()
                    return None
                    
        except Exception as e:
            logger.error(f"Full extraction failed: {e}")
            return None
    
    def _try_sampled_extraction(self, pdf_path: str, page_num: int) -> Optional[ExtractionResult]:
        """
        Try sampled extraction (every Nth element) with timeout
        """
        try:
            with multiprocessing.Pool(1) as pool:
                async_result = pool.apply_async(
                    _extract_drawings_worker,
                    (pdf_path, page_num, "sampled")
                )
                
                try:
                    drawings, polylines = async_result.get(timeout=self.sample_timeout)
                    
                    return ExtractionResult(
                        drawings=drawings,
                        polylines=polylines,
                        quality_factor=0.5,
                        extraction_method="sampled",
                        processing_time=0.0,
                        element_count=len(drawings) + len(polylines)
                    )
                except multiprocessing.TimeoutError:
                    logger.warning(f"Sampled extraction timed out after {self.sample_timeout}s")
                    pool.terminate()
                    return None
                    
        except Exception as e:
            logger.error(f"Sampled extraction failed: {e}")
            return None
    
    def _extract_bounding_boxes(self, pdf_path: str, page_num: int) -> ExtractionResult:
        """
        Fast bounding box extraction as last resort
        This should never fail
        """
        drawings = []
        polylines = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num < len(doc):
                page = doc[page_num]
                
                # Just get page dimensions and basic rectangles
                rect = page.rect
                
                # Create a simple bounding box representation
                drawings.append({
                    'type': 'page_bounds',
                    'bbox': [rect.x0, rect.y0, rect.x1, rect.y1],
                    'width': rect.width,
                    'height': rect.height
                })
                
                # Try to at least get text bounding boxes for room detection
                text_blocks = page.get_text_blocks()
                for block in text_blocks[:100]:  # Limit to first 100
                    x0, y0, x1, y1 = block[:4]
                    drawings.append({
                        'type': 'text_bbox',
                        'bbox': [x0, y0, x1, y1],
                        'width': x1 - x0,
                        'height': y1 - y0
                    })
                
            doc.close()
            
        except Exception as e:
            logger.error(f"Even bbox extraction had issues: {e}")
            # Return minimal data
            drawings = [{'type': 'error', 'message': str(e)}]
        
        return ExtractionResult(
            drawings=drawings,
            polylines=polylines,
            quality_factor=0.25,
            extraction_method="bbox_fallback",
            processing_time=0.0,
            element_count=len(drawings)
        )


def _extract_drawings_worker(pdf_path: str, page_num: int, mode: str) -> Tuple[List, List]:
    """
    Worker function for multiprocessing
    Runs in separate process for true timeout capability
    """
    drawings = []
    polylines = []
    
    try:
        doc = fitz.open(pdf_path)
        if page_num < len(doc):
            page = doc[page_num]
            
            if mode == "full":
                # Full extraction
                page_drawings = page.get_drawings()
                
                for drawing in page_drawings:
                    # Process all drawings
                    if 'items' in drawing:
                        for item in drawing['items']:
                            if item[0] == 'l':  # Line
                                polylines.append([item[1], item[2]])
                            elif item[0] == 'c':  # Curve
                                # Approximate curve with line segments
                                polylines.append([item[1], item[4]])
                    
                    drawings.append({
                        'type': 'drawing',
                        'rect': drawing.get('rect'),
                        'fill': drawing.get('fill'),
                        'color': drawing.get('color'),
                        'width': drawing.get('width', 1)
                    })
                    
            elif mode == "sampled":
                # Sampled extraction - every 2nd element
                page_drawings = page.get_drawings()
                
                for i, drawing in enumerate(page_drawings):
                    if i % 2 == 0:  # Sample every other element
                        if 'items' in drawing:
                            for item in drawing['items'][:10]:  # Limit items per drawing
                                if item[0] == 'l':
                                    polylines.append([item[1], item[2]])
                        
                        drawings.append({
                            'type': 'drawing_sampled',
                            'rect': drawing.get('rect')
                        })
                        
                    if len(drawings) > 1000:  # Cap at 1000 for sampled mode
                        break
        
        doc.close()
        
    except Exception as e:
        logger.error(f"Worker extraction failed: {e}")
    
    return drawings, polylines


# Global instance
smart_extractor = SmartDrawingExtractor()