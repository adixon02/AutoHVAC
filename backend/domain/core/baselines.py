"""
Independent Baseline Calculation Methods
Provides deterministic alternatives to AI-enhanced calculations for validation
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """Load calculation candidate result"""
    name: Literal["A_ai", "B_code_min", "C_ua_oa", "D_regional"]
    heating_btuh: float
    cooling_btuh: float
    method_details: Dict[str, Any]  # Breakdown of calculation components


class CodeMinBaseline:
    """
    Method B: IECC-based minimum performance floor
    Uses code minimums by climate zone and era for conservative baseline
    """
    
    def __init__(self):
        # IECC code minimums by climate zone
        self.code_minimums = {
            '5B': {
                'wall_r': 20,  # R-20 cavity or R-13+5 continuous
                'roof_r': 49,  # R-49 ceiling
                'floor_r': 30, # R-30 floor
                'window_u': 0.30,
                'window_shgc': 0.40,
                'ach50_max': 5.0  # Maximum allowed
            },
            '4C': {
                'wall_r': 15,
                'roof_r': 38,
                'floor_r': 25,
                'window_u': 0.35,
                'window_shgc': 0.40,
                'ach50_max': 5.0
            },
            '6A': {
                'wall_r': 20,
                'roof_r': 49,
                'floor_r': 30,
                'window_u': 0.27,
                'window_shgc': 0.40,
                'ach50_max': 5.0
            }
        }
        
        # Duct location penalties by house type
        self.duct_penalties = {
            'single_story': {
                'vented_attic': 1.25,  # 25% penalty
                'conditioned_space': 1.0,
                'basement': 1.15,
                'crawlspace': 1.20
            },
            'multi_story': {
                'vented_attic': 1.20,
                'conditioned_space': 1.0,
                'basement': 1.10,
                'crawlspace': 1.15
            }
        }
    
    def calculate(
        self, 
        envelope: Dict[str, Any], 
        climate_data: Dict[str, Any]
    ) -> Candidate:
        """
        Calculate loads using IECC code minimums as conservative baseline.
        
        Args:
            envelope: Building envelope data
            climate_data: Design conditions
            
        Returns:
            Candidate with code-minimum based loads
        """
        
        climate_zone = envelope.get('climate_zone', '5B')
        minimums = self.code_minimums.get(climate_zone, self.code_minimums['5B'])
        
        area_sqft = envelope.get('area_sqft', 2000)
        stories = envelope.get('floor_count', 1)
        
        # Design temperature differences
        indoor_winter = 70
        indoor_summer = 75
        outdoor_winter = climate_data.get('winter_99', 0)
        outdoor_summer = climate_data.get('summer_1', 95)
        
        delta_t_heating = indoor_winter - outdoor_winter
        delta_t_cooling = outdoor_summer - indoor_summer
        
        # Building geometry estimates
        perimeter = 4 * math.sqrt(area_sqft)  # Assume square
        ceiling_height = 9.0  # Standard height
        wall_area = perimeter * ceiling_height * stories
        
        # Window area (18% of wall area - conservative)
        window_area = wall_area * 0.18
        net_wall_area = wall_area - window_area
        
        # Envelope loads using code minimums
        wall_u = 1.0 / minimums['wall_r']
        window_u = minimums['window_u']
        ceiling_u = 1.0 / minimums['roof_r']
        floor_u = 1.0 / minimums['floor_r']
        
        # Heating envelope loads
        wall_heating = net_wall_area * wall_u * delta_t_heating
        window_heating = window_area * window_u * delta_t_heating
        ceiling_heating = area_sqft * ceiling_u * delta_t_heating
        
        # Floor heating (varies by foundation)
        foundation_type = envelope.get('foundation_type', 'crawlspace')
        if 'slab' in foundation_type.lower():
            floor_heating = perimeter * 2.0 * delta_t_heating * 0.5  # Edge losses only
        else:
            floor_heating = area_sqft * floor_u * delta_t_heating * 0.7  # Reduced delta-T
        
        envelope_heating = wall_heating + window_heating + ceiling_heating + floor_heating
        
        # Infiltration heating
        ach50 = minimums['ach50_max']  # Use code maximum (worst case)
        ach_natural = ach50 / 20  # Conservative conversion
        volume_cuft = area_sqft * ceiling_height * stories
        infiltration_cfm = (ach_natural * volume_cuft) / 60
        infiltration_heating = 1.08 * infiltration_cfm * delta_t_heating
        
        # Duct penalties
        house_type = 'single_story' if stories == 1 else 'multi_story'
        duct_location = self._determine_worst_duct_location(envelope, house_type)
        duct_penalty = self.duct_penalties[house_type][duct_location]
        
        # Total heating load
        base_heating = envelope_heating + infiltration_heating
        total_heating = base_heating * duct_penalty
        
        # Cooling loads (simplified)
        # Envelope (use CLTD method approximation)
        envelope_cooling = envelope_heating * 0.15  # Simplified ratio
        
        # Solar gains
        window_shgc = minimums['window_shgc']
        solar_cooling = window_area * window_shgc * 200  # Conservative solar factor
        
        # Internal gains
        people_cooling = area_sqft * 2.0  # 2 BTU/hr·sqft
        equipment_cooling = area_sqft * 1.0  # 1 W/sqft = 3.412 BTU/hr·sqft
        lighting_cooling = area_sqft * 1.0
        
        internal_cooling = people_cooling + equipment_cooling + lighting_cooling
        
        # Infiltration cooling  
        infiltration_cooling = 1.08 * infiltration_cfm * delta_t_cooling
        
        total_cooling = envelope_cooling + solar_cooling + internal_cooling + infiltration_cooling
        
        # Method details for transparency
        details = {
            'climate_zone': climate_zone,
            'code_minimums_used': minimums,
            'duct_location': duct_location,
            'duct_penalty': duct_penalty,
            'envelope_heating': envelope_heating,
            'infiltration_heating': infiltration_heating,
            'infiltration_cfm': infiltration_cfm,
            'heating_components': {
                'walls': wall_heating,
                'windows': window_heating, 
                'ceiling': ceiling_heating,
                'floor': floor_heating
            },
            'cooling_components': {
                'envelope': envelope_cooling,
                'solar': solar_cooling,
                'internal': internal_cooling,
                'infiltration': infiltration_cooling
            }
        }
        
        logger.info(f"Code-min baseline: {total_heating:.0f} heating, {total_cooling:.0f} cooling BTU/hr")
        
        return Candidate(
            name="B_code_min",
            heating_btuh=total_heating,
            cooling_btuh=total_cooling,
            method_details=details
        )
    
    def _determine_worst_duct_location(self, envelope: Dict, house_type: str) -> str:
        """Determine worst plausible duct location for conservative estimate"""
        
        actual_location = envelope.get('duct_location', '').lower()
        
        if actual_location and 'conditioned' in actual_location:
            return 'conditioned_space'
        
        # Default to worst case by house type
        if house_type == 'single_story':
            return 'vented_attic'  # Worst for single story
        else:
            return 'crawlspace'  # Worst for multi-story


class UAOABaseline:
    """
    Method C: Deterministic UA + OA calculation
    Pure heat loss coefficient calculation with no AI influence
    """
    
    def calculate(
        self, 
        envelope: Dict[str, Any], 
        climate_data: Dict[str, Any]
    ) -> Candidate:
        """
        Calculate loads using deterministic UA + outdoor air method.
        
        Args:
            envelope: Building envelope data
            climate_data: Design conditions
            
        Returns:
            Candidate with UA+OA based loads
        """
        
        area_sqft = envelope.get('area_sqft', 2000)
        stories = envelope.get('floor_count', 1)
        
        # Design temperature differences
        indoor_winter = 70
        indoor_summer = 75
        outdoor_winter = climate_data.get('winter_99', 0)
        outdoor_summer = climate_data.get('summer_1', 95)
        
        delta_t_heating = indoor_winter - outdoor_winter
        delta_t_cooling = outdoor_summer - indoor_summer
        
        # Calculate building surface areas
        perimeter = 4 * math.sqrt(area_sqft)
        ceiling_height = 9.0
        
        # Surface areas
        wall_area = perimeter * ceiling_height * stories
        roof_area = area_sqft
        floor_area = area_sqft
        window_area = wall_area * 0.18  # 18% WWR
        net_wall_area = wall_area - window_area
        
        # Conservative U-values (realistic construction)
        wall_u = 1.0 / 20.0  # R-20 effective
        window_u = 0.30
        roof_u = 1.0 / 38.0  # R-38 effective with bridging
        floor_u = 1.0 / 25.0  # R-25 effective
        
        # Calculate UA (heat loss coefficient)
        ua_walls = net_wall_area * wall_u
        ua_windows = window_area * window_u
        ua_roof = roof_area * roof_u
        ua_floor = floor_area * floor_u * 0.7  # Ground coupling reduction
        
        total_ua = ua_walls + ua_windows + ua_roof + ua_floor
        
        # Heating load = UA × ΔT
        envelope_heating = total_ua * delta_t_heating
        
        # Outdoor air load using AIM-2 with conservative assumptions
        ach50 = envelope.get('ach50', 5.0)  # Conservative value
        ach_natural = self._calculate_ach_natural_conservative(ach50, stories)
        
        volume_cuft = area_sqft * ceiling_height * stories
        oa_cfm = (ach_natural * volume_cuft) / 60
        oa_heating = 1.08 * oa_cfm * delta_t_heating
        
        total_heating = envelope_heating + oa_heating
        
        # Cooling calculation (simplified but deterministic)
        envelope_cooling = total_ua * delta_t_cooling * 0.7  # Thermal mass effect
        
        # Solar gains (deterministic)
        solar_cooling = window_area * 0.30 * 200  # SHGC × Solar factor
        
        # Internal gains (deterministic)
        internal_cooling = area_sqft * 4.0  # 4 BTU/hr·sqft total internal
        
        # OA cooling
        oa_cooling = 1.08 * oa_cfm * delta_t_cooling
        
        total_cooling = envelope_cooling + solar_cooling + internal_cooling + oa_cooling
        
        # Method details
        details = {
            'total_ua': total_ua,
            'ua_breakdown': {
                'walls': ua_walls,
                'windows': ua_windows,
                'roof': ua_roof,
                'floor': ua_floor
            },
            'oa_cfm': oa_cfm,
            'ach_natural': ach_natural,
            'heating_components': {
                'envelope': envelope_heating,
                'outdoor_air': oa_heating
            },
            'cooling_components': {
                'envelope': envelope_cooling,
                'solar': solar_cooling,
                'internal': internal_cooling,
                'outdoor_air': oa_cooling
            }
        }
        
        logger.info(f"UA+OA baseline: {total_heating:.0f} heating, {total_cooling:.0f} cooling BTU/hr")
        
        return Candidate(
            name="C_ua_oa",
            heating_btuh=total_heating,
            cooling_btuh=total_cooling,
            method_details=details
        )
    
    def _calculate_ach_natural_conservative(self, ach50: float, stories: int) -> float:
        """Calculate natural ACH using conservative assumptions"""
        
        # Conservative conversion with wind exposure
        wind_factor = 1.2 if stories == 1 else 1.0  # Single story more exposed
        ach_natural = (ach50 / 20) * wind_factor
        
        # Floor of 0.3 for reasonable building
        return max(0.3, ach_natural)


class RegionalBaseline:
    """
    Method D: Regional intensity heuristics
    Uses BTU/hr·sqft bands by climate and building characteristics
    """
    
    def __init__(self):
        # Regional intensity bands (BTU/hr·sqft) by climate zone and configuration
        self.intensity_bands = {
            '5B': {
                'single_story_attic_ducts': {'heating': (18, 30), 'cooling': (12, 18)},
                'single_story_basement_ducts': {'heating': (15, 25), 'cooling': (12, 18)},
                'multi_story_attic_ducts': {'heating': (16, 26), 'cooling': (12, 18)},
                'multi_story_basement_ducts': {'heating': (14, 22), 'cooling': (12, 18)},
            },
            '4C': {
                'single_story_attic_ducts': {'heating': (15, 25), 'cooling': (10, 16)},
                'single_story_basement_ducts': {'heating': (12, 20), 'cooling': (10, 16)},
                'multi_story_attic_ducts': {'heating': (13, 22), 'cooling': (10, 16)},
                'multi_story_basement_ducts': {'heating': (11, 18), 'cooling': (10, 16)},
            },
            '6A': {
                'single_story_attic_ducts': {'heating': (20, 35), 'cooling': (12, 18)},
                'single_story_basement_ducts': {'heating': (17, 28), 'cooling': (12, 18)},
                'multi_story_attic_ducts': {'heating': (18, 30), 'cooling': (12, 18)},
                'multi_story_basement_ducts': {'heating': (15, 25), 'cooling': (12, 18)},
            }
        }
    
    def calculate(
        self, 
        envelope: Dict[str, Any], 
        climate_data: Dict[str, Any]
    ) -> Candidate:
        """
        Calculate loads using regional intensity bands.
        
        Args:
            envelope: Building envelope data
            climate_data: Design conditions
            
        Returns:
            Candidate with regional intensity based loads
        """
        
        climate_zone = envelope.get('climate_zone', '5B')
        area_sqft = envelope.get('area_sqft', 2000)
        stories = envelope.get('floor_count', 1)
        
        # Determine configuration
        house_type = 'single_story' if stories == 1 else 'multi_story'
        duct_location = envelope.get('duct_location', 'vented_attic')
        
        if 'attic' in duct_location.lower():
            duct_type = 'attic_ducts'
        else:
            duct_type = 'basement_ducts'
        
        config_key = f"{house_type}_{duct_type}"
        
        # Get intensity bands
        bands = self.intensity_bands.get(climate_zone, self.intensity_bands['5B'])
        intensity_range = bands.get(config_key, bands['single_story_attic_ducts'])
        
        # Use midpoint of range for conservative estimate
        heating_intensity = sum(intensity_range['heating']) / 2
        cooling_intensity = sum(intensity_range['cooling']) / 2
        
        # Calculate loads
        heating_btuh = heating_intensity * area_sqft
        cooling_btuh = cooling_intensity * area_sqft
        
        # Method details
        details = {
            'climate_zone': climate_zone,
            'configuration': config_key,
            'intensity_range': intensity_range,
            'used_intensity': {
                'heating': heating_intensity,
                'cooling': cooling_intensity
            }
        }
        
        logger.info(f"Regional baseline: {heating_btuh:.0f} heating, {cooling_btuh:.0f} cooling BTU/hr")
        
        return Candidate(
            name="D_regional",
            heating_btuh=heating_btuh,
            cooling_btuh=cooling_btuh,
            method_details=details
        )


# Singleton instances
_code_min_baseline = None
_ua_oa_baseline = None  
_regional_baseline = None

def get_code_min_baseline() -> CodeMinBaseline:
    """Get or create the global code-min baseline calculator"""
    global _code_min_baseline
    if _code_min_baseline is None:
        _code_min_baseline = CodeMinBaseline()
    return _code_min_baseline

def get_ua_oa_baseline() -> UAOABaseline:
    """Get or create the global UA+OA baseline calculator"""
    global _ua_oa_baseline
    if _ua_oa_baseline is None:
        _ua_oa_baseline = UAOABaseline()
    return _ua_oa_baseline

def get_regional_baseline() -> RegionalBaseline:
    """Get or create the global regional baseline calculator"""
    global _regional_baseline
    if _regional_baseline is None:
        _regional_baseline = RegionalBaseline()
    return _regional_baseline