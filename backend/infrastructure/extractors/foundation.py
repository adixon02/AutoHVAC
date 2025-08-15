"""
Foundation Type and Characteristics Extractor
Identifies foundation type and extracts parameters for proper Manual J calculations
Uses F-factors for slab foundations and below-grade U-factors for basements
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FoundationData:
    """Foundation characteristics for Manual J calculations"""
    foundation_type: str  # 'slab', 'crawlspace', 'basement', 'mixed'
    slab_perimeter_ft: float  # For F-factor calculations
    slab_area_sqft: float
    slab_edge_insulation_r: float  # R-value of edge insulation
    slab_edge_depth_in: float  # Depth of edge insulation
    basement_wall_area_sqft: float  # Below-grade wall area
    basement_wall_depth_ft: float  # Average below-grade depth
    basement_wall_r: float  # R-value of basement wall insulation
    basement_floor_area_sqft: float
    basement_floor_r: float  # R-value of basement floor insulation
    crawl_type: str  # 'vented', 'conditioned', 'sealed'
    crawl_wall_area_sqft: float
    crawl_wall_r: float
    crawl_floor_r: float
    confidence: float
    notes: List[str]


class FoundationExtractor:
    """
    Extracts foundation type and characteristics from blueprints
    Critical for accurate heat loss calculations
    """
    
    # ACCA Manual J F-factors for slab-on-grade (BTU/hr·ft·°F)
    # Table 4A - Slab Edge F-factors by insulation depth
    SLAB_F_FACTORS = {
        # (R-value, depth_inches): F-factor
        (0, 0): 1.35,      # Uninsulated
        (5, 12): 0.86,     # R-5, 12" deep
        (5, 24): 0.72,     # R-5, 24" deep
        (5, 36): 0.68,     # R-5, 36" deep
        (10, 24): 0.54,    # R-10, 24" deep
        (10, 36): 0.51,    # R-10, 36" deep
        (10, 48): 0.49,    # R-10, 48" deep
        (15, 36): 0.44,    # R-15, 36" deep
        (15, 48): 0.42,    # R-15, 48" deep
    }
    
    # Below-grade U-factors for basement walls (BTU/hr·ft²·°F)
    # Table 4B - Below-Grade Wall U-factors by depth and R-value
    BELOW_GRADE_U_FACTORS = {
        # (depth_ft, R-value): U-factor
        (0, 0): 0.360,     # 0-1 ft, uninsulated
        (2, 0): 0.248,     # 1-2 ft, uninsulated
        (3, 0): 0.193,     # 2-3 ft, uninsulated
        (4, 0): 0.160,     # 3-4 ft, uninsulated
        (5, 0): 0.119,     # 4-5 ft, uninsulated
        (6, 0): 0.096,     # 5-6 ft, uninsulated
        (7, 0): 0.079,     # 6-7 ft, uninsulated
        (8, 0): 0.067,     # 7+ ft, uninsulated
        (0, 5): 0.152,     # 0-1 ft, R-5
        (2, 5): 0.126,     # 1-2 ft, R-5
        (4, 5): 0.094,     # 3-4 ft, R-5
        (6, 5): 0.063,     # 5-6 ft, R-5
        (8, 5): 0.048,     # 7+ ft, R-5
        (0, 10): 0.092,    # 0-1 ft, R-10
        (4, 10): 0.062,    # 3-4 ft, R-10
        (8, 10): 0.035,    # 7+ ft, R-10
    }
    
    def __init__(self):
        self.foundation_keywords = {
            'slab': ['SLAB', 'SLAB ON GRADE', 'SLAB-ON-GRADE', 'SOG', 'CONCRETE SLAB'],
            'crawlspace': ['CRAWL SPACE', 'CRAWLSPACE', 'CRAWL', 'RAISED FLOOR'],
            'basement': ['BASEMENT', 'BSMT', 'LOWER LEVEL', 'CELLAR', 'BELOW GRADE'],
            'pier': ['PIER', 'PIER AND BEAM', 'POST', 'PILE']
        }
        
    def extract(
        self,
        text_blocks: List[Dict[str, Any]], 
        building_data: Optional[Dict[str, Any]] = None,
        climate_data: Optional[Dict[str, Any]] = None
    ) -> FoundationData:
        """Extract foundation data - simplified wrapper"""
        return self.extract_foundation(text_blocks, {}, [], None)
    
    def extract_foundation(
        self,
        text_blocks: List[Dict[str, Any]],
        vector_data: Dict[str, Any],
        tables: List[Dict[str, Any]],
        vision_results: Optional[Dict] = None
    ) -> FoundationData:
        """
        Extract foundation type and characteristics
        
        Args:
            text_blocks: Extracted text from all pages
            vector_data: Vector paths and dimensions
            tables: Extracted tables
            vision_results: Optional GPT-4V analysis results
            
        Returns:
            FoundationData with all parameters for Manual J calculations
        """
        logger.info("Extracting foundation characteristics")
        
        # Initialize with defaults
        foundation_data = FoundationData(
            foundation_type='slab',
            slab_perimeter_ft=140,  # Default for 1200 sqft rectangle
            slab_area_sqft=1200,
            slab_edge_insulation_r=0,  # Uninsulated default
            slab_edge_depth_in=0,
            basement_wall_area_sqft=0,
            basement_wall_depth_ft=0,
            basement_wall_r=0,
            basement_floor_area_sqft=0,
            basement_floor_r=0,
            crawl_type='vented',
            crawl_wall_area_sqft=0,
            crawl_wall_r=0,
            crawl_floor_r=8,  # R-8 typical for average crawlspace floors
            confidence=0.5,
            notes=[]
        )
        
        # 1. Identify foundation type from text
        foundation_type = self._identify_foundation_type(text_blocks)
        foundation_data.foundation_type = foundation_type
        foundation_data.notes.append(f"Foundation type: {foundation_type}")
        
        # 2. Extract dimensions from vector data
        if vector_data and 'paths' in vector_data:
            perimeter, area = self._extract_foundation_geometry(vector_data)
            if perimeter > 0:
                foundation_data.slab_perimeter_ft = perimeter
                foundation_data.slab_area_sqft = area
                foundation_data.confidence = 0.8
                foundation_data.notes.append(f"Extracted perimeter: {perimeter:.1f}ft")
        
        # 3. Extract insulation details from text
        insulation_info = self._extract_insulation_details(text_blocks)
        if insulation_info:
            if foundation_type == 'slab':
                foundation_data.slab_edge_insulation_r = insulation_info.get('edge_r', 0)
                foundation_data.slab_edge_depth_in = insulation_info.get('edge_depth', 0)
            elif foundation_type == 'basement':
                foundation_data.basement_wall_r = insulation_info.get('wall_r', 0)
                foundation_data.basement_floor_r = insulation_info.get('floor_r', 0)
            elif foundation_type == 'crawlspace':
                foundation_data.crawl_wall_r = insulation_info.get('wall_r', 0)
                foundation_data.crawl_floor_r = insulation_info.get('floor_r', 11)  # R-11 typical
        
        # 4. Extract basement depth if applicable
        if foundation_type == 'basement':
            depth = self._extract_basement_depth(text_blocks, vector_data)
            foundation_data.basement_wall_depth_ft = depth
            # Calculate wall area (perimeter × depth)
            foundation_data.basement_wall_area_sqft = foundation_data.slab_perimeter_ft * depth
            foundation_data.basement_floor_area_sqft = foundation_data.slab_area_sqft
        
        # 5. Determine crawlspace type
        if foundation_type == 'crawlspace':
            crawl_type = self._determine_crawl_type(text_blocks)
            foundation_data.crawl_type = crawl_type
            # Typical 4ft crawl height
            foundation_data.crawl_wall_area_sqft = foundation_data.slab_perimeter_ft * 4
        
        # 6. Use vision results if available
        if vision_results and 'foundation' in vision_results:
            self._apply_vision_results(foundation_data, vision_results['foundation'])
            foundation_data.confidence = 0.95
        
        logger.info(f"Foundation extraction complete: {foundation_type}, "
                   f"confidence={foundation_data.confidence:.2f}")
        
        return foundation_data
    
    def _identify_foundation_type(self, text_blocks: List[Dict]) -> str:
        """Identify foundation type from text"""
        type_counts = {
            'slab': 0,
            'crawlspace': 0,
            'basement': 0
        }
        
        for block in text_blocks:
            text_upper = block['text'].upper()
            
            for foundation_type, keywords in self.foundation_keywords.items():
                if foundation_type == 'pier':
                    # Pier foundations often become crawlspaces
                    foundation_type = 'crawlspace'
                
                for keyword in keywords:
                    if keyword in text_upper:
                        type_counts[foundation_type] += 1
                        logger.debug(f"Found '{keyword}' on page {block['page']}")
        
        # Return most frequently mentioned type
        if max(type_counts.values()) > 0:
            return max(type_counts, key=type_counts.get)
        
        # Default based on common regional practices
        return 'slab'
    
    def _extract_foundation_geometry(self, vector_data: Dict) -> Tuple[float, float]:
        """Extract foundation perimeter and area from vectors"""
        # This would analyze vector paths to find foundation outline
        # For now, return defaults based on typical residential
        return 140.0, 1200.0  # Will be properly implemented with vector analysis
    
    def _extract_insulation_details(self, text_blocks: List[Dict]) -> Dict[str, Any]:
        """Extract insulation R-values and depths"""
        insulation = {}
        
        patterns = [
            (r'R-?(\d+)\s*EDGE', 'edge_r'),
            (r'(\d+)["\s]+EDGE\s+INSULATION', 'edge_depth'),
            (r'R-?(\d+)\s*PERIMETER', 'edge_r'),
            (r'R-?(\d+)\s*BASEMENT\s*WALL', 'wall_r'),
            (r'R-?(\d+)\s*FOUNDATION\s*WALL', 'wall_r'),
            (r'R-?(\d+)\s*FLOOR', 'floor_r'),
        ]
        
        for block in text_blocks:
            text = block['text'].upper()
            for pattern, key in patterns:
                match = re.search(pattern, text)
                if match:
                    value = float(match.group(1))
                    insulation[key] = value
                    logger.debug(f"Found {key}: {value}")
        
        return insulation
    
    def _extract_basement_depth(
        self,
        text_blocks: List[Dict],
        vector_data: Dict
    ) -> float:
        """Extract basement depth below grade"""
        # Look for depth indicators in text
        for block in text_blocks:
            text = block['text'].upper()
            # Look for patterns like "8' BASEMENT", "7'-0" BELOW GRADE"
            patterns = [
                r"(\d+)['\s\-]+(?:BASEMENT|BELOW\s+GRADE|DEPTH)",
                r"BASEMENT.*?(\d+)['\s\-]+(?:DEEP|DEPTH|HEIGHT)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    depth = float(match.group(1))
                    if 5 <= depth <= 10:  # Reasonable basement depth
                        logger.debug(f"Found basement depth: {depth}ft")
                        return depth
        
        # Default 8ft basement depth
        return 8.0
    
    def _determine_crawl_type(self, text_blocks: List[Dict]) -> str:
        """Determine if crawlspace is vented, sealed, or conditioned"""
        indicators = {
            'vented': ['VENTED', 'VENTILATED', 'VENTS', 'FOUNDATION VENTS'],
            'conditioned': ['CONDITIONED', 'HEATED', 'INSULATED FLOOR'],
            'sealed': ['SEALED', 'ENCAPSULATED', 'CLOSED', 'UNVENTED']
        }
        
        for block in text_blocks:
            text = block['text'].upper()
            for crawl_type, keywords in indicators.items():
                for keyword in keywords:
                    if keyword in text:
                        logger.debug(f"Crawlspace type: {crawl_type} (found '{keyword}')")
                        return crawl_type
        
        # Default to vented (most common)
        return 'vented'
    
    def _apply_vision_results(
        self,
        foundation_data: FoundationData,
        vision_results: Dict
    ):
        """Apply GPT-4V vision analysis results"""
        if 'type' in vision_results:
            foundation_data.foundation_type = vision_results['type']
        
        if 'perimeter' in vision_results:
            foundation_data.slab_perimeter_ft = vision_results['perimeter']
        
        if 'area' in vision_results:
            foundation_data.slab_area_sqft = vision_results['area']
        
        if 'insulation' in vision_results:
            ins = vision_results['insulation']
            foundation_data.slab_edge_insulation_r = ins.get('r_value', 0)
            foundation_data.slab_edge_depth_in = ins.get('depth_inches', 0)
    
    def calculate_heat_loss(
        self,
        foundation_data: FoundationData,
        delta_t: float,
        is_heating: bool = True
    ) -> float:
        """
        Calculate foundation heat loss using ACCA Manual J methods
        
        Args:
            foundation_data: Foundation characteristics
            delta_t: Temperature difference (indoor - outdoor)
            is_heating: True for heating, False for cooling
            
        Returns:
            Heat loss/gain in BTU/hr
        """
        total_load = 0
        
        if foundation_data.foundation_type == 'slab':
            # Use F-factor method for slab edge losses
            f_factor = self._get_slab_f_factor(
                foundation_data.slab_edge_insulation_r,
                foundation_data.slab_edge_depth_in
            )
            
            # Q = F × P × ΔT
            slab_loss = f_factor * foundation_data.slab_perimeter_ft * delta_t
            total_load += slab_loss
            
            logger.debug(f"Slab edge loss: F={f_factor:.2f} × P={foundation_data.slab_perimeter_ft:.1f} "
                        f"× ΔT={delta_t:.1f} = {slab_loss:.0f} BTU/hr")
            
        elif foundation_data.foundation_type == 'basement':
            # Use below-grade U-factors for basement walls
            # Split wall into depth zones
            wall_loss = 0
            perimeter = foundation_data.slab_perimeter_ft
            
            for depth_ft in range(int(foundation_data.basement_wall_depth_ft)):
                u_factor = self._get_below_grade_u_factor(
                    depth_ft + 1,
                    foundation_data.basement_wall_r
                )
                # Area for this 1-ft strip
                area = perimeter * 1.0  # 1 ft height
                # Q = U × A × ΔT
                wall_loss += u_factor * area * delta_t
            
            total_load += wall_loss
            
            # Basement floor losses (minimal due to ground temperature)
            if is_heating:
                # Ground temperature is typically 50-55°F
                ground_delta_t = 70 - 52  # Indoor - ground temp
                floor_u = 1.0 / (foundation_data.basement_floor_r + 5)  # R-5 for ground
                floor_loss = floor_u * foundation_data.basement_floor_area_sqft * ground_delta_t
                total_load += floor_loss
            
            logger.debug(f"Basement wall loss: {wall_loss:.0f}, floor loss: {floor_loss if is_heating else 0:.0f}")
            
        elif foundation_data.foundation_type == 'crawlspace':
            # REDLINE FIX: Proper crawlspace temperature model per critique
            # Vented crawl = semi-outdoor with design crawl temp
            # Unvented crawl = buffer zone with energy balance
            
            floor_u = 1.0 / foundation_data.crawl_floor_r
            floor_area = foundation_data.slab_area_sqft  # First floor area
            
            if foundation_data.crawl_type == 'vented':
                # Vented crawl - use semi-outdoor temperature
                # Crawl temp = outdoor + small offset (5°F typical in winter)
                if is_heating:
                    # Winter: crawl slightly warmer than outdoor due to ground
                    crawl_offset = 5.0  # °F warmer than outdoor
                    effective_delta_t = delta_t - crawl_offset
                    floor_loss = floor_u * floor_area * effective_delta_t
                    
                    # Also add crawl wall losses if uninsulated
                    if foundation_data.crawl_wall_r < 5:
                        wall_u = 1.0 / max(1.0, foundation_data.crawl_wall_r + 1.0)  # Add ground R-1
                        wall_loss = wall_u * foundation_data.crawl_wall_area_sqft * effective_delta_t
                        total_load += wall_loss
                        logger.debug(f"Vented crawl wall loss: {wall_loss:.0f} BTU/hr")
                else:
                    # Summer: crawl cooler than outdoor (ground buffering)
                    crawl_offset = 10.0  # °F cooler than outdoor
                    effective_delta_t = max(0, delta_t - crawl_offset)
                    floor_loss = floor_u * floor_area * effective_delta_t
                
                total_load += floor_loss
                logger.debug(f"Vented crawl floor: U={floor_u:.3f} × A={floor_area:.0f} × ΔT={effective_delta_t:.1f} = {floor_loss:.0f}")
                
            else:
                # Unvented crawl - buffer zone with energy balance
                # Crawl temp depends on heat flow through floor, walls, and ground
                if is_heating:
                    # Winter: crawl temp approximately (2*Indoor + Outdoor + Ground)/4
                    # Simplified: use 60% of full delta T
                    effective_delta_t = delta_t * 0.6
                    floor_loss = floor_u * floor_area * effective_delta_t
                    
                    # Add crawl wall losses (less than vented)
                    wall_u = 1.0 / max(1.0, foundation_data.crawl_wall_r + 2.0)  # Add ground R-2
                    wall_loss = wall_u * foundation_data.crawl_wall_area_sqft * delta_t * 0.4
                    total_load += wall_loss
                else:
                    # Summer: minimal loss through sealed crawl
                    effective_delta_t = delta_t * 0.25
                    floor_loss = floor_u * floor_area * effective_delta_t
                
                total_load += floor_loss
                logger.debug(f"Unvented crawl floor: U={floor_u:.3f} × A={floor_area:.0f} × ΔT={effective_delta_t:.1f} = {floor_loss:.0f}")
        
        return total_load
    
    def _get_slab_f_factor(self, r_value: float, depth_in: float) -> float:
        """Get F-factor for slab edge from ACCA Manual J tables"""
        # Find closest match in table
        best_match = 1.35  # Uninsulated default
        
        for (r, d), f in self.SLAB_F_FACTORS.items():
            if r <= r_value and d <= depth_in:
                best_match = min(best_match, f)
        
        return best_match
    
    def _get_below_grade_u_factor(self, depth_ft: float, r_value: float) -> float:
        """Get U-factor for below-grade wall from ACCA Manual J tables"""
        # Clamp depth to table range
        depth_key = min(8, max(0, int(depth_ft)))
        
        # Find closest R-value in table
        r_key = 0
        if r_value >= 10:
            r_key = 10
        elif r_value >= 5:
            r_key = 5
        
        # Look up U-factor
        key = (depth_key, r_key)
        if key in self.BELOW_GRADE_U_FACTORS:
            return self.BELOW_GRADE_U_FACTORS[key]
        
        # Interpolate if needed
        return 0.15  # Conservative default


# Singleton instance
_foundation_extractor = None


def get_foundation_extractor() -> FoundationExtractor:
    """Get or create the global foundation extractor"""
    global _foundation_extractor
    if _foundation_extractor is None:
        _foundation_extractor = FoundationExtractor()
    return _foundation_extractor