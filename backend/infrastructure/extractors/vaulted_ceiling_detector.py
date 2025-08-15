"""
Vaulted Ceiling Detector
Identifies spaces with vaulted, cathedral, or tray ceilings
These significantly impact heating/cooling loads due to increased volume
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CeilingType(Enum):
    """Types of ceiling configurations"""
    FLAT = "flat"                    # Standard 8-10' ceiling
    VAULTED = "vaulted"              # Sloped following roofline
    CATHEDRAL = "cathedral"          # High peaked ceiling
    TRAY = "tray"                    # Recessed/raised center
    COFFERED = "coffered"            # Grid pattern recessed
    SHED = "shed"                    # Single slope
    OPEN_TO_BELOW = "open_to_below"  # Two-story space
    EXPOSED_BEAM = "exposed_beam"    # Exposed structural beams


@dataclass
class VaultedCeilingResult:
    """Result of vaulted ceiling detection"""
    space_name: str
    ceiling_type: CeilingType
    base_height_ft: float      # Standard ceiling height
    peak_height_ft: float      # Maximum height for vaulted
    volume_multiplier: float   # How much to increase volume
    confidence: float
    evidence: List[str]
    affects_heating: bool      # Does this increase heating load?
    affects_cooling: bool      # Does this increase cooling load?


class VaultedCeilingDetector:
    """
    Detects vaulted and special ceiling conditions.
    Critical for accurate volume and load calculations.
    """
    
    # Text patterns indicating vaulted ceilings
    VAULTED_PATTERNS = [
        r'VAULT(?:ED)?\s*(?:CEILING|CLG|CEIL)',
        r'CATHEDRAL\s*(?:CEILING|CLG)',
        r'COFFERED\s*(?:CEILING|CLG)',
        r'TRAY\s*(?:CEILING|CLG)',
        r'SLOPED\s*(?:CEILING|CLG)',
        r'EXPOSED\s*(?:BEAM|RAFTER)',
        r'OPEN\s*TO\s*(?:ABOVE|BELOW)',
        r'TWO[\s-]?STORY',
        r'DOUBLE[\s-]?HEIGHT',
        r'\d+[\'"\s]+(?:VAULT|CEILING)',  # "12' VAULT"
        r'(?:CEILING|CLG)\s*HT\.?\s*\d+',  # "CEILING HT 14'"
    ]
    
    # Height indicators
    HEIGHT_PATTERNS = [
        r'(\d+)[\'"\s]*(?:CEILING|CLG|VAULT)',  # "14' CEILING"
        r'(?:CEILING|CLG|VAULT)\s*(?:HT\.?|HEIGHT)?\s*[:=]?\s*(\d+)',  # "CLG HT: 12"
        r'(\d+)[\'"\s]*(?:TO|AT)\s*(?:PEAK|RIDGE)',  # "16' TO PEAK"
        r'HT\.?\s*[:=]?\s*(\d+)',  # "HT: 10"
    ]
    
    # Room types more likely to have vaulted ceilings
    LIKELY_VAULTED_ROOMS = [
        'GREAT ROOM', 'LIVING', 'FAMILY', 'MASTER',
        'FOYER', 'ENTRY', 'DINING', 'STUDY'
    ]
    
    # Volume increase factors by ceiling type
    VOLUME_FACTORS = {
        CeilingType.FLAT: 1.0,
        CeilingType.VAULTED: 1.5,      # 50% more volume
        CeilingType.CATHEDRAL: 2.0,     # Double volume
        CeilingType.TRAY: 1.15,         # 15% more
        CeilingType.COFFERED: 1.1,      # 10% more
        CeilingType.SHED: 1.3,          # 30% more
        CeilingType.OPEN_TO_BELOW: 2.0, # Full two stories
        CeilingType.EXPOSED_BEAM: 1.2   # 20% more (thermal bridging)
    }
    
    # Load impact factors
    HEATING_IMPACT = {
        CeilingType.FLAT: 1.0,
        CeilingType.VAULTED: 1.15,      # 15% more heating
        CeilingType.CATHEDRAL: 1.25,     # 25% more heating
        CeilingType.TRAY: 1.05,         # 5% more
        CeilingType.COFFERED: 1.05,
        CeilingType.SHED: 1.10,
        CeilingType.OPEN_TO_BELOW: 1.30, # 30% more (stack effect)
        CeilingType.EXPOSED_BEAM: 1.10   # Thermal bridging
    }
    
    def detect_vaulted_ceilings(
        self,
        text_blocks: List[Dict[str, Any]],
        spaces: Optional[List[Any]] = None,
        page_type: str = "floor_plan"
    ) -> List[VaultedCeilingResult]:
        """
        Detect vaulted ceilings in blueprint.
        
        Args:
            text_blocks: Text extracted from blueprint
            spaces: Optional list of detected spaces
            page_type: Type of blueprint page
            
        Returns:
            List of VaultedCeilingResult for each vaulted space
        """
        results = []
        
        # Process text blocks
        for block in text_blocks:
            text = block.get('text', '').upper()
            
            # Check for vaulted patterns
            for pattern in self.VAULTED_PATTERNS:
                if re.search(pattern, text):
                    result = self._analyze_vaulted_text(text, block)
                    if result:
                        results.append(result)
                        break
        
        # Process spaces if provided
        if spaces:
            for space in spaces:
                space_name = getattr(space, 'name', '')
                
                # Check if space name suggests vaulted
                if any(room in space_name.upper() for room in self.LIKELY_VAULTED_ROOMS):
                    # Look for nearby height annotations
                    result = self._check_space_for_vaulting(space, text_blocks)
                    if result:
                        results.append(result)
        
        # Remove duplicates
        results = self._deduplicate_results(results)
        
        # Log findings
        if results:
            logger.info(f"Found {len(results)} vaulted ceilings:")
            for r in results:
                logger.info(f"  {r.space_name}: {r.ceiling_type.value} "
                          f"({r.peak_height_ft}' peak, "
                          f"{r.volume_multiplier:.1f}x volume)")
        
        return results
    
    def _analyze_vaulted_text(
        self,
        text: str,
        block: Dict[str, Any]
    ) -> Optional[VaultedCeilingResult]:
        """Analyze text block for vaulted ceiling details"""
        
        evidence = []
        ceiling_type = CeilingType.FLAT
        base_height = 9.0  # Default ceiling height
        peak_height = base_height
        
        # Determine ceiling type
        if 'CATHEDRAL' in text:
            ceiling_type = CeilingType.CATHEDRAL
            evidence.append("Cathedral ceiling indicated")
        elif 'VAULT' in text:
            ceiling_type = CeilingType.VAULTED
            evidence.append("Vaulted ceiling indicated")
        elif 'TRAY' in text:
            ceiling_type = CeilingType.TRAY
            evidence.append("Tray ceiling indicated")
        elif 'COFFERED' in text:
            ceiling_type = CeilingType.COFFERED
            evidence.append("Coffered ceiling indicated")
        elif 'OPEN TO' in text:
            ceiling_type = CeilingType.OPEN_TO_BELOW
            evidence.append("Open to below/above")
        elif 'TWO STORY' in text or 'TWO-STORY' in text:
            ceiling_type = CeilingType.OPEN_TO_BELOW
            evidence.append("Two-story space")
        
        # Extract height if present
        for pattern in self.HEIGHT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                try:
                    height = float(match.group(1))
                    if height > base_height:
                        peak_height = height
                        evidence.append(f"Height: {height}' detected")
                except:
                    pass
        
        # Estimate peak height if not found
        if ceiling_type != CeilingType.FLAT and peak_height == base_height:
            if ceiling_type == CeilingType.CATHEDRAL:
                peak_height = 16.0  # Typical cathedral
            elif ceiling_type == CeilingType.VAULTED:
                peak_height = 14.0  # Typical vault
            elif ceiling_type == CeilingType.TRAY:
                peak_height = 10.0  # Typical tray
            elif ceiling_type == CeilingType.OPEN_TO_BELOW:
                peak_height = 18.0  # Two stories
        
        # Extract room name if possible
        space_name = self._extract_room_name(text)
        if not space_name:
            space_name = "Unknown Space"
        
        # Calculate impacts
        volume_multiplier = self.VOLUME_FACTORS[ceiling_type]
        heating_impact = self.HEATING_IMPACT[ceiling_type]
        
        # Calculate confidence
        confidence = 0.5
        if evidence:
            confidence = min(0.9, 0.3 + len(evidence) * 0.2)
        
        if ceiling_type == CeilingType.FLAT:
            return None  # Don't report flat ceilings
        
        return VaultedCeilingResult(
            space_name=space_name,
            ceiling_type=ceiling_type,
            base_height_ft=base_height,
            peak_height_ft=peak_height,
            volume_multiplier=volume_multiplier,
            confidence=confidence,
            evidence=evidence,
            affects_heating=(heating_impact > 1.0),
            affects_cooling=(volume_multiplier > 1.0)
        )
    
    def _check_space_for_vaulting(
        self,
        space: Any,
        text_blocks: List[Dict[str, Any]]
    ) -> Optional[VaultedCeilingResult]:
        """Check if a detected space has vaulted ceiling"""
        
        space_name = getattr(space, 'name', 'Unknown')
        space_area = getattr(space, 'area_sqft', 0)
        
        # Look for text near this space mentioning vaulting
        # This would require spatial analysis of text location
        # For now, use heuristics
        
        if 'GREAT' in space_name.upper() or 'MASTER' in space_name.upper():
            # These often have vaulted ceilings
            return VaultedCeilingResult(
                space_name=space_name,
                ceiling_type=CeilingType.VAULTED,
                base_height_ft=9.0,
                peak_height_ft=14.0,
                volume_multiplier=1.5,
                confidence=0.6,
                evidence=[f"{space_name} commonly has vaulted ceiling"],
                affects_heating=True,
                affects_cooling=True
            )
        
        return None
    
    def _extract_room_name(self, text: str) -> str:
        """Extract room name from text"""
        
        # Common room patterns
        room_patterns = [
            r'((?:MASTER|GREAT|LIVING|FAMILY|DINING|KITCHEN|BED)\s*(?:ROOM|RM)?)',
            r'((?:FOYER|ENTRY|STUDY|OFFICE|DEN))',
            r'(BEDROOM\s*\d+)',
            r'(BR\s*\d+)'
        ]
        
        for pattern in room_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).title()
        
        return ""
    
    def _deduplicate_results(
        self,
        results: List[VaultedCeilingResult]
    ) -> List[VaultedCeilingResult]:
        """Remove duplicate detections"""
        
        unique = {}
        for result in results:
            key = result.space_name.lower()
            if key not in unique or unique[key].confidence < result.confidence:
                unique[key] = result
        
        return list(unique.values())
    
    def calculate_volume_adjustment(
        self,
        base_area_sqft: float,
        base_height_ft: float,
        vaulted_results: List[VaultedCeilingResult]
    ) -> float:
        """
        Calculate total volume adjustment for vaulted ceilings.
        
        Args:
            base_area_sqft: Floor area
            base_height_ft: Standard ceiling height
            vaulted_results: List of vaulted ceiling detections
            
        Returns:
            Adjusted total volume in cubic feet
        """
        
        base_volume = base_area_sqft * base_height_ft
        
        if not vaulted_results:
            return base_volume
        
        # Apply maximum multiplier found
        max_multiplier = max(r.volume_multiplier for r in vaulted_results)
        
        # If multiple vaulted spaces, weight by assumed area
        if len(vaulted_results) > 1:
            # Assume vaulted spaces are 30% of total
            vaulted_fraction = 0.3
            adjusted_multiplier = 1.0 + (max_multiplier - 1.0) * vaulted_fraction
        else:
            # Single vaulted space, assume it's a major space (20% of area)
            adjusted_multiplier = 1.0 + (max_multiplier - 1.0) * 0.2
        
        return base_volume * adjusted_multiplier
    
    def get_load_adjustment_factor(
        self,
        vaulted_results: List[VaultedCeilingResult],
        is_heating: bool = True
    ) -> float:
        """
        Get load adjustment factor for vaulted ceilings.
        
        Args:
            vaulted_results: List of vaulted ceiling detections
            is_heating: True for heating, False for cooling
            
        Returns:
            Multiplication factor for load (1.0 = no adjustment)
        """
        
        if not vaulted_results:
            return 1.0
        
        # Find maximum impact
        max_impact = 1.0
        for result in vaulted_results:
            if is_heating and result.affects_heating:
                impact = self.HEATING_IMPACT[result.ceiling_type]
            elif not is_heating and result.affects_cooling:
                # Cooling impact is primarily from volume
                impact = 1.0 + (result.volume_multiplier - 1.0) * 0.5
            else:
                impact = 1.0
            
            max_impact = max(max_impact, impact)
        
        # If multiple vaulted spaces, moderate the impact
        if len(vaulted_results) > 2:
            # Building has many vaulted spaces
            return 1.0 + (max_impact - 1.0) * 0.7
        else:
            return max_impact


# Singleton instance
_vaulted_detector = None


def get_vaulted_ceiling_detector() -> VaultedCeilingDetector:
    """Get or create the global vaulted ceiling detector"""
    global _vaulted_detector
    if _vaulted_detector is None:
        _vaulted_detector = VaultedCeilingDetector()
    return _vaulted_detector