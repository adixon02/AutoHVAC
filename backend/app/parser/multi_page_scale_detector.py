"""
Multi-page scale detector for architectural blueprints
Analyzes all pages to find the most accurate scale
"""

import logging
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
from .scale_detector import ScaleDetector, ScaleResult

logger = logging.getLogger(__name__)


class MultiPageScaleDetector:
    """
    Detects scale across multiple PDF pages and selects the best one
    """
    
    def __init__(self):
        self.scale_detector = ScaleDetector()
    
    def detect_scale_from_all_pages(
        self,
        pdf_path: str,
        page_analyses: List[Dict[str, Any]] = None,
        max_pages: int = 10
    ) -> Tuple[ScaleResult, int]:
        """
        Detect scale from all viable pages and return the best result
        
        Args:
            pdf_path: Path to PDF file
            page_analyses: Optional list of page analysis results to prioritize certain pages
            max_pages: Maximum number of pages to analyze
            
        Returns:
            Tuple of (best_scale_result, page_number_with_best_scale)
        """
        logger.info(f"Starting multi-page scale detection for {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            num_pages = min(len(doc), max_pages)
            
            # Prioritize pages based on analysis if available
            pages_to_check = []
            if page_analyses:
                # Sort pages by score to check best candidates first
                sorted_analyses = sorted(page_analyses, key=lambda x: x.get('score', 0), reverse=True)
                for analysis in sorted_analyses[:5]:  # Check top 5 pages
                    page_num = analysis.get('page_number', 1) - 1  # Convert to 0-based
                    if 0 <= page_num < num_pages:
                        pages_to_check.append(page_num)
            
            # Add remaining pages
            for i in range(num_pages):
                if i not in pages_to_check:
                    pages_to_check.append(i)
            
            scale_results = []
            
            for page_num in pages_to_check[:max_pages]:
                try:
                    logger.info(f"Analyzing scale on page {page_num + 1}")
                    page = doc[page_num]
                    
                    # Extract text and geometry for scale detection
                    text_elements = self._extract_text_from_page(page)
                    drawings = page.get_drawings()
                    
                    # Simple geometry extraction for scale detection
                    lines = []
                    rectangles = []
                    
                    for drawing in drawings[:10000]:  # Limit for performance
                        if 'l' in drawing:  # Line
                            line = drawing['l']
                            lines.append({
                                'x0': line[0], 'y0': line[1],
                                'x1': line[2], 'y1': line[3],
                                'length': ((line[2]-line[0])**2 + (line[3]-line[1])**2)**0.5
                            })
                        elif 'r' in drawing:  # Rectangle
                            rect = drawing['r']
                            rectangles.append({
                                'x0': rect.x0, 'y0': rect.y0,
                                'x1': rect.x1, 'y1': rect.y1,
                                'width': rect.width,
                                'height': rect.height
                            })
                    
                    # Look for dimensions in text
                    dimensions = self._extract_dimensions_from_text(text_elements)
                    
                    # Detect scale for this page
                    scale_result = self.scale_detector.detect_scale(
                        text_elements=text_elements,
                        dimensions=dimensions,
                        rectangles=rectangles,
                        lines=lines,
                        page_width=page.rect.width,
                        page_height=page.rect.height
                    )
                    
                    scale_results.append((scale_result, page_num + 1))
                    
                    logger.info(f"Page {page_num + 1}: Scale {scale_result.scale_factor:.1f} px/ft, "
                              f"confidence {scale_result.confidence:.2f}, method: {scale_result.detection_method}")
                    
                    # If we find a high-confidence scale from text notation, use it
                    if scale_result.confidence > 0.85 and scale_result.detection_method == "text_notation":
                        logger.info(f"Found high-confidence scale notation on page {page_num + 1}")
                        doc.close()
                        return scale_result, page_num + 1
                    
                except Exception as e:
                    logger.warning(f"Failed to detect scale on page {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            # Select best scale result
            if scale_results:
                # Sort by confidence
                scale_results.sort(key=lambda x: x[0].confidence, reverse=True)
                best_result, best_page = scale_results[0]
                
                # Log all results for debugging
                logger.info("Scale detection results from all pages:")
                for result, page in scale_results[:5]:
                    logger.info(f"  Page {page}: {result.scale_factor:.1f} px/ft, "
                              f"confidence {result.confidence:.2f}, method: {result.detection_method}")
                
                logger.info(f"Selected scale from page {best_page}: {best_result.scale_factor:.1f} px/ft "
                          f"with confidence {best_result.confidence:.2f}")
                
                return best_result, best_page
            
            # Fallback if no scale detected
            logger.warning("No scale detected from any page, using default")
            return ScaleResult(
                scale_factor=48.0,  # Default 1/4"=1' scale
                confidence=0.3,
                detection_method="fallback_default",
                validation_results={},
                alternative_scales=[]
            ), 1
            
        except Exception as e:
            logger.error(f"Multi-page scale detection failed: {str(e)}")
            # Return default scale
            return ScaleResult(
                scale_factor=48.0,
                confidence=0.3,
                detection_method="fallback_error",
                validation_results={},
                alternative_scales=[]
            ), 1
    
    def _extract_text_from_page(self, page) -> List[Dict[str, Any]]:
        """Extract text elements from a page"""
        text_elements = []
        try:
            text = page.get_text("dict")
            for block in text.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text_content = span.get("text", "").strip()
                            if text_content:
                                text_elements.append({
                                    'text': text_content,
                                    'x0': span.get("bbox", [0])[0],
                                    'y0': span.get("bbox", [0, 0])[1],
                                    'size': span.get("size", 0),
                                    'flags': span.get("flags", 0)
                                })
        except Exception as e:
            logger.warning(f"Text extraction failed: {str(e)}")
        
        return text_elements
    
    def _extract_dimensions_from_text(self, text_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract dimension annotations from text"""
        dimensions = []
        dimension_pattern = r"(\d+)['\s]*-?\s*(\d+)?[\"\s]*"
        
        for element in text_elements:
            text = element.get('text', '')
            if re.search(dimension_pattern, text):
                dimensions.append({
                    'dimension_text': text,
                    'x0': element.get('x0', 0),
                    'y0': element.get('y0', 0)
                })
        
        return dimensions