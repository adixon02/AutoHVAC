"""
Volume-Based Infiltration Calculator for Manual J
Calculates whole-building infiltration and distributes by room area
Based on ASHRAE and ACCA methodologies
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InfiltrationMethod(Enum):
    """Method used to determine infiltration"""
    BLOWER_DOOR = "blower_door"  # Measured ACH50/CFM50
    ACH_NATURAL = "ach_natural"  # Direct ACH input
    CONSTRUCTION_QUALITY = "construction_quality"  # Estimated from tightness
    CODE_DEFAULT = "code_default"  # Building code defaults


@dataclass
class InfiltrationResult:
    """Infiltration calculation results"""
    # Whole building values
    total_cfm_natural: float  # Natural infiltration CFM
    total_cfm_heating: float  # Design heating infiltration
    total_cfm_cooling: float  # Design cooling infiltration
    ach_natural: float  # Natural air changes per hour
    ach50: float  # Blower door ACH at 50 Pa
    
    # Per-room distribution (dict of room_name: cfm)
    room_cfm_heating: Dict[str, float]
    room_cfm_cooling: Dict[str, float]
    
    # Metadata
    method: InfiltrationMethod
    confidence: float
    notes: str


class InfiltrationCalculator:
    """
    Calculate whole-building infiltration and distribute to rooms.
    Uses volume-based calculations, not per-room.
    """
    
    # LBL infiltration model factors (Sherman-Grimsrud)
    # Converts ACH50 to natural ACH
    LBL_FACTORS = {
        "1": {"heating": 0.10, "cooling": 0.05},  # Very hot
        "2": {"heating": 0.12, "cooling": 0.06},  # Hot
        "3": {"heating": 0.14, "cooling": 0.07},  # Warm
        "4": {"heating": 0.16, "cooling": 0.08},  # Mixed
        "5": {"heating": 0.18, "cooling": 0.09},  # Cool
        "6": {"heating": 0.20, "cooling": 0.10},  # Cold
        "7": {"heating": 0.22, "cooling": 0.11},  # Very cold
        "8": {"heating": 0.25, "cooling": 0.12},  # Subarctic
    }
    
    # Construction quality to ACH50 estimates
    QUALITY_ACH50 = {
        "very_tight": 1.5,   # Passive house level
        "tight": 3.0,        # Energy Star level
        "average": 7.0,      # Code minimum
        "loose": 12.0,       # Older construction
        "very_loose": 20.0,  # Pre-1950s no air sealing
    }
    
    # Wind exposure adjustments
    WIND_FACTORS = {
        "protected": 0.85,   # Urban, trees
        "normal": 1.0,       # Suburban
        "exposed": 1.15,     # Open field
    }
    
    # Stack effect height factors
    HEIGHT_FACTORS = {
        1: 1.0,   # Single story
        2: 1.15,  # Two story
        3: 1.25,  # Three story
    }
    
    def calculate_infiltration(
        self,
        building_volume: float,
        room_areas: Dict[str, float],
        climate_zone: str,
        blower_door_result: Optional[str] = None,
        construction_quality: Optional[str] = None,
        num_stories: int = 1,
        wind_exposure: str = "normal",
        design_temps: Optional[Dict[str, float]] = None
    ) -> InfiltrationResult:
        """
        Calculate whole-building infiltration and distribute to rooms.
        
        Args:
            building_volume: Total conditioned volume in cubic feet
            room_areas: Dict of room_name: area_sqft for distribution
            climate_zone: IECC climate zone
            blower_door_result: Optional "X ACH50" or "Y CFM50" string
            construction_quality: Optional quality rating
            num_stories: Number of stories (affects stack effect)
            wind_exposure: Wind exposure level
            design_temps: Optional dict with outdoor_heating, outdoor_cooling temps
            
        Returns:
            InfiltrationResult with total and per-room CFM values
        """
        logger.info(f"Calculating infiltration for {building_volume:.0f} ft³ building")
        
        # Step 1: Determine ACH50
        ach50, method = self._determine_ach50(
            building_volume,
            blower_door_result,
            construction_quality
        )
        
        logger.info(f"ACH50: {ach50:.1f} ({method.value})")
        
        # Step 2: Convert to natural infiltration
        zone_num = climate_zone[0] if climate_zone else "4"
        if zone_num not in self.LBL_FACTORS:
            zone_num = "4"
            logger.warning(f"Unknown climate zone {climate_zone}, using zone 4")
        
        lbl = self.LBL_FACTORS[zone_num]
        
        # Natural infiltration (annual average)
        ach_natural = ach50 * ((lbl["heating"] + lbl["cooling"]) / 2)
        cfm_natural = (building_volume * ach_natural) / 60
        
        # Design infiltration (peak conditions)
        # Apply height and wind factors
        height_factor = self.HEIGHT_FACTORS.get(num_stories, 1.0)
        wind_factor = self.WIND_FACTORS.get(wind_exposure, 1.0)
        
        # Heating design (worst case)
        ach_heating = ach50 * lbl["heating"] * height_factor * wind_factor
        cfm_heating = (building_volume * ach_heating) / 60
        
        # Cooling design (less stack effect)
        ach_cooling = ach50 * lbl["cooling"] * wind_factor
        cfm_cooling = (building_volume * ach_cooling) / 60
        
        # Apply temperature adjustments if provided
        if design_temps:
            outdoor_heating = design_temps.get("outdoor_heating", 0)
            outdoor_cooling = design_temps.get("outdoor_cooling", 95)
            indoor = design_temps.get("indoor", 70)
            
            # Stack effect adjustment for heating
            if outdoor_heating < 32:  # Cold climates
                stack_multiplier = 1.0 + (32 - outdoor_heating) / 100
                cfm_heating *= stack_multiplier
            
            # Reduce cooling infiltration in mild conditions
            if outdoor_cooling < 85:
                cfm_cooling *= 0.8
        
        logger.info(f"Natural infiltration: {cfm_natural:.0f} CFM ({ach_natural:.2f} ACH)")
        logger.info(f"Heating design: {cfm_heating:.0f} CFM")
        logger.info(f"Cooling design: {cfm_cooling:.0f} CFM")
        
        # Step 3: Distribute to rooms by area
        total_area = sum(room_areas.values())
        
        room_cfm_heating = {}
        room_cfm_cooling = {}
        
        for room_name, area in room_areas.items():
            # Distribute proportionally by floor area
            area_fraction = area / total_area if total_area > 0 else 0
            
            room_cfm_heating[room_name] = cfm_heating * area_fraction
            room_cfm_cooling[room_name] = cfm_cooling * area_fraction
            
            logger.debug(f"  {room_name}: {area:.0f} sqft -> "
                        f"{room_cfm_heating[room_name]:.0f} CFM heating, "
                        f"{room_cfm_cooling[room_name]:.0f} CFM cooling")
        
        # Determine confidence
        confidence = self._calculate_confidence(method, construction_quality)
        
        # Create notes
        notes = self._generate_notes(method, ach50, num_stories, wind_exposure)
        
        return InfiltrationResult(
            total_cfm_natural=cfm_natural,
            total_cfm_heating=cfm_heating,
            total_cfm_cooling=cfm_cooling,
            ach_natural=ach_natural,
            ach50=ach50,
            room_cfm_heating=room_cfm_heating,
            room_cfm_cooling=room_cfm_cooling,
            method=method,
            confidence=confidence,
            notes=notes
        )
    
    def _determine_ach50(
        self,
        building_volume: float,
        blower_door_result: Optional[str],
        construction_quality: Optional[str]
    ) -> Tuple[float, InfiltrationMethod]:
        """Determine ACH50 from available data"""
        
        # Priority 1: Blower door test
        if blower_door_result:
            result_upper = blower_door_result.upper().strip()
            
            # Parse ACH50
            if "ACH50" in result_upper or "ACH" in result_upper:
                try:
                    # Extract number before ACH
                    import re
                    match = re.search(r'([\d.]+)\s*ACH', result_upper)
                    if match:
                        ach50 = float(match.group(1))
                        return ach50, InfiltrationMethod.BLOWER_DOOR
                except:
                    pass
            
            # Parse CFM50
            if "CFM50" in result_upper or "CFM" in result_upper:
                try:
                    import re
                    match = re.search(r'([\d.]+)\s*CFM', result_upper)
                    if match:
                        cfm50 = float(match.group(1))
                        ach50 = (cfm50 * 60) / building_volume
                        return ach50, InfiltrationMethod.BLOWER_DOOR
                except:
                    pass
        
        # Priority 2: Construction quality
        if construction_quality:
            quality_lower = construction_quality.lower()
            
            # Check vintage-based qualities
            if "19" in quality_lower or "20" in quality_lower:
                # Parse year
                import re
                year_match = re.search(r'(19\d{2}|20\d{2})', quality_lower)
                if year_match:
                    year = int(year_match.group(1))
                    if year < 1950:
                        ach50 = 20.0
                    elif year < 1970:
                        ach50 = 15.0
                    elif year < 1990:
                        ach50 = 10.0
                    elif year < 2010:
                        ach50 = 7.0
                    else:
                        ach50 = 3.0
                    return ach50, InfiltrationMethod.CONSTRUCTION_QUALITY
            
            # Check quality descriptors
            for quality, value in self.QUALITY_ACH50.items():
                if quality.replace("_", " ") in quality_lower or \
                   quality.replace("_", "") in quality_lower:
                    return value, InfiltrationMethod.CONSTRUCTION_QUALITY
        
        # Default: Code minimum
        return 7.0, InfiltrationMethod.CODE_DEFAULT
    
    def _calculate_confidence(
        self,
        method: InfiltrationMethod,
        construction_quality: Optional[str]
    ) -> float:
        """Calculate confidence in infiltration estimate"""
        
        if method == InfiltrationMethod.BLOWER_DOOR:
            return 0.95  # Measured data
        elif method == InfiltrationMethod.ACH_NATURAL:
            return 0.85  # Direct input
        elif method == InfiltrationMethod.CONSTRUCTION_QUALITY:
            if construction_quality and any(
                year in construction_quality 
                for year in ["19", "20"]
            ):
                return 0.70  # Vintage-based
            return 0.60  # Quality-based
        else:
            return 0.40  # Default
    
    def _generate_notes(
        self,
        method: InfiltrationMethod,
        ach50: float,
        num_stories: int,
        wind_exposure: str
    ) -> str:
        """Generate descriptive notes"""
        
        notes = []
        
        # Method note
        if method == InfiltrationMethod.BLOWER_DOOR:
            notes.append(f"Based on blower door test: {ach50:.1f} ACH50")
        elif method == InfiltrationMethod.CONSTRUCTION_QUALITY:
            notes.append(f"Estimated from construction quality: {ach50:.1f} ACH50")
        else:
            notes.append(f"Using code default: {ach50:.1f} ACH50")
        
        # Building characteristics
        if num_stories > 1:
            notes.append(f"{num_stories}-story building (increased stack effect)")
        
        if wind_exposure != "normal":
            notes.append(f"{wind_exposure.title()} wind exposure")
        
        # Tightness classification
        if ach50 < 3:
            notes.append("Very tight construction (Energy Star level)")
        elif ach50 < 5:
            notes.append("Tight construction")
        elif ach50 < 7:
            notes.append("Average construction (code minimum)")
        elif ach50 < 12:
            notes.append("Loose construction")
        else:
            notes.append("Very loose construction (significant air leakage)")
        
        return "; ".join(notes)
    
    def calculate_infiltration_loads(
        self,
        cfm: float,
        outdoor_temp: float,
        indoor_temp: float,
        outdoor_humidity_ratio: Optional[float] = None,
        indoor_humidity_ratio: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate sensible and latent infiltration loads.
        
        Args:
            cfm: Infiltration rate in CFM
            outdoor_temp: Outdoor temperature (°F)
            indoor_temp: Indoor temperature (°F)
            outdoor_humidity_ratio: Outdoor humidity ratio (lb/lb)
            indoor_humidity_ratio: Indoor humidity ratio (lb/lb)
            
        Returns:
            Dict with sensible, latent, and total loads in BTU/hr
        """
        # Sensible load: Q = 1.08 × CFM × ΔT
        sensible = 1.08 * cfm * abs(outdoor_temp - indoor_temp)
        
        # Latent load (cooling only)
        latent = 0.0
        if outdoor_humidity_ratio and indoor_humidity_ratio and outdoor_temp > indoor_temp:
            # Q = 4840 × CFM × ΔW
            delta_w = outdoor_humidity_ratio - indoor_humidity_ratio
            if delta_w > 0:
                latent = 4840 * cfm * delta_w
        
        return {
            "sensible": sensible,
            "latent": latent,
            "total": sensible + latent
        }


# Singleton instance
infiltration_calculator = InfiltrationCalculator()