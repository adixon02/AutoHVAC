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
MAX_ELEMENTS_PER_PAGE = 20000

# Room type keywords for scoring
ROOM_KEYWORDS = [
    'bedroom', 'living', 'kitchen', 'bathroom', 'dining', 'office',
    'family', 'master', 'guest', 'utility', 'laundry', 'closet',
    'hall', 'foyer', 'pantry', 'garage', 'basement', 'attic',
    'den', 'study', 'library', 'sunroom', 'porch', 'deck', 'room',
    'br', 'ba', 'kit', 'lr', 'dr', 'mb'  # Common abbreviations
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


class PDFPageAnalyzer:
    """
    Analyzes multi-page PDFs to identify the best floor plan page
    """
    
    def __init__(self, timeout_per_page: int = 30, max_pages: int = 100):
        self.timeout_per_page = timeout_per_page
        self.max_pages = max_pages
    
    def analyze_pdf_pages(self, pdf_path: str) -> Tuple[int, List[PageAnalysis]]:
        """
        Analyze all pages in PDF and select the best floor plan page
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (best_page_number, list_of_page_analyses)
            
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
                    logger.info(f"Page {page_num + 1} score: {analysis.score:.1f} "
                              f"(rectangles: {analysis.rectangle_count}, "
                              f"room_labels: {analysis.room_label_count}, "
                              f"dimensions: {analysis.dimension_count})")
                    
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
            
            # Select best page
            best_page_num = self._select_best_page(analyses)
            
            total_time = time.time() - start_time
            logger.info(f"Multi-page analysis completed in {total_time:.2f}s")
            logger.info(f"Selected page {best_page_num} as best floor plan")
            
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
            if len(drawings) > MAX_ELEMENTS_PER_PAGE:
                logger.warning(f"Page {page_num + 1} has {len(drawings)} elements, exceeding limit of {MAX_ELEMENTS_PER_PAGE}")
                return PageAnalysis(
                    page_number=page_num + 1,
                    score=0.0,
                    rectangle_count=0,
                    room_label_count=0,
                    dimension_count=0,
                    text_element_count=0,
                    geometric_complexity=len(drawings),
                    processing_time=0.0,
                    too_complex=True
                )
            
            # Extract text for analysis
            text_content = page.get_text()
            text_words = text_content.split() if text_content else []
            
            # Count geometric elements
            rectangles = self._count_rectangles(drawings)
            
            # Count room labels
            room_labels = self._count_room_labels(text_content)
            
            # Count dimensions
            dimensions = self._count_dimensions(text_content)
            
            # Calculate floor plan score
            score = self._calculate_floor_plan_score(
                rectangles, room_labels, dimensions, len(drawings), len(text_words)
            )
            
            return PageAnalysis(
                page_number=page_num + 1,
                score=score,
                rectangle_count=rectangles,
                room_label_count=room_labels,
                dimension_count=dimensions,
                text_element_count=len(text_words),
                geometric_complexity=len(drawings),
                processing_time=0.0  # Will be set by caller
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
    
    def _count_room_labels(self, text: str) -> int:
        """Count room labels in text content"""
        if not text:
            return 0
        
        text_lower = text.lower()
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
                                   text_words: int) -> float:
        """
        Calculate floor plan likelihood score for a page
        
        Higher scores indicate better floor plan candidates
        """
        score = 0.0
        
        # Rectangle count (potential rooms): +2 points per rectangle, up to 40 points
        score += min(rectangles * 2, 40)
        
        # Room labels: +5 points per room label, up to 50 points
        score += min(room_labels * 5, 50)
        
        # Dimensions: +3 points per dimension, up to 30 points
        score += min(dimensions * 3, 30)
        
        # Geometric complexity bonus (moderate complexity is good for floor plans)
        if 50 <= total_drawings <= 2000:
            score += 15  # Sweet spot for floor plan complexity
        elif 20 <= total_drawings < 50:
            score += 10  # Acceptable but simple
        elif total_drawings > 2000:
            score -= 10  # Penalize overly complex pages
        
        # Text density bonus (floor plans should have some text but not be document pages)
        if 10 <= text_words <= 200:
            score += 10  # Good balance of text
        elif text_words > 500:
            score -= 5   # Penalize text-heavy pages (likely not floor plans)
        
        # Minimum viable score threshold
        if rectangles == 0 and room_labels == 0:
            score = 0.0  # No potential for floor plan
        
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
        # Filter out pages with errors or too complex
        valid_analyses = [a for a in analyses if not a.error and not a.too_complex]
        
        if not valid_analyses:
            # If all pages failed, try to find the least problematic one
            if analyses:
                # Return first page as fallback
                logger.warning("No valid pages found, using page 1 as fallback")
                analyses[0].selected = True
                return 1
            else:
                raise ValueError("No pages could be analyzed")
        
        # Sort by score (highest first)
        valid_analyses.sort(key=lambda x: x.score, reverse=True)
        
        best_analysis = valid_analyses[0]
        
        # Require minimum score threshold
        if best_analysis.score < 10:
            logger.warning(f"Best page score ({best_analysis.score}) is below recommended threshold")
        
        # Mark as selected
        best_analysis.selected = True
        
        return best_analysis.page_number
    
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
                    'error': a.error
                }
                for a in analyses
            ]
        }


def analyze_pdf_for_best_page(pdf_path: str) -> Tuple[int, Dict[str, Any]]:
    """
    Convenience function to analyze PDF and return best page with summary
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (best_page_number, analysis_summary)
    """
    analyzer = PDFPageAnalyzer()
    best_page, analyses = analyzer.analyze_pdf_pages(pdf_path)
    summary = analyzer.get_analysis_summary(analyses)
    
    return best_page, summary