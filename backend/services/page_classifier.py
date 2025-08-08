"""
Intelligent page classification for blueprint PDFs
Quickly identifies floor plan pages vs elevations/details
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Types of blueprint pages"""
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SITE_PLAN = "site_plan"
    TITLE = "title"
    SCHEDULE = "schedule"
    UNKNOWN = "unknown"


@dataclass
class PageClassification:
    """Classification result for a PDF page"""
    page_num: int
    page_type: PageType
    confidence: float
    features: Dict[str, Any]
    keywords_found: List[str]
    processing_time: float


class PageClassifier:
    """
    Fast page classification for blueprint PDFs
    Goal: Identify floor plan pages in < 0.5s per page
    """
    
    # Keywords that strongly indicate page type
    FLOOR_PLAN_KEYWORDS = [
        "FLOOR PLAN", "FIRST FLOOR", "SECOND FLOOR", "GROUND FLOOR",
        "LEVEL 1", "LEVEL 2", "LEVEL 3", "1ST FLOOR", "2ND FLOOR",
        "MAIN FLOOR", "UPPER FLOOR", "LOWER FLOOR", "BASEMENT PLAN"
    ]
    
    ELEVATION_KEYWORDS = [
        "ELEVATION", "NORTH ELEVATION", "SOUTH ELEVATION",
        "EAST ELEVATION", "WEST ELEVATION", "FRONT ELEVATION",
        "REAR ELEVATION", "SIDE ELEVATION", "LEFT ELEVATION", "RIGHT ELEVATION"
    ]
    
    SECTION_KEYWORDS = [
        "SECTION", "CROSS SECTION", "BUILDING SECTION",
        "WALL SECTION", "DETAIL SECTION", "LONGITUDINAL SECTION"
    ]
    
    DETAIL_KEYWORDS = [
        "DETAIL", "TYPICAL DETAIL", "CONSTRUCTION DETAIL",
        "ENLARGED DETAIL", "CONNECTION DETAIL", "FRAMING DETAIL"
    ]
    
    SITE_KEYWORDS = [
        "SITE PLAN", "PLOT PLAN", "LANDSCAPE PLAN",
        "GRADING PLAN", "DRAINAGE PLAN", "SITE LAYOUT"
    ]
    
    TITLE_KEYWORDS = [
        "TITLE SHEET", "COVER SHEET", "INDEX", "PROJECT INFORMATION",
        "GENERAL NOTES", "SHEET INDEX", "DRAWING LIST"
    ]
    
    # Room-related keywords (weak indicators for floor plans)
    ROOM_KEYWORDS = [
        "BEDROOM", "BATHROOM", "KITCHEN", "LIVING", "DINING",
        "CLOSET", "GARAGE", "ENTRY", "FOYER", "HALLWAY",
        "MASTER", "GUEST", "OFFICE", "LAUNDRY", "PANTRY",
        "FAMILY ROOM", "GREAT ROOM", "DEN", "STUDY"
    ]
    
    def classify_pages(
        self,
        pdf_path: str,
        quick_mode: bool = True
    ) -> List[PageClassification]:
        """
        Classify all pages in a PDF
        
        Args:
            pdf_path: Path to PDF file
            quick_mode: If True, use fast extraction (< 0.5s per page)
            
        Returns:
            List of page classifications sorted by confidence
        """
        classifications = []
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            logger.info(f"Classifying {total_pages} pages in {pdf_path}")
            
            for page_num in range(total_pages):
                start_time = time.time()
                
                # Classify single page
                classification = self._classify_page(
                    doc[page_num],
                    page_num,
                    quick_mode
                )
                
                classification.processing_time = time.time() - start_time
                classifications.append(classification)
                
                logger.debug(f"Page {page_num + 1}: {classification.page_type.value} "
                           f"(confidence: {classification.confidence:.2f}, "
                           f"time: {classification.processing_time:.2f}s)")
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Failed to classify pages: {e}")
            return []
        
        # Sort by confidence for floor plans first, then other types
        def sort_key(c):
            if c.page_type == PageType.FLOOR_PLAN:
                return (0, -c.confidence)  # Floor plans first, highest confidence
            else:
                return (1, -c.confidence)  # Others second
        
        classifications.sort(key=sort_key)
        
        return classifications
    
    def _classify_page(
        self,
        page: fitz.Page,
        page_num: int,
        quick_mode: bool
    ) -> PageClassification:
        """
        Classify a single page
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            quick_mode: Use fast extraction
            
        Returns:
            PageClassification for the page
        """
        features = {}
        keywords_found = []
        
        # Extract text (fast)
        text = page.get_text().upper() if quick_mode else page.get_text("text").upper()
        
        # Extract basic features
        features['text_length'] = len(text)
        features['page_width'] = page.rect.width
        features['page_height'] = page.rect.height
        features['aspect_ratio'] = page.rect.width / page.rect.height if page.rect.height > 0 else 1
        
        # Count text blocks (fast indicator of content density)
        text_blocks = page.get_text_blocks()
        features['text_block_count'] = len(text_blocks)
        
        # Count drawings if not too many (indicator of complexity)
        if quick_mode:
            # Just get count, don't process
            try:
                drawings = page.get_drawings()
                features['drawing_count'] = len(list(drawings)) if drawings else 0
            except:
                features['drawing_count'] = 0
        else:
            features['drawing_count'] = len(page.get_drawings())
        
        # Check for keywords
        keyword_scores = {
            PageType.FLOOR_PLAN: self._check_keywords(text, self.FLOOR_PLAN_KEYWORDS, keywords_found),
            PageType.ELEVATION: self._check_keywords(text, self.ELEVATION_KEYWORDS, keywords_found),
            PageType.SECTION: self._check_keywords(text, self.SECTION_KEYWORDS, keywords_found),
            PageType.DETAIL: self._check_keywords(text, self.DETAIL_KEYWORDS, keywords_found),
            PageType.SITE_PLAN: self._check_keywords(text, self.SITE_KEYWORDS, keywords_found),
            PageType.TITLE: self._check_keywords(text, self.TITLE_KEYWORDS, keywords_found),
        }
        
        # Check for room keywords (weak indicator for floor plans)
        room_count = sum(1 for keyword in self.ROOM_KEYWORDS if keyword in text)
        features['room_keyword_count'] = room_count
        
        # Determine page type and confidence
        page_type, confidence = self._determine_page_type(
            keyword_scores,
            features,
            text
        )
        
        return PageClassification(
            page_num=page_num,
            page_type=page_type,
            confidence=confidence,
            features=features,
            keywords_found=keywords_found,
            processing_time=0.0  # Will be set by caller
        )
    
    def _check_keywords(
        self,
        text: str,
        keywords: List[str],
        found_list: List[str]
    ) -> float:
        """
        Check for keywords and return score
        
        Args:
            text: Text to search in (already uppercase)
            keywords: Keywords to look for
            found_list: List to append found keywords to
            
        Returns:
            Score based on keyword matches
        """
        score = 0.0
        
        for keyword in keywords:
            if keyword in text:
                found_list.append(keyword)
                # First keyword gets full point, subsequent get less
                score += 1.0 / (len(found_list) ** 0.5)
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _determine_page_type(
        self,
        keyword_scores: Dict[PageType, float],
        features: Dict[str, Any],
        text: str
    ) -> Tuple[PageType, float]:
        """
        Determine page type and confidence based on scores and features
        
        Args:
            keyword_scores: Scores for each page type
            features: Extracted page features
            text: Page text
            
        Returns:
            Tuple of (PageType, confidence)
        """
        # Find highest scoring type from keywords
        best_type = PageType.UNKNOWN
        best_score = 0.0
        
        for page_type, score in keyword_scores.items():
            if score > best_score:
                best_score = score
                best_type = page_type
        
        # Calculate confidence
        confidence = best_score
        
        # Boost confidence based on features
        if best_type == PageType.FLOOR_PLAN:
            # Floor plans typically have many room keywords
            if features['room_keyword_count'] >= 3:
                confidence = min(confidence + 0.2, 1.0)
            
            # Floor plans have moderate drawing complexity
            if 1000 < features.get('drawing_count', 0) < 50000:
                confidence = min(confidence + 0.1, 1.0)
            
            # Check for scale notation (strong indicator)
            if "SCALE" in text and ("1/4" in text or "1/8" in text):
                confidence = min(confidence + 0.2, 1.0)
        
        elif best_type == PageType.ELEVATION:
            # Elevations have fewer room keywords
            if features['room_keyword_count'] < 2:
                confidence = min(confidence + 0.1, 1.0)
        
        elif best_type == PageType.TITLE:
            # Title pages have less drawings
            if features.get('drawing_count', 0) < 100:
                confidence = min(confidence + 0.2, 1.0)
        
        # If no strong match, check heuristics
        if best_score < 0.3:
            # Use heuristics to guess
            if features['room_keyword_count'] >= 5:
                # Many room keywords -> likely floor plan
                best_type = PageType.FLOOR_PLAN
                confidence = 0.5
            elif features.get('drawing_count', 0) < 100 and features['text_block_count'] > 20:
                # Lots of text, few drawings -> likely title/schedule
                best_type = PageType.TITLE
                confidence = 0.4
            elif "SECTION" in text:
                best_type = PageType.SECTION
                confidence = 0.4
            else:
                best_type = PageType.UNKNOWN
                confidence = 0.2
        
        return best_type, confidence
    
    def find_best_floor_plan_page(
        self,
        pdf_path: str
    ) -> Optional[int]:
        """
        Quick method to find the most likely floor plan page
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Page number (0-indexed) of best floor plan page, or None
        """
        classifications = self.classify_pages(pdf_path, quick_mode=True)
        
        for classification in classifications:
            if classification.page_type == PageType.FLOOR_PLAN and classification.confidence > 0.5:
                logger.info(f"Best floor plan page: {classification.page_num + 1} "
                          f"(confidence: {classification.confidence:.2f})")
                return classification.page_num
        
        # No confident floor plan found
        logger.warning("No confident floor plan page found")
        return None
    
    def get_pages_by_type(
        self,
        classifications: List[PageClassification],
        page_type: PageType,
        min_confidence: float = 0.5
    ) -> List[int]:
        """
        Get page numbers of a specific type
        
        Args:
            classifications: List of page classifications
            page_type: Type to filter for
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of page numbers (0-indexed)
        """
        return [
            c.page_num
            for c in classifications
            if c.page_type == page_type and c.confidence >= min_confidence
        ]


# Create singleton instance
page_classifier = PageClassifier()