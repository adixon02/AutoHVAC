"""
PDF Page Analyzer Service
Handles multi-page PDF analysis, floor plan scoring, and best page selection
"""

import fitz  # PyMuPDF
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

# Maximum elements per page before rejecting as too complex
MAX_ELEMENTS_PER_PAGE = 100000  # Increased to handle complex floor plans

# Room type keywords for scoring
ROOM_KEYWORDS = [
    'bedroom', 'living', 'kitchen', 'bathroom', 'dining', 'office',
    'family', 'master', 'guest', 'utility', 'laundry', 'closet',
    'hall', 'foyer', 'pantry', 'garage', 'basement', 'attic',
    'den', 'study', 'library', 'sunroom', 'porch', 'deck', 'room',
    'br', 'ba', 'kit', 'lr', 'dr', 'mb'  # Common abbreviations
]

# Page type indicators
FLOOR_PLAN_INDICATORS = [
    'floor plan', 'floorplan', 'floor-plan', 'layout', 'main level',
    'first floor', 'second floor', 'upper level', 'lower level',
    'basement plan', 'ground floor', 'third floor', 'loft plan',
    'attic plan', 'mezzanine', 'penthouse'
]

SPECIFICATION_INDICATORS = [
    'specification', 'specifications', 'spec', 'specs', 'notes',
    'general notes', 'construction notes', 'details', 'legend',
    'schedule', 'electrical notes', 'mechanical notes', 'structural notes',
    'building code', 'requirements', 'standards', 'procedures',
    'installation', 'warranty', 'material list', 'equipment list'
]

ELEVATION_INDICATORS = [
    'elevation', 'front elevation', 'rear elevation', 'side elevation',
    'north elevation', 'south elevation', 'east elevation', 'west elevation',
    'section', 'cross section', 'detail', 'perspective', 'front view',
    'side view', 'rear view', 'street view', 'exterior view', 'facade',
    'building elevation', 'house elevation', 'exterior elevation'
]

# Additional elevation rejection patterns
ELEVATION_REJECTION_PATTERNS = [
    'roof pitch', 'roof slope', 'grade line', 'finish floor',
    'top of plate', 'ridge', 'eave', 'gutter', 'downspout',
    'siding', 'brick veneer', 'stone veneer', 'stucco',
    'shingle', 'fascia', 'soffit', 'window head', 'window sill',
    'foundation wall', 'footing', 'grade', 'finish grade'
]

# Dimension patterns for scoring
DIMENSION_PATTERNS = [
    r"(\d+)'\s*-?\s*(\d+)\"?",           # 12'-6"
    r"(\d+)'\s*(\d+)\"",                 # 12'6"
    r"(\d+)'",                           # 12'
    r"(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)", # 12.5 x 15.0
    r"(\d+)\s*[xX]\s*(\d+)",            # 12 x 15
]


@dataclass
class PageAnalysis:
    """Analysis results for a single PDF page"""
    page_number: int
    score: float
    rectangle_count: int
    room_label_count: int
    dimension_count: int
    text_element_count: int
    geometric_complexity: int
    processing_time: float
    selected: bool = False
    too_complex: bool = False
    error: Optional[str] = None
    page_type: str = "unknown"  # floor_plan, specification, elevation, unknown
    floor_number: Optional[int] = None  # Detected floor number (1, 2, etc.)
    floor_name: Optional[str] = None  # Floor name ("Main Floor", "Upper Level", etc.)


class PDFPageAnalyzer:
    """
    Analyzes multi-page PDFs to identify the best floor plan page
    """
    
    def __init__(self, timeout_per_page: int = 30, max_pages: int = 100):
        self.timeout_per_page = timeout_per_page
        self.max_pages = max_pages
    
    def analyze_pdf_pages(self, pdf_path: str, return_multiple: bool = False, 
                          min_score_threshold: float = 100.0) -> Tuple[int, List[PageAnalysis]]:
        """
        Analyze all pages in PDF and select the best floor plan page(s)
        
        Args:
            pdf_path: Path to PDF file
            return_multiple: If True, marks multiple high-scoring pages as selected
            min_score_threshold: Minimum score to consider a page as floor plan
            
        Returns:
            Tuple of (best_page_number, list_of_page_analyses)
            Note: If return_multiple=True, multiple pages may be marked as selected
            
        Raises:
            ValueError: If no suitable pages found or PDF invalid
            TimeoutError: If processing exceeds total time limit
        """
        start_time = time.time()
        logger.info(f"Starting multi-page PDF analysis: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Cannot open PDF file: {str(e)}")
        
        try:
            page_count = len(doc)
            logger.info(f"PDF has {page_count} pages")
            
            if page_count == 0:
                raise ValueError("PDF contains no pages")
            
            if page_count > self.max_pages:
                logger.warning(f"PDF has {page_count} pages, limiting analysis to first {self.max_pages}")
                page_count = self.max_pages
            
            analyses = []
            
            # Analyze each page
            for page_num in range(page_count):
                try:
                    page_start = time.time()
                    logger.info(f"Analyzing page {page_num + 1}/{page_count}")
                    
                    analysis = self._analyze_single_page(doc, page_num)
                    analysis.processing_time = time.time() - page_start
                    
                    analyses.append(analysis)
                    # Try to detect floor number
                    analysis.floor_number, analysis.floor_name = self._detect_floor_info(doc[page_num])
                    
                    logger.info(f"Page {page_num + 1} - Type: {analysis.page_type}, Score: {analysis.score:.1f} "
                              f"(rectangles: {analysis.rectangle_count}, "
                              f"room_labels: {analysis.room_label_count}, "
                              f"dimensions: {analysis.dimension_count}, "
                              f"floor: {analysis.floor_name or 'unknown'})")
                    
                except Exception as e:
                    logger.error(f"Error analyzing page {page_num + 1}: {str(e)}")
                    analyses.append(PageAnalysis(
                        page_number=page_num + 1,
                        score=0.0,
                        rectangle_count=0,
                        room_label_count=0,
                        dimension_count=0,
                        text_element_count=0,
                        geometric_complexity=0,
                        processing_time=time.time() - page_start,
                        error=str(e)
                    ))
            
            # Select best page(s)
            if return_multiple:
                best_page_num = self._select_multiple_pages(analyses, min_score_threshold)
                selected_count = sum(1 for a in analyses if a.selected)
                logger.info(f"Selected {selected_count} floor plan pages with scores >= {min_score_threshold}")
            else:
                best_page_num = self._select_best_page(analyses)
            
            total_time = time.time() - start_time
            logger.info(f"Multi-page analysis completed in {total_time:.2f}s")
            # Log detailed selection reasoning
            for analysis in analyses:
                if analysis.selected:
                    logger.info(f"Selected page {analysis.page_number} as floor plan - "
                              f"Type: {analysis.page_type}, Score: {analysis.score}, "
                              f"Rectangles: {analysis.rectangle_count}, "
                              f"Room Labels: {analysis.room_label_count}")
            
            return best_page_num, analyses
            
        finally:
            doc.close()
    
    def _analyze_single_page(self, doc: fitz.Document, page_num: int) -> PageAnalysis:
        """
        Analyze a single page for floor plan characteristics
        
        Args:
            doc: Opened PyMuPDF document
            page_num: Zero-based page number
            
        Returns:
            PageAnalysis with scoring results
        """
        page = doc[page_num]
        
        try:
            # Quick complexity check - count drawing elements
            drawings = page.get_drawings()
            element_count = len(drawings)
            
            # Progressive complexity handling - don't reject complex pages outright
            if element_count > MAX_ELEMENTS_PER_PAGE:
                logger.warning(f"Page {page_num + 1} has {element_count} elements, exceeding soft limit of {MAX_ELEMENTS_PER_PAGE}")
                # Mark as complex but still try to process if it's likely a floor plan
                # Only hard reject if it's way over limit (>200k elements)
                if element_count > 200000:
                    logger.error(f"Page {page_num + 1} has {element_count} elements - too complex to process")
                    return PageAnalysis(
                        page_number=page_num + 1,
                        score=0.0,
                        rectangle_count=0,
                        room_label_count=0,
                        dimension_count=0,
                        text_element_count=0,
                        geometric_complexity=element_count,
                        processing_time=0.0,
                        too_complex=True
                    )
                # Otherwise, continue processing but note the complexity
                logger.info(f"Processing complex page {page_num + 1} despite high element count")
            
            # Extract text for analysis
            text_content = page.get_text()
            text_words = text_content.split() if text_content else []
            
            # Detect page type
            page_type = self._detect_page_type(text_content)
            
            # Count geometric elements
            rectangles = self._count_rectangles(drawings)
            
            # Count room labels with context awareness
            room_labels = self._count_room_labels(text_content)
            
            # Count dimensions
            dimensions = self._count_dimensions(text_content)
            
            # Calculate floor plan score with page type awareness
            score = self._calculate_floor_plan_score(
                rectangles, room_labels, dimensions, len(drawings), len(text_words), page_type
            )
            
            logger.info(f"Page {page_num + 1} detected as {page_type} with score {score}")
            
            return PageAnalysis(
                page_number=page_num + 1,
                score=score,
                rectangle_count=rectangles,
                room_label_count=room_labels,
                dimension_count=dimensions,
                text_element_count=len(text_words),
                geometric_complexity=len(drawings),
                processing_time=0.0,  # Will be set by caller
                page_type=page_type  # Store detected page type
            )
            
        except Exception as e:
            logger.error(f"Error analyzing page {page_num + 1}: {str(e)}")
            return PageAnalysis(
                page_number=page_num + 1,
                score=0.0,
                rectangle_count=0,
                room_label_count=0,
                dimension_count=0,
                text_element_count=0,
                geometric_complexity=0,
                processing_time=0.0,
                error=str(e)
            )
    
    def _count_rectangles(self, drawings: List) -> int:
        """Count rectangular shapes that could be rooms"""
        rectangle_count = 0
        
        for drawing in drawings:
            # PyMuPDF drawing items have 'items' containing the actual shapes
            if hasattr(drawing, 'items'):
                for item in drawing['items']:
                    # Look for rectangular paths
                    if item[0] == 'l':  # Line item
                        # A rectangle would typically be 4 connected lines
                        pass  # Simplified - in production would analyze path structure
                    elif item[0] == 're':  # Rectangle item
                        rectangle_count += 1
        
        # Fallback: estimate from total drawings (rough heuristic)
        if rectangle_count == 0:
            # Assume ~10% of drawings are potential room rectangles
            rectangle_count = max(1, len(drawings) // 10)
        
        return rectangle_count
    
    def _detect_page_type(self, text: str) -> str:
        """Detect the type of page based on text content"""
        if not text:
            return "unknown"
        
        text_lower = text.lower()
        
        # Check for elevation indicators FIRST (to catch them early)
        # Count elevation indicators
        elevation_count = sum(1 for indicator in ELEVATION_INDICATORS 
                            if indicator in text_lower[:2000])  # Check more text
        elevation_rejection_count = sum(1 for pattern in ELEVATION_REJECTION_PATTERNS 
                                      if pattern in text_lower)
        
        # Strong elevation detection
        if elevation_count >= 1 and elevation_rejection_count >= 2:
            return "elevation"
        if any(indicator in text_lower[:500] for indicator in 
               ['elevation', 'front view', 'side view', 'rear view', 'facade']):
            # Check if it's really an elevation (not "floor plan elevation" etc)
            if 'floor plan' not in text_lower[:500]:
                return "elevation"
        
        # Check for floor plan indicators (high priority)
        for indicator in FLOOR_PLAN_INDICATORS:
            if indicator in text_lower[:1500]:  # Check in first 1500 chars
                # Make sure it's not in a list of elevations
                if 'elevation' not in text_lower[max(0, text_lower.find(indicator)-50):
                                                text_lower.find(indicator)+50]:
                    return "floor_plan"
        
        # Check for specification indicators
        spec_count = sum(1 for indicator in SPECIFICATION_INDICATORS if indicator in text_lower)
        if spec_count >= 2:  # Multiple spec indicators = likely a spec page
            return "specification"
        
        return "unknown"
    
    def _count_room_labels(self, text: str) -> int:
        """Count room labels in text content with context awareness"""
        if not text:
            return 0
        
        text_lower = text.lower()
        
        # If this is a specification page, don't count room keywords as heavily
        page_type = self._detect_page_type(text)
        if page_type == "specification":
            # Only count room labels that appear to be actual labels (with dimensions)
            room_count = 0
            for keyword in ROOM_KEYWORDS:
                # Look for room keyword followed by dimension pattern
                pattern = r'\b' + re.escape(keyword) + r'\b.*?\d+[\'"].*?\d+[\'"]'
                matches = re.findall(pattern, text_lower)
                room_count += len(matches)
            return min(room_count, 10)  # Cap specification page room count
        
        # For non-specification pages, use normal counting
        room_count = 0
        
        for keyword in ROOM_KEYWORDS:
            # Count occurrences of each room keyword
            occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
            room_count += occurrences
        
        # Look for numbered rooms (BR1, BR2, etc.)
        numbered_rooms = len(re.findall(r'\b(bed|bath|room|br|ba)\s*\d+\b', text_lower))
        room_count += numbered_rooms
        
        return room_count
    
    def _count_dimensions(self, text: str) -> int:
        """Count dimension annotations in text"""
        if not text:
            return 0
        
        dimension_count = 0
        
        for pattern in DIMENSION_PATTERNS:
            matches = re.findall(pattern, text)
            dimension_count += len(matches)
        
        return dimension_count
    
    def _calculate_floor_plan_score(self, rectangles: int, room_labels: int, 
                                   dimensions: int, total_drawings: int, 
                                   text_words: int, page_type: str = "unknown") -> float:
        """
        Calculate floor plan likelihood score for a page
        
        Higher scores indicate better floor plan candidates
        """
        score = 0.0
        
        # Page type bonuses/penalties (ADJUSTED)
        if page_type == "floor_plan":
            score += 50  # Strong bonus for detected floor plans
            logger.debug(f"Added 50 points for floor_plan page type")
        elif page_type == "specification":
            score -= 50  # Stronger penalty for specification pages
            logger.debug(f"Subtracted 50 points for specification page type")
        elif page_type == "elevation":
            score -= 60  # Much stronger penalty for elevation pages
            logger.debug(f"Subtracted 60 points for elevation page type")
        
        # Rectangle count (potential rooms): +2 points per rectangle, up to 40 points
        rect_score = min(rectangles * 2, 40)
        score += rect_score
        if rect_score > 0:
            logger.debug(f"Added {rect_score} points for {rectangles} rectangles")
        
        # Room labels: +5 points per room label, up to 50 points
        # Reduced weight if specification page
        if page_type == "specification":
            room_score = min(room_labels * 2, 20)  # Much less weight for specs
        else:
            room_score = min(room_labels * 5, 50)
        score += room_score
        if room_score > 0:
            logger.debug(f"Added {room_score} points for {room_labels} room labels")
        
        # Dimensions: +3 points per dimension, up to 30 points
        dim_score = min(dimensions * 3, 30)
        score += dim_score
        if dim_score > 0:
            logger.debug(f"Added {dim_score} points for {dimensions} dimensions")
        
        # Geometric complexity bonus (moderate to high complexity often indicates detailed floor plans)
        if 50 <= total_drawings <= 5000:
            score += 20  # Good range for floor plans
            logger.debug(f"Added 20 points for ideal drawing complexity ({total_drawings} drawings)")
        elif 5000 < total_drawings <= 50000:
            score += 15  # Complex but likely still a detailed floor plan
            logger.debug(f"Added 15 points for high drawing complexity ({total_drawings} drawings)")
        elif 20 <= total_drawings < 50:
            score += 10  # Acceptable but simple
            logger.debug(f"Added 10 points for simple drawing complexity ({total_drawings} drawings)")
        elif total_drawings > 50000:
            score += 5   # Very complex, but could still be main floor plan
            logger.debug(f"Added 5 points for very high drawing complexity ({total_drawings} drawings)")
        
        # Text density bonus (floor plans should have some text but not be document pages)
        if 10 <= text_words <= 200:
            score += 10  # Good balance of text
            logger.debug(f"Added 10 points for ideal text density ({text_words} words)")
        elif text_words > 500:
            penalty = -10 if page_type != "floor_plan" else -5  # Less penalty if detected as floor plan
            score += penalty
            logger.debug(f"Added {penalty} points for high text density ({text_words} words)")
        
        # Minimum viable score threshold
        if rectangles == 0 and room_labels == 0 and page_type != "floor_plan":
            score = max(score, 0.0)  # Don't go negative unless there's a reason
        
        return round(score, 1)
    
    def _select_best_page(self, analyses: List[PageAnalysis]) -> int:
        """
        Select the best page from analysis results
        
        Args:
            analyses: List of PageAnalysis objects
            
        Returns:
            Page number (1-based) of best page
            
        Raises:
            ValueError: If no suitable pages found
        """
        # First, try pages that aren't marked as errors
        non_error_analyses = [a for a in analyses if not a.error]
        
        if not non_error_analyses:
            # If all pages have errors, use all for consideration
            non_error_analyses = analyses
            logger.warning("All pages have errors, considering all for selection")
        
        # Sort ALL pages by score first (including complex ones)
        # Complex pages might still be the best floor plans
        all_sorted = sorted(non_error_analyses, key=lambda x: x.score, reverse=True)
        
        # Check if a "complex" page has significantly better score
        if all_sorted:
            best_overall = all_sorted[0]
            
            # Filter to non-complex pages
            simple_pages = [a for a in non_error_analyses if not a.too_complex]
            
            if simple_pages:
                best_simple = max(simple_pages, key=lambda x: x.score)
                
                # If complex page has much better score (2x or more), use it
                # This handles cases where main floor plans are complex but important
                if best_overall.too_complex and best_overall.score > best_simple.score * 1.5:
                    logger.info(f"Selecting complex page {best_overall.page_number} with score {best_overall.score} "
                              f"over simpler page {best_simple.page_number} with score {best_simple.score}")
                    best_analysis = best_overall
                else:
                    best_analysis = best_simple
            else:
                # All pages are complex, use the best one
                logger.warning("All pages are complex, using highest scoring page")
                best_analysis = best_overall
        else:
            raise ValueError("No pages could be analyzed")
        
        # Require minimum score threshold
        if best_analysis.score < 10:
            logger.warning(f"Best page score ({best_analysis.score}) is below recommended threshold")
        
        # Mark as selected
        best_analysis.selected = True
        
        logger.info(f"Selected page {best_analysis.page_number} with score {best_analysis.score}, "
                   f"complex={best_analysis.too_complex}, rectangles={best_analysis.rectangle_count}, "
                   f"room_labels={best_analysis.room_label_count}")
        
        return best_analysis.page_number
    
    def _select_multiple_pages(self, analyses: List[PageAnalysis], 
                              min_score_threshold: float = 100.0) -> int:
        """
        Select multiple floor plan pages that meet the threshold
        
        Args:
            analyses: List of PageAnalysis objects
            min_score_threshold: Minimum score to select a page
            
        Returns:
            Page number of the best page (for compatibility)
            Side effect: Marks all qualifying pages as selected
        """
        # Filter to non-error pages
        non_error_analyses = [a for a in analyses if not a.error]
        
        if not non_error_analyses:
            non_error_analyses = analyses
            logger.warning("All pages have errors, considering all for selection")
        
        # Find all pages that:
        # 1. Are detected as floor_plan type OR have high enough score
        # 2. Meet the minimum score threshold
        # 3. Are not too complex (unless they're the only option)
        floor_plan_pages = []
        
        for analysis in non_error_analyses:
            # Strong floor plan detection
            if analysis.page_type == "floor_plan" and analysis.score >= min_score_threshold:
                floor_plan_pages.append(analysis)
                logger.info(f"Page {analysis.page_number} selected as floor plan: "
                          f"score={analysis.score}, type={analysis.page_type}")
            # High score even if type is unknown (but not elevation/spec)
            elif (analysis.page_type not in ["elevation", "specification"] and 
                  analysis.score >= min_score_threshold * 1.2):  # Higher threshold for unknown
                floor_plan_pages.append(analysis)
                logger.info(f"Page {analysis.page_number} selected based on high score: "
                          f"score={analysis.score}, type={analysis.page_type}")
        
        # If no pages qualify, select the single best one
        if not floor_plan_pages:
            logger.warning(f"No pages meet threshold {min_score_threshold}, selecting single best")
            best = max(non_error_analyses, key=lambda x: x.score)
            floor_plan_pages = [best]
        
        # Mark all selected pages
        best_score = 0
        best_page_num = 1
        
        for analysis in floor_plan_pages:
            analysis.selected = True
            if analysis.score > best_score:
                best_score = analysis.score
                best_page_num = analysis.page_number
        
        logger.info(f"Selected {len(floor_plan_pages)} floor plan pages")
        return best_page_num
    
    def _detect_floor_info(self, page: fitz.Page) -> Tuple[Optional[int], Optional[str]]:
        """
        Detect floor number and name from page text
        
        Returns:
            Tuple of (floor_number, floor_name)
        """
        try:
            text = page.get_text()[:1000].upper()  # Check first 1000 chars
            
            # Common floor patterns
            floor_patterns = [
                (r'FIRST\s+FLOOR|1ST\s+FLOOR|LEVEL\s+1', 1, "First Floor"),
                (r'SECOND\s+FLOOR|2ND\s+FLOOR|LEVEL\s+2|UPPER\s+LEVEL|UPSTAIRS', 2, "Second Floor"),
                (r'THIRD\s+FLOOR|3RD\s+FLOOR|LEVEL\s+3', 3, "Third Floor"),
                (r'BASEMENT|LOWER\s+LEVEL|GARDEN\s+LEVEL', 0, "Basement"),
                (r'MAIN\s+FLOOR|MAIN\s+LEVEL|GROUND\s+FLOOR', 1, "Main Floor"),
                (r'UPPER\s+FLOOR', 2, "Upper Floor"),
                (r'BONUS\s+FLOOR|BONUS\s+ROOM', 2, "Bonus Floor"),
                (r'ATTIC|LOFT', 3, "Attic/Loft"),
            ]
            
            for pattern, floor_num, floor_name in floor_patterns:
                if re.search(pattern, text):
                    return floor_num, floor_name
            
            return None, None
            
        except Exception as e:
            logger.debug(f"Error detecting floor info: {e}")
            return None, None
    
    def get_analysis_summary(self, analyses: List[PageAnalysis]) -> Dict[str, Any]:
        """Generate summary of multi-page analysis results"""
        return {
            'total_pages_analyzed': len(analyses),
            'pages_too_complex': sum(1 for a in analyses if a.too_complex),
            'pages_with_errors': sum(1 for a in analyses if a.error),
            'best_page': next((a.page_number for a in analyses if a.selected), None),
            'best_score': next((a.score for a in analyses if a.selected), 0.0),
            'average_score': sum(a.score for a in analyses) / len(analyses) if analyses else 0.0,
            'total_processing_time': sum(a.processing_time for a in analyses),
            'page_details': [
                {
                    'page': a.page_number,
                    'score': a.score,
                    'rectangles': a.rectangle_count,
                    'room_labels': a.room_label_count,
                    'dimensions': a.dimension_count,
                    'selected': a.selected,
                    'too_complex': a.too_complex,
                    'error': a.error,
                    'page_type': a.page_type
                }
                for a in analyses
            ]
        }


def analyze_pdf_for_best_page(pdf_path: str, return_multiple: bool = False,
                             min_score_threshold: float = 100.0) -> Tuple[int, Dict[str, Any]]:
    """
    Convenience function to analyze PDF and return best page(s) with summary
    
    Args:
        pdf_path: Path to PDF file
        return_multiple: If True, select multiple floor plan pages
        min_score_threshold: Minimum score for floor plan selection
        
    Returns:
        Tuple of (best_page_number, analysis_summary)
    """
    analyzer = PDFPageAnalyzer()
    best_page, analyses = analyzer.analyze_pdf_pages(pdf_path, return_multiple, min_score_threshold)
    summary = analyzer.get_analysis_summary(analyses)
    
    return best_page, summary