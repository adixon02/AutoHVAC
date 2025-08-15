"""
Blueprint Quality Score Module
Assesses blueprint completeness and routes to appropriate calculation strategies
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Blueprint quality assessment result"""
    value: float  # 0.0 to 1.0 overall quality
    features: Dict[str, float]  # Individual signal scores 0 to 1
    routing_recommendation: str  # "ai_heavy", "hybrid", "conservative"
    confidence_factors: List[str]  # What drove the score


class BlueprintQualityAssessor:
    """
    Analyzes blueprint completeness to determine calculation strategy.
    Routes based on data availability and reliability.
    """
    
    def __init__(self):
        # Feature weights that sum to 1.0
        self.weights = {
            'spec_density_per_page': 0.15,
            'schedules_present': 0.10,
            'sections_elevations_present': 0.10,
            'north_arrow_found': 0.05,
            'ach50_found': 0.10,
            'duct_location_found': 0.10,
            'room_polygonize_success_rate': 0.15,
            'facade_wwr_reconciled': 0.10,
            'area_vector_vs_table_delta': 0.10,
            'foundation_resolved': 0.05
        }
        
        # Routing thresholds
        self.ai_heavy_threshold = 0.8
        self.hybrid_threshold = 0.5
    
    def assess_quality(
        self, 
        extraction_data: Dict[str, Any],
        geometry_data: Dict[str, Any],
        energy_specs: Any
    ) -> QualityScore:
        """
        Assess blueprint quality based on extracted data completeness.
        
        Args:
            extraction_data: Raw extracted data from pipeline
            geometry_data: Room/space detection results  
            energy_specs: Energy specification extraction results
            
        Returns:
            QualityScore with routing recommendation
        """
        
        features = {}
        confidence_factors = []
        
        # 1. Specification density per page (0.15 weight)
        features['spec_density_per_page'] = self._assess_spec_density(
            extraction_data.get('text_blocks', [])
        )
        
        # 2. Schedules present (0.10 weight)
        features['schedules_present'] = self._assess_schedules(
            extraction_data.get('text_blocks', [])
        )
        
        # 3. Sections and elevations present (0.10 weight)
        features['sections_elevations_present'] = self._assess_drawings(
            extraction_data.get('page_classifications', {})
        )
        
        # 4. North arrow found (0.05 weight)
        features['north_arrow_found'] = self._assess_north_arrow(
            extraction_data.get('text_blocks', [])
        )
        
        # 5. ACH50 found (0.10 weight)
        features['ach50_found'] = 1.0 if (energy_specs and energy_specs.ach50) else 0.0
        
        # 6. Duct location found (0.10 weight)
        features['duct_location_found'] = self._assess_duct_location(
            extraction_data.get('text_blocks', [])
        )
        
        # 7. Room polygonization success rate (0.15 weight)
        features['room_polygonize_success_rate'] = self._assess_room_detection(
            geometry_data
        )
        
        # 8. Facade WWR reconciled with elevations (0.10 weight)
        features['facade_wwr_reconciled'] = self._assess_wwr_reconciliation(
            extraction_data
        )
        
        # 9. Area vector vs table delta (0.10 weight)
        features['area_vector_vs_table_delta'] = self._assess_area_consistency(
            extraction_data
        )
        
        # 10. Foundation depth and type resolved (0.05 weight)
        features['foundation_resolved'] = self._assess_foundation_completeness(
            extraction_data
        )
        
        # Calculate weighted score
        total_score = sum(
            features[feature] * self.weights[feature]
            for feature in features
        )
        
        # Determine routing recommendation
        if total_score >= self.ai_heavy_threshold:
            routing = "ai_heavy"
            confidence_factors.append("High spec density enables AI-heavy processing")
        elif total_score >= self.hybrid_threshold:
            routing = "hybrid" 
            confidence_factors.append("Medium spec density requires hybrid approach")
        else:
            routing = "conservative"
            confidence_factors.append("Low spec density requires conservative defaults")
        
        # Add specific confidence factors
        if features['ach50_found'] > 0:
            confidence_factors.append("ACH50 specified increases confidence")
        if features['duct_location_found'] > 0:
            confidence_factors.append("Duct location known improves accuracy")
        if features['room_polygonize_success_rate'] < 0.5:
            confidence_factors.append("Poor room detection reduces confidence")
        
        logger.info(f"Blueprint quality score: {total_score:.2f} -> {routing} routing")
        
        return QualityScore(
            value=total_score,
            features=features,
            routing_recommendation=routing,
            confidence_factors=confidence_factors
        )
    
    def _assess_spec_density(self, text_blocks: List[Dict]) -> float:
        """Assess density of technical specifications per page"""
        if not text_blocks:
            return 0.0
        
        spec_keywords = [
            'r-', 'u-', 'ach50', 'insulation', 'thermal', 'btu', 'cfm',
            'seer', 'hspf', 'efficiency', 'assembly', 'construction'
        ]
        
        pages = {}
        spec_count = 0
        
        for block in text_blocks:
            page = block.get('page', 1)
            text = block.get('text', '').lower()
            
            if page not in pages:
                pages[page] = 0
            
            # Count spec-related text blocks
            if any(keyword in text for keyword in spec_keywords):
                pages[page] += 1
                spec_count += 1
        
        if not pages:
            return 0.0
        
        avg_specs_per_page = spec_count / len(pages)
        
        # Normalize: 0-2 specs/page = 0.0, 2-6 specs/page = 0.5, 6+ specs/page = 1.0
        return min(1.0, max(0.0, (avg_specs_per_page - 2) / 4))
    
    def _assess_schedules(self, text_blocks: List[Dict]) -> float:
        """Check for window, door, and mechanical schedules"""
        if not text_blocks:
            return 0.0
        
        schedule_indicators = [
            'window schedule', 'door schedule', 'equipment schedule',
            'mech schedule', 'schedule', 'symbol', 'legend'
        ]
        
        all_text = ' '.join(block.get('text', '') for block in text_blocks).lower()
        
        found_count = sum(1 for indicator in schedule_indicators if indicator in all_text)
        
        # Normalize: 0 = 0.0, 1-2 = 0.5, 3+ = 1.0
        return min(1.0, found_count / 3)
    
    def _assess_drawings(self, page_classifications: Dict) -> float:
        """Check for sections, elevations, and details"""
        if not page_classifications:
            return 0.0
        
        drawing_types = ['elevation', 'section', 'detail']
        found_types = set()
        
        for page_data in page_classifications.values():
            # Handle both tuple format (page_type, confidence) and dict format
            if isinstance(page_data, tuple):
                page_type = page_data[0] if len(page_data) > 0 else ''
            else:
                page_type = page_data.get('type', '') if hasattr(page_data, 'get') else ''
            
            if page_type in drawing_types:
                found_types.add(page_type)
        
        # Normalize: 0 types = 0.0, 1 type = 0.33, 2 types = 0.67, 3 types = 1.0
        return len(found_types) / 3
    
    def _assess_north_arrow(self, text_blocks: List[Dict]) -> float:
        """Check for north arrow or orientation indicators"""
        if not text_blocks:
            return 0.0
        
        north_indicators = ['north', 'n', '↑', 'arrow', 'orientation']
        
        all_text = ' '.join(block.get('text', '') for block in text_blocks).lower()
        
        return 1.0 if any(indicator in all_text for indicator in north_indicators) else 0.0
    
    def _assess_duct_location(self, text_blocks: List[Dict]) -> float:
        """Check for duct location information"""
        if not text_blocks:
            return 0.0
        
        duct_indicators = [
            'duct', 'hvac', 'mechanical', 'furnace', 'air handler',
            'crawl', 'basement', 'attic', 'plenum'
        ]
        
        all_text = ' '.join(block.get('text', '') for block in text_blocks).lower()
        
        found_count = sum(1 for indicator in duct_indicators if indicator in all_text)
        
        # Normalize: 0 = 0.0, 1-2 = 0.5, 3+ = 1.0
        return min(1.0, found_count / 3)
    
    def _assess_room_detection(self, geometry_data: Dict) -> float:
        """Assess success rate of room polygon detection"""
        if not geometry_data:
            return 0.0
        
        spaces = geometry_data.get('spaces', [])
        if not spaces:
            return 0.0
        
        # Check what percentage of spaces have valid polygons
        valid_spaces = sum(1 for space in spaces if hasattr(space, 'area_sqft') and space.area_sqft > 0)
        
        success_rate = valid_spaces / len(spaces) if spaces else 0.0
        
        return min(1.0, success_rate)
    
    def _assess_wwr_reconciliation(self, extraction_data: Dict) -> float:
        """Check if window-to-wall ratios can be determined from elevations"""
        # Simplified for now - would check elevation analysis vs floor plan
        page_classifications = extraction_data.get('page_classifications', {})
        
        has_elevations = any(
            (data[0] if isinstance(data, tuple) and len(data) > 0 else 
             data.get('type', '') if hasattr(data, 'get') else '') == 'elevation'
            for data in page_classifications.values()
        )
        
        return 0.7 if has_elevations else 0.3
    
    def _assess_area_consistency(self, extraction_data: Dict) -> float:
        """Check consistency between vector-detected and text-extracted areas"""
        detected_area = extraction_data.get('total_sqft', 0)
        
        # If we successfully extracted area from text, score higher
        if detected_area and detected_area != 2000:  # 2000 is default fallback
            return 0.8
        else:
            return 0.2
    
    def _assess_foundation_completeness(self, extraction_data: Dict) -> float:
        """Check if foundation type and details are resolved"""
        foundation_data = extraction_data.get('foundation', {})
        
        if foundation_data:
            foundation_type = foundation_data.get('type', '')
            confidence = foundation_data.get('confidence', 0)
            
            if foundation_type and confidence > 0.5:
                return confidence
        
        return 0.3  # Default low score if foundation unclear


# Singleton instance
_quality_assessor = None

def get_quality_assessor() -> BlueprintQualityAssessor:
    """Get or create the global quality assessor"""
    global _quality_assessor
    if _quality_assessor is None:
        _quality_assessor = BlueprintQualityAssessor()
    return _quality_assessor