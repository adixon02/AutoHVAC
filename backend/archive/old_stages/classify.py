"""
Page Classification Stage with Scoring Algorithm
Uses weighted scoring to identify floor plan pages
"""

import logging
import fitz
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Information about a single page"""
    page_num: int
    page_type: str  # "floor_plan", "elevation", "section", "other"
    floor_number: Optional[int]  # 0=basement, 1=first, 2=second, etc.
    floor_name: Optional[str]  # "First Floor", "Second Floor", etc.
    score: float  # Classification score
    confidence: float  # Confidence level (0-1)
    keywords_found: List[str]


class PageClassifier:
    """
    Smart page classification using scoring algorithm
    Much better than rigid exclude rules
    """
    
    # Keyword weights for scoring
    FLOOR_PLAN_KEYWORDS = {
        # Strong indicators (high weight)
        'FLOOR PLAN': 30,
        'MAIN FLOOR': 25,
        'FIRST FLOOR': 25,
        'SECOND FLOOR': 25,
        'UPPER FLOOR': 25,
        'LOWER FLOOR': 25,
        'BONUS FLOOR': 25,
        'BONUS ROOM': 20,
        'BASEMENT PLAN': 20,
        
        # Room keywords (medium weight)
        'BEDROOM': 5,
        'BATHROOM': 5,
        'KITCHEN': 5,
        'LIVING': 5,
        'DINING': 5,
        'MASTER': 4,
        'FAMILY': 4,
        'OFFICE': 3,
        'GARAGE': 3,
        'CLOSET': 2,
        'PANTRY': 2,
        'LAUNDRY': 2,
        'UTILITY': 2,
        
        # Weak indicators
        'ROOM': 1,
        'HALL': 1,
        'ENTRY': 1,
    }
    
    # Negative indicators (reduce score)
    NEGATIVE_KEYWORDS = {
        # Strong negative (these are definitely not floor plans)
        'FRONT ELEVATION': -50,
        'REAR ELEVATION': -50,
        'LEFT ELEVATION': -50,
        'RIGHT ELEVATION': -50,
        'SIDE ELEVATION': -50,
        'ELECTRICAL PLAN': -40,
        'PLUMBING PLAN': -40,
        'FRAMING PLAN': -40,
        'FOUNDATION PLAN': -30,  # Sometimes combined with floor plan
        'ROOF PLAN': -40,
        'SITE PLAN': -40,
        
        # Moderate negative (might be combined with floor plan)
        'BUILDING SECTION': -15,  # Often on same page as bonus room
        'WALL SECTION': -10,
        'DETAIL': -5,
        'SCHEDULE': -10,
        
        # Weak negative
        'INDEX': -20,
        'NOTES': -5,
        'SPECIFICATIONS': -15,
    }
    
    # Floor level patterns for detection
    FLOOR_PATTERNS = {
        0: ['BASEMENT', 'LOWER LEVEL', 'CELLAR', 'GARDEN LEVEL'],
        1: ['FIRST FLOOR', '1ST FLOOR', 'GROUND FLOOR', 'MAIN FLOOR', 'LEVEL 1'],
        2: ['SECOND FLOOR', '2ND FLOOR', 'UPPER LEVEL', 'LEVEL 2', 'BONUS FLOOR', 'BONUS ROOM'],
        3: ['THIRD FLOOR', '3RD FLOOR', 'LEVEL 3'],
    }
    
    # Scoring thresholds
    MIN_SCORE_THRESHOLD = 30  # Minimum score to consider as floor plan
    HIGH_CONFIDENCE_THRESHOLD = 50  # High confidence floor plan
    
    def identify_floor_plans(self, pdf_path: str) -> List[PageInfo]:
        """
        Main entry point - identify all floor plan pages using scoring
        """
        floor_plans = []
        
        try:
            doc = fitz.open(pdf_path)
            
            logger.info(f"Analyzing {len(doc)} pages in PDF")
            
            # Score each page
            page_scores = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_info = self._score_page(page, page_num)
                
                if page_info:
                    page_scores.append(page_info)
                    logger.debug(f"Page {page_num + 1}: Score={page_info.score:.1f}, "
                               f"Type={page_info.page_type}")
            
            # Select floor plans based on scores
            for page_info in page_scores:
                if page_info.score >= self.MIN_SCORE_THRESHOLD:
                    floor_plans.append(page_info)
                    logger.info(f"Selected page {page_info.page_num + 1}: "
                              f"{page_info.floor_name or 'Floor plan'} "
                              f"(score: {page_info.score:.1f})")
                elif page_info.score > 0:
                    logger.debug(f"Rejected page {page_info.page_num + 1}: "
                               f"Score {page_info.score:.1f} below threshold")
            
            doc.close()
            
            if not floor_plans:
                logger.warning("No floor plans detected in PDF!")
            else:
                logger.info(f"Found {len(floor_plans)} floor plan pages")
                
                # Check for multi-story
                unique_floors = set(p.floor_number for p in floor_plans if p.floor_number is not None)
                if len(unique_floors) > 1:
                    logger.info(f"Multi-story building detected: {len(unique_floors)} floors")
            
            return floor_plans
            
        except Exception as e:
            logger.error(f"Error classifying pages: {e}")
            return []
    
    def _score_page(self, page, page_num: int) -> Optional[PageInfo]:
        """Score a single page using weighted keywords"""
        try:
            # Extract text
            text = page.get_text().upper()
            
            # Initialize score
            score = 0.0
            keywords_found = []
            
            # Score positive keywords
            for keyword, weight in self.FLOOR_PLAN_KEYWORDS.items():
                count = text.count(keyword)
                if count > 0:
                    # Diminishing returns for multiple occurrences
                    keyword_score = weight * (1 + 0.2 * (count - 1))
                    score += keyword_score
                    keywords_found.append(keyword)
                    logger.debug(f"  +{keyword_score:.1f} for '{keyword}' (×{count})")
            
            # Score negative keywords
            for keyword, weight in self.NEGATIVE_KEYWORDS.items():
                if keyword in text:
                    score += weight  # Weight is negative
                    logger.debug(f"  {weight} for '{keyword}'")
            
            # Bonus for having scale notation
            if 'SCALE:' in text or '1/4"=' in text or '1/8"=' in text:
                score += 10
                logger.debug(f"  +10 for scale notation")
            
            # Bonus for square footage notation
            if 'SQ FT' in text or 'SQFT' in text or 'SF' in text:
                score += 5
                logger.debug(f"  +5 for square footage")
            
            # Determine page type based on score and keywords
            if score >= self.MIN_SCORE_THRESHOLD:
                page_type = "floor_plan"
            elif any(elev in text for elev in ['ELEVATION', 'ELEVATIONS']):
                page_type = "elevation"
            elif 'SECTION' in text:
                page_type = "section"
            else:
                page_type = "other"
            
            # Detect floor level
            floor_number, floor_name = self._detect_floor_level(text)
            
            # Calculate confidence
            if score >= self.HIGH_CONFIDENCE_THRESHOLD:
                confidence = min(0.95, 0.5 + score / 100)
            elif score >= self.MIN_SCORE_THRESHOLD:
                confidence = 0.5 + (score - self.MIN_SCORE_THRESHOLD) / 40
            else:
                confidence = max(0.1, score / self.MIN_SCORE_THRESHOLD * 0.5)
            
            return PageInfo(
                page_num=page_num,
                page_type=page_type,
                floor_number=floor_number,
                floor_name=floor_name,
                score=score,
                confidence=confidence,
                keywords_found=keywords_found[:10]  # Limit to top 10
            )
            
        except Exception as e:
            logger.debug(f"Error scoring page {page_num}: {e}")
            return None
    
    def _detect_floor_level(self, text: str) -> tuple[Optional[int], Optional[str]]:
        """Detect which floor this is"""
        for floor_num, patterns in self.FLOOR_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    floor_name = self._get_floor_name(floor_num)
                    return floor_num, floor_name
        
        # If no explicit floor found but has rooms, assume first floor
        if any(room in text for room in ['LIVING', 'KITCHEN', 'DINING']):
            return 1, "First Floor (assumed)"
        
        return None, None
    
    def _get_floor_name(self, floor_num: int) -> str:
        """Get human-readable floor name"""
        names = {
            0: "Basement",
            1: "First Floor",
            2: "Second Floor",
            3: "Third Floor",
        }
        return names.get(floor_num, f"Floor {floor_num}")


# Module-level convenience function
def identify_floor_plans(pdf_path: str) -> List[PageInfo]:
    """Convenience function"""
    classifier = PageClassifier()
    return classifier.identify_floor_plans(pdf_path)