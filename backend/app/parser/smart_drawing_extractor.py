"""
Smart drawing extraction with progressive degradation
Works in Celery daemon context - no multiprocessing
"""

import logging
import time
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
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
    Intelligent drawing extraction that works in Celery
    Uses threading (not multiprocessing) for timeouts
    """
    
    def __init__(self):
        self.full_timeout = 5.0  # seconds for full extraction
        self.max_full_elements = 5000  # Limit for full extraction
        self.max_sample_elements = 1000  # Limit for sampled extraction
        
    def extract_drawings(
        self,
        pdf_path: str,
        page_num: int
    ) -> ExtractionResult:
        """
        Extract drawings with progressive degradation
        Works in Celery daemon context
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            ExtractionResult with best possible extraction
        """
        start_time = time.time()
        
        # Check file exists
        if not os.path.exists(pdf_path):
            logger.warning(f"PDF file not found: {pdf_path}")
            return self._create_empty_result()
        
        # Try full extraction with threading (works in Celery)
        logger.info(f"Attempting drawing extraction for page {page_num + 1}")
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._extract_with_limits, pdf_path, page_num, self.max_full_elements)
                
                try:
                    drawings, polylines, method = future.result(timeout=self.full_timeout)
                    
                    if drawings or polylines:
                        quality = 1.0 if method == "full" else 0.7
                        return ExtractionResult(
                            drawings=drawings,
                            polylines=polylines,
                            quality_factor=quality,
                            extraction_method=method,
                            processing_time=time.time() - start_time,
                            element_count=len(drawings) + len(polylines)
                        )
                        
                except FutureTimeoutError:
                    logger.warning(f"Extraction timed out after {self.full_timeout}s, trying reduced extraction")
                    
        except Exception as e:
            logger.error(f"Threaded extraction failed: {e}")
        
        # Fallback: Direct extraction with strict limits
        logger.info("Using direct extraction with strict limits")
        try:
            drawings, polylines = self._extract_limited_direct(pdf_path, page_num, self.max_sample_elements)
            
            if drawings or polylines:
                return ExtractionResult(
                    drawings=drawings,
                    polylines=polylines,
                    quality_factor=0.5,
                    extraction_method="limited",
                    processing_time=time.time() - start_time,
                    element_count=len(drawings) + len(polylines)
                )
                
        except Exception as e:
            logger.error(f"Limited extraction failed: {e}")
        
        # Last resort: Bounding boxes only
        logger.warning("Using bounding box fallback")
        result = self._extract_bounding_boxes(pdf_path, page_num)
        result.processing_time = time.time() - start_time
        return result
    
    def _extract_with_limits(
        self,
        pdf_path: str,
        page_num: int,
        max_elements: int
    ) -> Tuple[List, List, str]:
        """
        Extract drawings with element count limits
        Runs in thread for timeout capability
        """
        drawings = []
        polylines = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                doc.close()
                return [], [], "error"
                
            page = doc[page_num]
            
            # Get drawings with iteration limit
            page_drawings = page.get_drawings()
            total_count = 0
            
            for i, drawing in enumerate(page_drawings):
                if i >= max_elements:
                    logger.info(f"Reached element limit {max_elements}")
                    doc.close()
                    return drawings, polylines, "limited"
                
                # Process drawing
                if 'items' in drawing:
                    for item in drawing['items'][:20]:  # Limit items per drawing
                        if item[0] == 'l':  # Line
                            polylines.append([item[1], item[2]])
                        elif item[0] == 'c':  # Curve
                            polylines.append([item[1], item[4]])
                        total_count += 1
                        
                        if total_count >= max_elements * 2:  # Polyline limit
                            break
                
                drawings.append({
                    'type': 'drawing',
                    'rect': drawing.get('rect'),
                    'fill': drawing.get('fill'),
                    'color': drawing.get('color')
                })
                
            doc.close()
            return drawings, polylines, "full"
            
        except Exception as e:
            logger.error(f"Drawing extraction error: {e}")
            return [], [], "error"
    
    def _extract_limited_direct(
        self,
        pdf_path: str,
        page_num: int,
        max_elements: int
    ) -> Tuple[List, List]:
        """
        Direct extraction with very strict limits
        No threading, minimal processing
        """
        drawings = []
        polylines = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                doc.close()
                return [], []
                
            page = doc[page_num]
            
            # Try to get just basic drawings
            try:
                # Use get_cdrawings if available (faster)
                if hasattr(page, 'get_cdrawings'):
                    page_drawings = page.get_cdrawings()
                else:
                    page_drawings = page.get_drawings()
                    
                for i, drawing in enumerate(page_drawings):
                    if i >= max_elements:
                        break
                        
                    drawings.append({
                        'type': 'drawing_limited',
                        'rect': drawing.get('rect', [0, 0, 0, 0])
                    })
                    
            except Exception as e:
                logger.warning(f"Could not get drawings: {e}")
            
            # At least get text blocks as rectangles
            if not drawings:
                text_blocks = page.get_text_blocks()
                for i, block in enumerate(text_blocks):
                    if i >= 100:
                        break
                    x0, y0, x1, y1 = block[:4]
                    drawings.append({
                        'type': 'text_block',
                        'rect': [x0, y0, x1, y1]
                    })
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Direct extraction error: {e}")
            
        return drawings, polylines
    
    def _extract_bounding_boxes(self, pdf_path: str, page_num: int) -> ExtractionResult:
        """
        Fast bounding box extraction as last resort
        """
        drawings = []
        polylines = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num < len(doc):
                page = doc[page_num]
                
                # Get page bounds
                rect = page.rect
                drawings.append({
                    'type': 'page_bounds',
                    'bbox': [rect.x0, rect.y0, rect.x1, rect.y1],
                    'width': rect.width,
                    'height': rect.height
                })
                
                # Get text bounding boxes
                try:
                    text_blocks = page.get_text_blocks()
                    for i, block in enumerate(text_blocks[:100]):
                        x0, y0, x1, y1 = block[:4]
                        drawings.append({
                            'type': 'text_bbox',
                            'bbox': [x0, y0, x1, y1],
                            'width': x1 - x0,
                            'height': y1 - y0
                        })
                except:
                    pass
                
            doc.close()
            
        except Exception as e:
            logger.error(f"Bbox extraction error: {e}")
            drawings = [{'type': 'error', 'message': str(e)}]
        
        return ExtractionResult(
            drawings=drawings,
            polylines=polylines,
            quality_factor=0.25,
            extraction_method="bbox_fallback",
            processing_time=0.0,
            element_count=len(drawings)
        )
    
    def _create_empty_result(self) -> ExtractionResult:
        """Create empty result when file not found"""
        return ExtractionResult(
            drawings=[],
            polylines=[],
            quality_factor=0.0,
            extraction_method="empty",
            processing_time=0.0,
            element_count=0
        )


# Global instance
smart_extractor = SmartDrawingExtractor()