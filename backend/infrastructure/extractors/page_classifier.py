"""
Page Classifier
Identifies the type of each page in a multi-page blueprint
Critical for separating main floor, bonus floor, foundation, etc.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Types of blueprint pages"""
    MAIN_FLOOR = "main_floor"
    SECOND_FLOOR = "second_floor"
    BONUS_FLOOR = "bonus_floor"
    BASEMENT = "basement"
    FOUNDATION = "foundation"
    ROOF_PLAN = "roof_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SCHEDULE = "schedule"
    SITE_PLAN = "site_plan"
    UNKNOWN = "unknown"


@dataclass
class PageClassification:
    """Result of page classification"""
    page_number: int
    page_type: PageType
    confidence: float
    evidence: List[str]
    floor_level: Optional[int] = None  # 0=basement, 1=main, 2=second
    has_dimensions: bool = False
    has_room_labels: bool = False
    has_scale: bool = False
    area_sqft: Optional[float] = None


class PageClassifier:
    """
    Classifies blueprint pages by type.
    Essential for multi-story buildings and bonus-over-garage detection.
    """
    
    # Keywords strongly indicating page type
    PAGE_TYPE_KEYWORDS = {
        PageType.MAIN_FLOOR: [
            r'MAIN\s+FLOOR', r'FIRST\s+FLOOR', r'1ST\s+FLOOR',
            r'GROUND\s+FLOOR', r'LEVEL\s+1', r'MAIN\s+LEVEL'
        ],
        PageType.SECOND_FLOOR: [
            r'SECOND\s+FLOOR', r'2ND\s+FLOOR', r'UPPER\s+FLOOR',
            r'UPPER\s+LEVEL', r'LEVEL\s+2', r'UPSTAIRS'
        ],
        PageType.BONUS_FLOOR: [
            r'BONUS\s+ROOM', r'BONUS\s+FLOOR', r'BONUS\s+SPACE',
            r'BONUS\s+LEVEL', r'OVER\s+GARAGE', r'LOFT'
        ],
        PageType.BASEMENT: [
            r'BASEMENT', r'BSMT', r'LOWER\s+LEVEL', r'CELLAR',
            r'BELOW\s+GRADE', r'WALKOUT', r'DAYLIGHT\s+BASEMENT'
        ],
        PageType.FOUNDATION: [
            r'FOUNDATION', r'FOOTING', r'SLAB', r'CRAWL\s*SPACE',
            r'PIER', r'STEM\s+WALL', r'GRADE\s+BEAM'
        ],
        PageType.ROOF_PLAN: [
            r'ROOF\s+PLAN', r'ROOF\s+FRAMING', r'RAFTER',
            r'TRUSS', r'RIDGE', r'HIP', r'VALLEY'
        ],
        PageType.ELEVATION: [
            r'ELEVATION', r'FRONT\s+VIEW', r'SIDE\s+VIEW',
            r'REAR\s+VIEW', r'EXTERIOR'
        ],
        PageType.SECTION: [
            r'SECTION', r'CROSS\s+SECTION', r'BUILDING\s+SECTION',
            r'WALL\s+SECTION', r'DETAIL\s+SECTION'
        ]
    }
    
    # Room labels that indicate floor plans
    ROOM_LABELS = [
        r'BEDROOM', r'BATHROOM', r'KITCHEN', r'LIVING',
        r'DINING', r'GARAGE', r'CLOSET', r'HALL',
        r'MASTER', r'GUEST', r'OFFICE', r'DEN'
    ]
    
    # Dimension patterns
    DIMENSION_PATTERNS = [
        r'\d+[\'"\s]+[-x]\s*\d+[\'"\s]+',  # 12'-6" x 10'-0"
        r'\d+\s*X\s*\d+',  # 12 X 10
        r'\d+\s*SQ\.?\s*FT\.?',  # 1500 SQ FT
        r'\d+\s*SF'  # 1500 SF
    ]
    
    def classify_pages(
        self,
        pages_text: List[List[Dict[str, Any]]],
        images: Optional[List[Any]] = None
    ) -> List[PageClassification]:
        """
        Classify all pages in a blueprint.
        
        Args:
            pages_text: Text blocks for each page
            images: Optional images for each page
            
        Returns:
            List of PageClassification for each page
        """
        classifications = []
        
        for page_num, text_blocks in enumerate(pages_text):
            classification = self.classify_single_page(
                text_blocks,
                page_num,
                images[page_num] if images and page_num < len(images) else None
            )
            classifications.append(classification)
        
        # Post-process to resolve ambiguities
        self._resolve_ambiguities(classifications)
        
        # Log summary
        self._log_classification_summary(classifications)
        
        return classifications
    
    def classify_single_page(
        self,
        text_blocks: List[Dict[str, Any]],
        page_number: int,
        image: Optional[Any] = None
    ) -> PageClassification:
        """
        Classify a single blueprint page.
        
        Args:
            text_blocks: Text extracted from page
            page_number: Page index
            image: Optional page image
            
        Returns:
            PageClassification for the page
        """
        evidence = []
        scores = {page_type: 0.0 for page_type in PageType}
        
        # Combine all text for analysis
        all_text = ' '.join([
            block.get('text', '').upper() 
            for block in text_blocks
        ])
        
        # 1. Check for explicit page type keywords
        for page_type, patterns in self.PAGE_TYPE_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, all_text):
                    scores[page_type] += 10.0
                    evidence.append(f"Found '{pattern}' indicating {page_type.value}")
        
        # 2. Check for room labels (indicates floor plan)
        room_count = 0
        room_labels_found = []
        for pattern in self.ROOM_LABELS:
            matches = re.findall(pattern, all_text)
            if matches:
                room_count += len(matches)
                room_labels_found.extend(matches[:3])  # Keep first 3
        
        if room_count > 5:
            # Many room labels = likely floor plan
            scores[PageType.MAIN_FLOOR] += 5.0
            scores[PageType.SECOND_FLOOR] += 5.0
            scores[PageType.BONUS_FLOOR] += 3.0
            evidence.append(f"Found {room_count} room labels: {', '.join(room_labels_found[:3])}")
        
        # 3. Check for dimensions
        has_dimensions = False
        dimension_count = 0
        for pattern in self.DIMENSION_PATTERNS:
            matches = re.findall(pattern, all_text)
            dimension_count += len(matches)
        
        if dimension_count > 10:
            has_dimensions = True
            evidence.append(f"Found {dimension_count} dimensions")
        
        # 4. Check for scale
        has_scale = bool(re.search(r'SCALE[:\s]+\d', all_text))
        if has_scale:
            evidence.append("Found scale notation")
        
        # 5. Check for area
        area_match = re.search(r'(\d+)\s*(?:TOTAL\s*)?SQ\.?\s*FT\.?', all_text)
        area_sqft = float(area_match.group(1)) if area_match else None
        
        # 6. Special checks for bonus room
        if 'BONUS' in all_text:
            scores[PageType.BONUS_FLOOR] += 8.0
            evidence.append("Explicit 'BONUS' mention")
            
            # Check if it's over garage
            if 'GARAGE' in all_text or 'OVER' in all_text:
                scores[PageType.BONUS_FLOOR] += 5.0
                evidence.append("Bonus over garage indicated")
        
        # 7. Check for garage on main floor
        if re.search(r'\d+\s*CAR\s*GARAGE', all_text) or 'GARAGE' in all_text:
            if scores[PageType.BONUS_FLOOR] < 5:
                scores[PageType.MAIN_FLOOR] += 3.0
                evidence.append("Garage found (likely main floor)")
        
        # 8. Foundation-specific checks
        if any(word in all_text for word in ['FOOTING', 'REBAR', 'CONCRETE', 'STEM WALL']):
            scores[PageType.FOUNDATION] += 5.0
            evidence.append("Foundation construction details found")
        
        # Determine winning page type
        max_score = max(scores.values())
        if max_score > 0:
            page_type = max(scores, key=scores.get)
            confidence = min(1.0, max_score / 20.0)  # Normalize confidence
        else:
            page_type = PageType.UNKNOWN
            confidence = 0.0
        
        # Determine floor level
        floor_level = self._determine_floor_level(page_type, all_text)
        
        return PageClassification(
            page_number=page_number,
            page_type=page_type,
            confidence=confidence,
            evidence=evidence,
            floor_level=floor_level,
            has_dimensions=has_dimensions,
            has_room_labels=room_count > 0,
            has_scale=has_scale,
            area_sqft=area_sqft
        )
    
    def _determine_floor_level(
        self,
        page_type: PageType,
        text: str
    ) -> Optional[int]:
        """Determine which floor level this page represents"""
        
        if page_type == PageType.BASEMENT:
            return 0
        elif page_type == PageType.MAIN_FLOOR:
            return 1
        elif page_type in [PageType.SECOND_FLOOR, PageType.BONUS_FLOOR]:
            return 2
        elif page_type == PageType.FOUNDATION:
            return 0  # Foundation is at ground level
        
        # Try to infer from text
        if 'BASEMENT' in text or 'LOWER' in text:
            return 0
        elif 'MAIN' in text or 'FIRST' in text or '1ST' in text:
            return 1
        elif 'SECOND' in text or '2ND' in text or 'UPPER' in text:
            return 2
        
        return None
    
    def _resolve_ambiguities(
        self,
        classifications: List[PageClassification]
    ):
        """Resolve ambiguous classifications using context"""
        
        # If we have a bonus floor but no second floor, bonus might be the second floor
        has_bonus = any(c.page_type == PageType.BONUS_FLOOR for c in classifications)
        has_second = any(c.page_type == PageType.SECOND_FLOOR for c in classifications)
        
        if has_bonus and not has_second:
            for c in classifications:
                if c.page_type == PageType.BONUS_FLOOR:
                    c.floor_level = 2
                    c.evidence.append("Bonus floor is the second floor")
        
        # If we have multiple UNKNOWN pages with room labels, try to assign them
        unknown_with_rooms = [
            c for c in classifications 
            if c.page_type == PageType.UNKNOWN and c.has_room_labels
        ]
        
        if unknown_with_rooms:
            # Assign based on what's missing
            if not any(c.page_type == PageType.MAIN_FLOOR for c in classifications):
                unknown_with_rooms[0].page_type = PageType.MAIN_FLOOR
                unknown_with_rooms[0].floor_level = 1
                unknown_with_rooms[0].evidence.append("Inferred as main floor (has rooms)")
    
    def _log_classification_summary(
        self,
        classifications: List[PageClassification]
    ):
        """Log summary of page classifications"""
        
        logger.info(f"Classified {len(classifications)} pages:")
        
        for c in classifications:
            logger.info(
                f"  Page {c.page_number}: {c.page_type.value} "
                f"(confidence: {c.confidence:.0%}, floor: {c.floor_level})"
            )
            
            if c.area_sqft:
                logger.info(f"    Area: {c.area_sqft} sqft")
            
            if c.evidence:
                logger.debug(f"    Evidence: {'; '.join(c.evidence[:3])}")
    
    def find_main_floor_page(
        self,
        classifications: List[PageClassification]
    ) -> Optional[PageClassification]:
        """Find the main floor plan page"""
        
        # First try explicit main floor
        for c in classifications:
            if c.page_type == PageType.MAIN_FLOOR:
                return c
        
        # Then try first floor with room labels
        for c in classifications:
            if c.floor_level == 1 and c.has_room_labels:
                return c
        
        return None
    
    def find_bonus_floor_page(
        self,
        classifications: List[PageClassification]
    ) -> Optional[PageClassification]:
        """Find the bonus floor plan page"""
        
        for c in classifications:
            if c.page_type == PageType.BONUS_FLOOR:
                return c
        
        # Check second floor that mentions bonus
        for c in classifications:
            if c.page_type == PageType.SECOND_FLOOR:
                if any('BONUS' in e for e in c.evidence):
                    return c
        
        return None


# Singleton instance
_page_classifier = None


def get_page_classifier() -> PageClassifier:
    """Get or create the global page classifier"""
    global _page_classifier
    if _page_classifier is None:
        _page_classifier = PageClassifier()
    return _page_classifier