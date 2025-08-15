"""
Garage Detector
Identifies garage spaces and their footprint for thermal boundary analysis
Critical for detecting bonus-over-garage configurations
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GarageDetectionResult:
    """Result of garage detection"""
    found: bool
    garage_polygon: Optional[List[Tuple[float, float]]]  # Boundary points
    area_sqft: float
    is_heated: bool
    car_capacity: int  # 1, 2, 3 car garage
    page_number: int
    confidence: float
    evidence: List[Dict[str, Any]]


class GarageDetector:
    """
    Detects garage spaces from blueprint text and vectors.
    Critical for identifying thermal boundaries.
    """
    
    # Text patterns that indicate garage
    GARAGE_PATTERNS = [
        r'GARAGE',
        r'GAR\.',
        r'(\d+)\s*CAR\s*GARAGE',
        r'CARPORT',
        r'PARKING',
        r'(\d+)\s*BAY\s*GARAGE'
    ]
    
    # Patterns that indicate heated/conditioned garage (rare)
    HEATED_PATTERNS = [
        r'HEATED\s+GARAGE',
        r'CONDITIONED\s+GARAGE',
        r'FINISHED\s+GARAGE',
        r'WORKSHOP',  # Often heated
    ]
    
    # Typical garage sizes (sqft) for validation
    GARAGE_SIZES = {
        1: (200, 400),   # 1-car garage range
        2: (400, 700),   # 2-car garage range
        3: (600, 1200),  # 3-car garage range
    }
    
    def detect_garage(
        self,
        text_blocks: List[Dict[str, Any]],
        vector_data: Dict[str, Any],
        page_type: str = "main_floor"
    ) -> GarageDetectionResult:
        """
        Detect garage from blueprint data.
        
        Args:
            text_blocks: Text extracted from PDF
            vector_data: Vector paths from PDF
            page_type: Type of blueprint page
            
        Returns:
            GarageDetectionResult with garage details
        """
        logger.info("Detecting garage...")
        
        # 1. Find garage text labels
        garage_texts = self._find_garage_labels(text_blocks)
        
        if not garage_texts:
            logger.info("No garage text found")
            return GarageDetectionResult(
                found=False,
                garage_polygon=None,
                area_sqft=0,
                is_heated=False,
                car_capacity=0,
                page_number=0,
                confidence=0,
                evidence=[]
            )
        
        # 2. Extract garage area from text
        area_sqft, car_capacity = self._extract_garage_size(garage_texts)
        
        # 3. Find garage polygon in vectors (if available)
        garage_polygon = None
        if vector_data and area_sqft > 0:
            garage_polygon = self._find_garage_polygon(
                vector_data, 
                garage_texts[0]['bbox'] if 'bbox' in garage_texts[0] else None,
                area_sqft
            )
        
        # 4. Check if garage is heated
        is_heated = self._check_if_heated(text_blocks)
        
        # 5. Calculate confidence
        confidence = self._calculate_confidence(
            found_text=len(garage_texts) > 0,
            found_area=area_sqft > 0,
            found_polygon=garage_polygon is not None,
            area_reasonable=self._is_area_reasonable(area_sqft, car_capacity)
        )
        
        # 6. Compile evidence
        evidence = []
        for text in garage_texts:
            evidence.append({
                'type': 'text',
                'value': text['text'],
                'location': text.get('bbox', []),
                'page': text.get('page', 0)
            })
        
        if area_sqft > 0:
            evidence.append({
                'type': 'area',
                'value': f"{area_sqft:.0f} sqft",
                'source': 'text_extraction'
            })
        
        result = GarageDetectionResult(
            found=True,
            garage_polygon=garage_polygon,
            area_sqft=area_sqft,
            is_heated=is_heated,
            car_capacity=car_capacity,
            page_number=garage_texts[0].get('page', 1) if garage_texts else 0,
            confidence=confidence,
            evidence=evidence
        )
        
        logger.info(f"Garage detected: {area_sqft:.0f} sqft, {car_capacity}-car, "
                   f"heated={is_heated}, confidence={confidence:.2f}")
        
        return result
    
    def _find_garage_labels(self, text_blocks: List[Dict]) -> List[Dict]:
        """Find text blocks that mention garage"""
        garage_texts = []
        
        for block in text_blocks:
            text = block.get('text', '').upper()
            
            for pattern in self.GARAGE_PATTERNS:
                if re.search(pattern, text):
                    garage_texts.append(block)
                    logger.debug(f"Found garage text: {text}")
                    break
        
        return garage_texts
    
    def _extract_garage_size(
        self, 
        garage_texts: List[Dict]
    ) -> Tuple[float, int]:
        """
        Extract garage area and car capacity from text.
        
        Returns:
            (area_sqft, car_capacity)
        """
        area_sqft = 0
        car_capacity = 2  # Default assumption
        
        for text_block in garage_texts:
            text = text_block.get('text', '').upper()
            
            # Look for explicit area (e.g., "GARAGE 625 SQ FT")
            area_match = re.search(r'GARAGE.*?(\d+)\s*(?:SQ\.?\s*FT\.?|SF)', text)
            if not area_match:
                area_match = re.search(r'(\d+)\s*(?:SQ\.?\s*FT\.?|SF).*?GARAGE', text)
            
            if area_match:
                area_sqft = float(area_match.group(1))
                logger.debug(f"Found garage area: {area_sqft} sqft")
            
            # Look for car capacity (e.g., "2 CAR GARAGE")
            car_match = re.search(r'(\d+)\s*CAR\s*GARAGE', text)
            if car_match:
                car_capacity = int(car_match.group(1))
                logger.debug(f"Found {car_capacity}-car garage")
        
        # If no explicit area, estimate from car capacity
        if area_sqft == 0 and car_capacity > 0:
            # Use middle of typical range
            min_size, max_size = self.GARAGE_SIZES[car_capacity]
            area_sqft = (min_size + max_size) / 2
            logger.debug(f"Estimated {car_capacity}-car garage as {area_sqft} sqft")
        
        return area_sqft, car_capacity
    
    def _find_garage_polygon(
        self,
        vector_data: Dict,
        text_bbox: Optional[List[float]],
        expected_area: float
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Find the polygon representing the garage.
        
        This is simplified for now - full implementation would
        use computational geometry to find the enclosed space.
        """
        # TODO: Implement polygon detection
        # For now, return None (text-based detection is sufficient)
        return None
    
    def _check_if_heated(self, text_blocks: List[Dict]) -> bool:
        """Check if garage is heated/conditioned"""
        for block in text_blocks:
            text = block.get('text', '').upper()
            for pattern in self.HEATED_PATTERNS:
                if re.search(pattern, text):
                    logger.debug(f"Found heated garage indicator: {text}")
                    return True
        return False
    
    def _is_area_reasonable(self, area_sqft: float, car_capacity: int) -> bool:
        """Check if detected area is reasonable for car capacity"""
        if car_capacity == 0 or area_sqft == 0:
            return False
        
        if car_capacity in self.GARAGE_SIZES:
            min_size, max_size = self.GARAGE_SIZES[car_capacity]
            return min_size <= area_sqft <= max_size
        
        return False
    
    def _calculate_confidence(
        self,
        found_text: bool,
        found_area: bool,
        found_polygon: bool,
        area_reasonable: bool
    ) -> float:
        """Calculate detection confidence"""
        score = 0.0
        
        if found_text:
            score += 0.4  # Text is most reliable
        if found_area:
            score += 0.3  # Explicit area is good
        if area_reasonable:
            score += 0.2  # Area makes sense
        if found_polygon:
            score += 0.1  # Polygon is bonus
        
        return min(1.0, score)


# Singleton instance
_garage_detector = None


def get_garage_detector() -> GarageDetector:
    """Get or create the global garage detector"""
    global _garage_detector
    if _garage_detector is None:
        _garage_detector = GarageDetector()
    return _garage_detector