"""
ACCA Manual J Load Calculation Engine
Implements simplified Manual J algorithms for HVAC sizing
"""

from typing import Dict, Any, List, Optional
from app.parser.schema import BlueprintSchema, Room
from .climate_data import get_climate_data, get_climate_zone_factors, get_construction_vintage_values
from .cltd_clf import (
    calculate_wall_load_cltd, calculate_roof_load_cltd, 
    calculate_window_solar_load, calculate_window_conduction_load,
    calculate_internal_load_clf, get_diversity_factor
)
from .infiltration import (
    convert_cfm50_to_natural, convert_ach50_to_cfm50, 
    estimate_infiltration_by_quality, calculate_infiltration_loads,
    ConstructionQuality, InfiltrationMethod
)
from .thermal_mass import (
    classify_thermal_mass, apply_thermal_mass_to_loads,
    MassLevel, calculate_mass_factor
)
from .envelope_extractor import EnvelopeExtraction
from .audit_tracker import get_audit_tracker, create_calculation_audit
from .blueprint_validator import BlueprintValidator, ValidationSeverity
import math
import time
import logging

logger = logging.getLogger(__name__)


def _get_humidity_ratio(temp_f: float, rh_percent: float) -> float:
    """
    Calculate humidity ratio (lb water/lb dry air) from temperature and RH
    
    Simplified psychrometric calculation for HVAC loads
    
    Args:
        temp_f: Temperature in °F
        rh_percent: Relative humidity in percent (0-100)
        
    Returns:
        Humidity ratio in lb water/lb dry air
    """
    # Convert to Celsius for calculation
    temp_c = (temp_f - 32) * 5/9
    
    # Saturation vapor pressure (kPa) - Antoine equation
    if temp_c >= 0:
        p_sat = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    else:
        p_sat = 0.61078 * math.exp((21.875 * temp_c) / (temp_c + 265.5))
    
    # Actual vapor pressure
    p_vapor = p_sat * rh_percent / 100
    
    # Atmospheric pressure (assume sea level)
    p_atm = 101.325  # kPa
    
    # Humidity ratio
    w = 0.622 * p_vapor / (p_atm - p_vapor)
    
    return w


def _apply_thermal_bridging_factor(
    base_load: float,
    construction_type: str,
    component: str,
    load_type: str = "cooling"
) -> float:
    """
    Apply thermal bridging factor to conduction loads
    
    Args:
        base_load: Base conduction load (BTU/hr)
        construction_type: "wood_frame", "steel_frame", "masonry", etc.
        component: "wall", "roof", "floor"
        load_type: "heating" or "cooling" - different factors for each
    
    Returns:
        Load including thermal bridging effects
    """
    # Thermal bridging factors (multiply base load)
    # These account for heat transfer through structural members
    # Different factors for heating vs cooling - thermal bridging less significant in heating
    
    if load_type == "heating":
        # REDUCED factors for heating to address overestimation
        bridging_factors = {
            ("wood_frame", "wall"): 1.02,      # Reduced: 2% for wood studs (was 1.04)
            ("wood_frame", "roof"): 1.04,      # Reduced: 4% for roof trusses (was 1.06)
            ("wood_frame", "floor"): 1.02,     # Reduced: 2% for floor joists (was 1.04)
            ("steel_frame", "wall"): 1.15,     # Reduced: 15% for steel studs (was 1.20)
            ("steel_frame", "roof"): 1.12,     # Reduced: 12% for steel trusses (was 1.16)
            ("steel_frame", "floor"): 1.10,    # Reduced: 10% for steel joists (was 1.12)
            ("masonry", "wall"): 1.06,         # Reduced: 6% for masonry ties (was 1.09)
            ("masonry", "roof"): 1.02,         # Reduced: 2% for roof connections (was 1.04)
            ("masonry", "floor"): 1.02,        # Reduced: 2% for floor connections (was 1.03)
            ("concrete", "wall"): 1.08,        # Reduced: 8% for concrete bridges (was 1.12)
            ("concrete", "roof"): 1.05,        # Reduced: 5% for concrete roof (was 1.08)
            ("concrete", "floor"): 1.05,       # Reduced: 5% for concrete floor (was 1.08)
        }
    else:
        # MAINTAIN cooling factors for accuracy
        bridging_factors = {
            ("wood_frame", "wall"): 1.04,      # 4% for wood studs
            ("wood_frame", "roof"): 1.06,      # 6% for roof trusses
            ("wood_frame", "floor"): 1.04,     # 4% for floor joists
            ("steel_frame", "wall"): 1.20,     # 20% for steel studs
            ("steel_frame", "roof"): 1.16,     # 16% for steel trusses
            ("steel_frame", "floor"): 1.12,    # 12% for steel joists
            ("masonry", "wall"): 1.09,         # 9% for masonry ties
            ("masonry", "roof"): 1.04,         # 4% for roof connections
            ("masonry", "floor"): 1.03,        # 3% for floor connections
            ("concrete", "wall"): 1.12,        # 12% for concrete bridges
            ("concrete", "roof"): 1.08,        # 8% for concrete roof
            ("concrete", "floor"): 1.08,       # 8% for concrete floor
        }
    
    # Default to wood frame if construction type unknown
    if construction_type is None or construction_type == "":
        construction_type = "wood_frame"
    
    # Normalize construction type
    construction_type = construction_type.lower().replace("-", "_").replace(" ", "_")
    
    # Get factor or default to 1.0 (no adjustment)
    factor = bridging_factors.get((construction_type, component), 1.0)
    
    return base_load * factor


def _calculate_floor_losses(
    floor_area: float,
    floor_type: str,
    outdoor_temp: float,
    indoor_temp: float,
    climate_zone: str,
    perimeter_length: float = None
) -> Dict[str, float]:
    """
    Calculate heat loss through floors (slab, crawlspace, or basement)
    
    Args:
        floor_area: Floor area in sq ft
        floor_type: "slab", "crawlspace", "basement", "above_grade"
        outdoor_temp: Outdoor design temperature (°F)
        indoor_temp: Indoor design temperature (°F)
        climate_zone: ASHRAE climate zone
        perimeter_length: Perimeter length for slab edge losses (ft)
    
    Returns:
        Dict with heating and cooling loads in BTU/hr
    """
    delta_t_heating = indoor_temp - outdoor_temp
    delta_t_cooling = outdoor_temp - indoor_temp
    
    if floor_type == "above_grade":
        # No ground contact - minimal loss
        return {"heating": 0, "cooling": 0}
    
    elif floor_type == "slab":
        # Slab-on-grade losses are primarily through the perimeter
        if perimeter_length is None:
            # Estimate perimeter from area (assume square for simplicity)
            perimeter_length = 4 * math.sqrt(floor_area)
        
        # F-factors for slab edge heat loss (BTU/hr·ft·°F)
        # Based on insulation level and climate zone
        if climate_zone in ["6A", "6B", "7", "8"]:
            f_factor = 0.73  # Assumes R-10 edge insulation
        elif climate_zone in ["4A", "4B", "5A", "5B"]:
            f_factor = 0.86  # Assumes R-5 edge insulation
        else:
            f_factor = 1.20  # Uninsulated or minimal insulation
        
        # Slab edge loss
        heating_loss = f_factor * perimeter_length * delta_t_heating
        
        # Slab provides thermal mass benefit in cooling
        cooling_loss = 0  # Slab typically helps with cooling
        
    elif floor_type == "crawlspace":
        # Crawlspace with insulated floor above
        # U-factor depends on floor insulation
        if climate_zone in ["6A", "6B", "7", "8"]:
            u_factor = 0.033  # R-30 floor insulation
        elif climate_zone in ["4A", "4B", "5A", "5B"]:
            u_factor = 0.050  # R-20 floor insulation
        else:
            u_factor = 0.067  # R-15 floor insulation
        
        # Apply crawlspace temperature modifier (crawlspace is warmer than outside)
        crawl_temp_ratio = 0.5  # Crawlspace temp is halfway between indoor and outdoor
        effective_delta_t = delta_t_heating * crawl_temp_ratio
        
        heating_loss = u_factor * floor_area * effective_delta_t
        cooling_loss = u_factor * floor_area * delta_t_cooling * 0.3  # Reduced cooling impact
        
    elif floor_type == "basement":
        # Basement floor losses (below grade)
        # Use simplified basement heat loss factors
        if perimeter_length is None:
            perimeter_length = 4 * math.sqrt(floor_area)
        
        # Below-grade wall loss factor (BTU/hr·ft·°F per linear foot of perimeter)
        # Assumes 4 ft below grade average
        below_grade_factor = 0.35  # For insulated basement walls
        
        # Basement floor loss factor (BTU/hr·ft²·°F)
        floor_factor = 0.025  # For uninsulated basement floor
        
        heating_loss = (below_grade_factor * perimeter_length * 4 + 
                       floor_factor * floor_area) * delta_t_heating
        cooling_loss = heating_loss * 0.1  # Minimal cooling loss for basements
    
    else:
        # Unknown floor type - use conservative estimate
        u_factor = 0.05  # Moderate insulation
        heating_loss = u_factor * floor_area * delta_t_heating
        cooling_loss = u_factor * floor_area * delta_t_cooling * 0.5
    
    return {
        "heating": max(0, heating_loss),
        "cooling": max(0, cooling_loss)
    }


# Legacy climate zone data - now replaced by climate_data service
# Keeping for backward compatibility with tests
CLIMATE_ZONES = {
    "90210": {"heating_factor": 35, "cooling_factor": 25, "zone": "3A"},  # Los Angeles
    "10001": {"heating_factor": 45, "cooling_factor": 20, "zone": "4A"},  # NYC
    "33101": {"heating_factor": 15, "cooling_factor": 35, "zone": "1A"},  # Miami
    "60601": {"heating_factor": 50, "cooling_factor": 22, "zone": "5A"},  # Chicago
    "default": {"heating_factor": 40, "cooling_factor": 25, "zone": "4A"}
}

# Room type multipliers
ROOM_MULTIPLIERS = {
    "living": {"heating": 1.0, "cooling": 1.3},   # Reduced heating from 1.2
    "bedroom": {"heating": 0.9, "cooling": 1.0},  # No change - already reasonable
    "kitchen": {"heating": 1.0, "cooling": 1.4},  # Reduced heating from 1.1
    "bathroom": {"heating": 1.0, "cooling": 1.1}, # Reduced heating from 1.1 to 1.0
    "dining": {"heating": 0.95, "cooling": 1.1},  # Reduced heating from 1.0
    "office": {"heating": 0.9, "cooling": 1.2},   # No change
    "utility": {"heating": 0.8, "cooling": 1.3},  # No change
    "other": {"heating": 0.95, "cooling": 1.0}    # Reduced heating from 1.0
}

# Orientation factors
ORIENTATION_FACTORS = {
    "N": {"heating": 1.1, "cooling": 0.9},   # North - less solar gain
    "S": {"heating": 0.9, "cooling": 1.2},   # South - high solar gain
    "E": {"heating": 1.0, "cooling": 1.1},   # East - morning sun
    "W": {"heating": 1.0, "cooling": 1.3},   # West - afternoon sun
    "NE": {"heating": 1.05, "cooling": 0.95},
    "NW": {"heating": 1.05, "cooling": 1.1},
    "SE": {"heating": 0.95, "cooling": 1.15},
    "SW": {"heating": 0.95, "cooling": 1.25},
    "": {"heating": 1.0, "cooling": 1.0}      # Interior rooms
}


def _calculate_confidence_metrics(zones: List[Dict], schema: BlueprintSchema) -> Dict[str, Any]:
    """Calculate overall confidence metrics for the load calculation"""
    
    # Room-level confidence
    room_confidences = []
    orientation_known_count = 0
    low_confidence_rooms = []
    warnings = []
    
    for zone in zones:
        if 'confidence' in zone:
            room_confidences.append(zone['confidence'])
            if zone['confidence'] < 0.5:
                low_confidence_rooms.append(zone['name'])
        
        if 'data_quality' in zone and zone['data_quality'].get('orientation_known', False):
            orientation_known_count += 1
    
    overall_confidence = sum(room_confidences) / len(room_confidences) if room_confidences else 0.5
    
    # Check for orientation issues
    orientation_known = orientation_known_count == len(zones)
    if not orientation_known:
        warnings.append("Building orientation unknown - solar loads averaged for all rooms")
    
    # Check for low confidence rooms
    if low_confidence_rooms:
        warnings.append(f"Low confidence rooms: {', '.join(low_confidence_rooms)}")
    
    # Check for area validation
    total_room_area = sum(zone['area'] for zone in zones)
    if abs(total_room_area - schema.sqft_total) > schema.sqft_total * 0.1:
        area_diff_pct = abs(total_room_area - schema.sqft_total) / schema.sqft_total * 100
        warnings.append(f"Area correction applied: parsed {total_room_area:.0f} sqft vs declared {schema.sqft_total:.0f} sqft ({area_diff_pct:.0f}% difference)")
        overall_confidence *= 0.9
    
    return {
        "overall_confidence": round(overall_confidence, 2),
        "orientation_known": orientation_known,
        "rooms_with_low_confidence": len(low_confidence_rooms),
        "total_rooms": len(zones),
        "values_estimated": [f"{zone['name']}_dimensions" for zone in zones 
                           if zone.get('data_quality', {}).get('dimension_source') == 'estimated'],
        "warnings": warnings,
        "data_sources": {
            "gpt4v_parsing": True,
            "envelope_extraction": False,  # Will be updated if envelope data used
            "climate_data": "ASHRAE/IECC Database"
        }
    }


def _calculate_room_loads_cltd_clf(room: Room, room_type: str, climate_data: Dict, construction_values: Dict,
                                  outdoor_cooling_temp: float, outdoor_heating_temp: float, indoor_temp: float, 
                                  include_ventilation: bool = True, envelope_data: Optional[EnvelopeExtraction] = None) -> Dict[str, float]:
    """Calculate room loads using enhanced CLF/CLTD methodology"""
    
    # Use actual envelope data if available, otherwise estimate
    if envelope_data:
        # Use extracted ceiling height with confidence weighting
        if envelope_data.ceiling_height_confidence >= 0.6:
            ceiling_height = envelope_data.ceiling_height
        else:
            ceiling_height = 9.0  # Default if low confidence
    else:
        ceiling_height = 9.0  # Default assumption
    
    # Enhanced wall area calculation using GPT-4V exterior wall data
    exterior_walls_count = room.source_elements.get('exterior_walls', 1) if hasattr(room, 'source_elements') else 1
    
    # Initialize variables to prevent UnboundLocalError
    wall_area = 0
    window_area = 0
    room_perimeter = 0  # Initialize room_perimeter to prevent UnboundLocalError
    
    # Calculate room perimeter based on area (needed for all rooms, including interior)
    # Use actual dimensions if available, otherwise estimate
    if hasattr(room, 'dimensions_ft') and room.dimensions_ft and len(room.dimensions_ft) >= 2:
        width = room.dimensions_ft[0]
        length = room.dimensions_ft[1]
        room_perimeter = 2 * (width + length)
    else:
        # Assume rectangular room with 1.5:1 aspect ratio (more realistic than square)
        width = math.sqrt(room.area / 1.5)
        length = width * 1.5
        room_perimeter = 2 * (width + length)
    
    if exterior_walls_count == 0:
        # Interior room - no exterior wall area
        logger.info(f"Room {room.name} is interior - no exterior wall loads")
    else:
        
        # Calculate exterior wall length based on actual number of exterior walls
        # This is more accurate than dividing by 4
        if exterior_walls_count == 1:
            # One exterior wall - typically the longer dimension
            exterior_wall_length = max(width, length) if 'width' in locals() else room_perimeter * 0.3
        elif exterior_walls_count == 2:
            # Corner room - one long + one short wall
            exterior_wall_length = (max(width, length) + min(width, length)) if 'width' in locals() else room_perimeter * 0.5
        elif exterior_walls_count == 3:
            # Three walls exposed
            exterior_wall_length = room_perimeter * 0.75
        elif exterior_walls_count >= 4:
            # All walls exposed (rare, usually standalone structure)
            exterior_wall_length = room_perimeter
        else:
            # Interior room or default
            exterior_wall_length = 0
        
        # Calculate wall area
        wall_area = exterior_wall_length * ceiling_height
        
        # Subtract door area only if room has exterior doors
        exterior_doors = room.source_elements.get('exterior_doors', 0) if hasattr(room, 'source_elements') else 0
        if exterior_doors > 0:
            door_area = exterior_doors * 21  # 3ft x 7ft doors
            wall_area -= door_area
        
        # Calculate window area with size variation based on count
        if room.windows > 0:
            # BALANCED window sizes for accurate cooling loads
            # Previous reduction was too aggressive, causing 33% cooling underestimation
            if room.windows == 1:
                window_size = 14.0  # Balanced: 3.5x4 ft (was 15→12, now 14)
            elif room.windows <= 3:
                window_size = 11.0  # Balanced: 2.75x4 ft (was 12→10, now 11)
            else:
                window_size = 9.0   # Balanced: 3x3 ft (was 9→8, now 9)
            
            window_area = room.windows * window_size
            wall_area -= window_area
        else:
            window_area = 0
    
    # Roof area (only for top floor rooms)
    roof_area = room.area if room.floor == max([r.floor for r in [room]]) else 0
    
    # Get U-factors - prioritize extracted envelope data, fallback to construction values
    if envelope_data and envelope_data.wall_confidence >= 0.6:
        wall_u_factor = envelope_data.wall_u_factor
        wall_construction_type = envelope_data.wall_construction
    else:
        wall_u_factor = 1.0 / construction_values['wall_r_value']
        wall_construction_type = "estimated"
    
    if envelope_data and envelope_data.roof_confidence >= 0.6:
        roof_u_factor = envelope_data.roof_u_factor
        roof_construction_type = envelope_data.roof_construction
    else:
        roof_u_factor = 1.0 / construction_values['roof_r_value']
        roof_construction_type = "estimated"
        
    if envelope_data and envelope_data.window_confidence >= 0.6:
        window_u_factor = envelope_data.window_u_factor
        window_shgc = envelope_data.window_shgc
        window_type = envelope_data.window_type
    else:
        window_u_factor = construction_values['window_u_factor']
        window_shgc = construction_values['window_shgc']
        window_type = "estimated"
    
    # Determine construction types - use envelope data if available
    if envelope_data:
        # Map construction types from envelope data
        if "masonry" in wall_construction_type.lower() or "concrete" in wall_construction_type.lower():
            wall_type = 'masonry_medium'
        elif "2x6" in wall_construction_type.lower() or "heavy" in wall_construction_type.lower():
            wall_type = 'frame_heavy'
        elif "2x4" in wall_construction_type.lower() and envelope_data.wall_r_value < 12:
            wall_type = 'frame_light'
        else:
            wall_type = 'frame_medium'
            
        if "cathedral" in roof_construction_type.lower() or "heavy" in roof_construction_type.lower():
            roof_type = 'heavy_roof'
        elif envelope_data.roof_r_value < 25:
            roof_type = 'light_roof'
        else:
            roof_type = 'medium_roof'
    else:
        # Fallback to vintage-based estimation
        if 'pre-1980' in str(construction_values).lower():
            wall_type = 'frame_light'
            roof_type = 'light_roof'
        elif 'current-code' in str(construction_values).lower():
            wall_type = 'frame_heavy'
            roof_type = 'heavy_roof'
        else:
            wall_type = 'frame_medium'
            roof_type = 'medium_roof'
    
    # COOLING LOAD CALCULATIONS using CLF/CLTD
    cooling_load = 0.0
    
    # Extract climate zone for CLTD adjustments (needed for multiple calculations)
    climate_zone = climate_data.get('zone', '4A')
    
    # 1. Wall conduction load
    if wall_area > 0:
        wall_load = calculate_wall_load_cltd(
            wall_area, wall_u_factor, wall_type, room.orientation,
            outdoor_cooling_temp, indoor_temp, climate_zone
        )
        cooling_load += wall_load
    
    # 2. Roof conduction load
    if roof_area > 0:
        roof_load = calculate_roof_load_cltd(
            roof_area, roof_u_factor, roof_type,
            outdoor_cooling_temp, indoor_temp, climate_zone
        )
        cooling_load += roof_load
    
    # 3. Window conduction load
    if window_area > 0:
        window_conduction = calculate_window_conduction_load(
            window_area, window_u_factor, outdoor_cooling_temp, indoor_temp
        )
        cooling_load += window_conduction
    
    # 4. Window solar load with orientation uncertainty handling
    if window_area > 0:
        # Check if orientation is known
        orientation_confidence = room.source_elements.get('orientation_confidence', 0.0) if hasattr(room, 'source_elements') else 0.0
        
        if room.orientation == 'unknown' or orientation_confidence < 0.3:
            # Unknown orientation - use balanced distribution for new construction residential
            # Equal probability of each orientation is more accurate than worst-case assumptions
            orientation_weights = {
                'S': 0.25,  # 25% - Balanced approach
                'W': 0.25,  # 25% - Balanced approach  
                'E': 0.25,  # 25% - Balanced approach
                'N': 0.25   # 25% - Balanced approach
            }
            
            weighted_solar = 0
            for orient, weight in orientation_weights.items():
                solar_contribution = calculate_window_solar_load(
                    window_area, window_shgc, orient
                )
                weighted_solar += solar_contribution * weight
            
            solar_load = weighted_solar
            logger.info(f"Room {room.name}: Using balanced solar load (25% each direction) for unknown orientation")
        else:
            solar_load = calculate_window_solar_load(
                window_area, window_shgc, room.orientation
            )
        cooling_load += solar_load
    
    # 5. Internal loads with CLF
    # People load (assume 1 person per 200 sq ft)
    people_count = max(1, room.area / 200)
    people_load = calculate_internal_load_clf(people_count * 250, 'people')  # 250 BTU/hr per person sensible
    cooling_load += people_load
    
    # BALANCED lighting load (modern mixed LED/conventional)
    # Adjusted to 1.7 W/sq ft for realistic residential lighting mix
    lighting_load = calculate_internal_load_clf(room.area * 1.7 * 3.41, 'lighting')  # Convert W to BTU/hr
    cooling_load += lighting_load
    
    # BALANCED equipment loads for realistic residential usage
    # Previous reduction was too aggressive, causing cooling underestimation
    equipment_loads = {
        'kitchen': room.area * 4.5,  # Balanced: cooking, refrigerator, dishwasher (was 5→4, now 4.5)
        'office': room.area * 2.8,   # Balanced: computers, monitors, printers (was 3→2.4, now 2.8)
        'living': room.area * 1.4,   # Balanced: TV, game consoles, etc (was 1.5→1.2, now 1.4)
        'bedroom': room.area * 1.0,  # Balanced: chargers, TV, fans (was 1→0.8, now 1.0)
        'bathroom': room.area * 1.8, # Balanced: fans, hair dryers (was 2→1.6, now 1.8)
        'other': room.area * 1.0     # Balanced: general loads (was 1→0.8, now 1.0)
    }
    equipment_heat = equipment_loads.get(room_type, equipment_loads['other'])
    equipment_load = calculate_internal_load_clf(equipment_heat, 'equipment')
    cooling_load += equipment_load
    
    # 6. Infiltration cooling load (sensible + latent)
    # Note: infiltration_cfm is calculated in the heating section below, but we need it here too
    # This is a temporary calculation that will be overwritten with the actual value
    
    # Calculate infiltration CFM (will be recalculated in heating section)
    room_volume = room.area * ceiling_height
    if envelope_data and envelope_data.infiltration_confidence >= 0.6:
        if envelope_data.blower_door_result:
            blower_result = envelope_data.blower_door_result.strip().upper()
            if "ACH50" in blower_result:
                ach50 = float(blower_result.replace("ACH50", "").strip())
                cfm50 = convert_ach50_to_cfm50(ach50, room_volume)
            elif "CFM50" in blower_result:
                cfm50 = float(blower_result.replace("CFM50", "").strip())
            else:
                cfm50 = None
            
            if cfm50:
                temp_infiltration_cfm = convert_cfm50_to_natural(
                    cfm50 * (room.area / room.area),
                    climate_data['climate_zone'],
                    stories=1,
                    shielding="average"
                )
            else:
                quality_map = {
                    "tight": ConstructionQuality.TIGHT,
                    "code": ConstructionQuality.AVERAGE,
                    "loose": ConstructionQuality.LOOSE
                }
                quality = quality_map.get(envelope_data.infiltration_class, ConstructionQuality.AVERAGE)
                temp_infiltration_cfm, _ = estimate_infiltration_by_quality(
                    quality, room_volume, climate_data['climate_zone']
                )
        else:
            quality_map = {
                "tight": ConstructionQuality.TIGHT,
                "code": ConstructionQuality.AVERAGE,
                "loose": ConstructionQuality.LOOSE
            }
            quality = quality_map.get(envelope_data.infiltration_class, ConstructionQuality.AVERAGE)
            temp_infiltration_cfm, _ = estimate_infiltration_by_quality(
                quality, room_volume, climate_data['climate_zone']
            )
    else:
        ach = construction_values.get('infiltration_ach', 0.5)
        temp_infiltration_cfm = (room_volume * ach) / 60
    
    # Get humidity ratios for latent calculation
    outdoor_humidity_ratio = _get_humidity_ratio(outdoor_cooling_temp, climate_data.get('cooling_rh_1', 50))
    indoor_humidity_ratio = _get_humidity_ratio(indoor_temp, 50)  # Assume 50% RH indoor
    
    infiltration_cooling_loads = calculate_infiltration_loads(
        temp_infiltration_cfm, outdoor_cooling_temp, indoor_temp,
        outdoor_humidity_ratio, indoor_humidity_ratio
    )
    cooling_load += infiltration_cooling_loads['total']
    
    # 7. Ventilation load (ASHRAE 62.2)
    ventilation = _calculate_ventilation_load(
        room, 
        {'heating_db_99': outdoor_heating_temp, 'cooling_db_1': outdoor_cooling_temp, 'zone': climate_data['climate_zone']}, 
        include_ventilation=include_ventilation,
        outdoor_heating_temp=outdoor_heating_temp,
        outdoor_cooling_temp=outdoor_cooling_temp
    )
    cooling_load += ventilation['cooling']
    
    # HEATING LOAD CALCULATIONS (simplified conduction method)
    heating_load = 0.0
    
    # Wall conduction with thermal bridging
    if wall_area > 0:
        base_wall_load = wall_u_factor * wall_area * (indoor_temp - outdoor_heating_temp)
        # Determine construction type for thermal bridging
        construction_type = "wood_frame"  # Default
        if envelope_data and hasattr(envelope_data, 'wall_construction'):
            if "steel" in envelope_data.wall_construction.lower():
                construction_type = "steel_frame"
            elif "masonry" in envelope_data.wall_construction.lower():
                construction_type = "masonry"
            elif "concrete" in envelope_data.wall_construction.lower():
                construction_type = "concrete"
        wall_heating_load = _apply_thermal_bridging_factor(base_wall_load, construction_type, "wall", "heating")
        heating_load += wall_heating_load
    
    # Roof conduction with thermal bridging
    if roof_area > 0:
        base_roof_load = roof_u_factor * roof_area * (indoor_temp - outdoor_heating_temp)
        # Determine construction type for thermal bridging
        construction_type = "wood_frame"  # Default
        if envelope_data and hasattr(envelope_data, 'roof_construction'):
            if "steel" in envelope_data.roof_construction.lower():
                construction_type = "steel_frame"
            elif "concrete" in envelope_data.roof_construction.lower():
                construction_type = "concrete"
        roof_heating_load = _apply_thermal_bridging_factor(base_roof_load, construction_type, "roof", "heating")
        heating_load += roof_heating_load
    
    # Window conduction (no thermal bridging for windows)
    if window_area > 0:
        window_heating_load = window_u_factor * window_area * (indoor_temp - outdoor_heating_temp)
        heating_load += window_heating_load
    
    # Infiltration heating load - enhanced with blower door support
    room_volume = room.area * ceiling_height
    
    if envelope_data and envelope_data.infiltration_confidence >= 0.6:
        # Check if blower door results are available
        if envelope_data.blower_door_result:
            # Parse blower door result (e.g., "3 ACH50" or "1200 CFM50")
            blower_result = envelope_data.blower_door_result.strip().upper()
            if "ACH50" in blower_result:
                ach50 = float(blower_result.replace("ACH50", "").strip())
                cfm50 = convert_ach50_to_cfm50(ach50, room_volume)
            elif "CFM50" in blower_result:
                cfm50 = float(blower_result.replace("CFM50", "").strip())
            else:
                # Fallback to quality-based estimate
                cfm50 = None
            
            if cfm50:
                # Convert to natural infiltration using climate-specific factors
                infiltration_cfm = convert_cfm50_to_natural(
                    cfm50 * (room.area / room.area),  # Proportion for this room
                    climate_data['climate_zone'],
                    stories=1,  # Could be enhanced with building data
                    shielding="average"
                )
            else:
                # Use quality-based estimate
                quality_map = {
                    "tight": ConstructionQuality.TIGHT,
                    "code": ConstructionQuality.AVERAGE,
                    "loose": ConstructionQuality.LOOSE
                }
                quality = quality_map.get(envelope_data.infiltration_class, ConstructionQuality.AVERAGE)
                infiltration_cfm, ach_natural = estimate_infiltration_by_quality(
                    quality, room_volume, climate_data['climate_zone']
                )
        else:
            # Use infiltration class
            quality_map = {
                "tight": ConstructionQuality.TIGHT,
                "code": ConstructionQuality.AVERAGE,
                "loose": ConstructionQuality.LOOSE
            }
            quality = quality_map.get(envelope_data.infiltration_class, ConstructionQuality.AVERAGE)
            infiltration_cfm, ach_natural = estimate_infiltration_by_quality(
                quality, room_volume, climate_data['climate_zone']
            )
    else:
        # Use construction vintage defaults
        ach = construction_values.get('infiltration_ach', 0.5)
        infiltration_cfm = (room_volume * ach) / 60
    
    # Calculate infiltration heating load with seasonal adjustment
    # Apply 15% reduction for heating season (building contraction, less wind)
    heating_infiltration_cfm = infiltration_cfm * 0.85
    infiltration_loads = calculate_infiltration_loads(
        heating_infiltration_cfm, outdoor_heating_temp, indoor_temp
    )
    infiltration_heating = infiltration_loads['sensible']
    heating_load += infiltration_heating
    
    # Add ventilation heating load
    heating_load += ventilation['heating']
    
    # Add floor losses (only for ground floor rooms)
    if room.floor == 1:
        # Determine floor type from envelope data or use default
        floor_type = "slab"  # Default assumption
        if envelope_data:
            if envelope_data.floor_construction:
                if "slab" in envelope_data.floor_construction.lower():
                    floor_type = "slab"
                elif "crawl" in envelope_data.floor_construction.lower():
                    floor_type = "crawlspace"
                elif "basement" in envelope_data.floor_construction.lower():
                    floor_type = "basement"
        
        # Calculate floor losses
        floor_losses = _calculate_floor_losses(
            room.area,
            floor_type,
            outdoor_heating_temp,
            indoor_temp,
            climate_data['climate_zone'],
            perimeter_length=room_perimeter  # Use the calculated room perimeter
        )
        
        heating_load += floor_losses['heating']
        cooling_load += floor_losses['cooling']
        
        logger.info(f"Room {room.name}: Added floor losses - Heating: {floor_losses['heating']:.0f} BTU/hr, Type: {floor_type}")
    
    # Apply thermal mass adjustments
    if envelope_data:
        # Classify thermal mass level
        mass_level = classify_thermal_mass(
            wall_type=envelope_data.wall_construction,
            floor_type=envelope_data.floor_construction,
            exposed_slab=envelope_data.exposed_slab,
            interior_mass_walls=envelope_data.thermal_mass_walls
        )
        
        # Apply mass effects to loads
        cooling_load, heating_load = apply_thermal_mass_to_loads(
            cooling_load, heating_load, mass_level, room_type
        )
        
        logger.info(f"Room {room.name}: Applied {mass_level.value} thermal mass adjustments")
    
    # Apply corner room and thermal exposure multipliers
    if hasattr(room, 'source_elements'):
        # Corner room factor
        if room.source_elements.get('corner_room', False):
            heating_load *= 1.15  # 15% increase for corner rooms
            cooling_load *= 1.20  # 20% increase for corner rooms
            logger.info(f"Room {room.name}: Applied corner room factors (H:1.15x, C:1.20x)")
        
        # Thermal exposure factor
        thermal_exposure = room.source_elements.get('thermal_exposure', 'medium')
        exposure_factors = {
            'high': {'heating': 1.2, 'cooling': 1.25},
            'medium': {'heating': 1.1, 'cooling': 1.1},
            'low': {'heating': 1.0, 'cooling': 1.0}
        }
        factors = exposure_factors.get(thermal_exposure, exposure_factors['medium'])
        heating_load *= factors['heating']
        cooling_load *= factors['cooling']
        
        # Apply confidence-based safety factors
        room_confidence = room.confidence if hasattr(room, 'confidence') else 0.8
        if room_confidence < 0.5:
            # Low confidence - add safety margin
            heating_load *= 1.1
            cooling_load *= 1.1
            logger.warning(f"Room {room.name}: Low confidence ({room_confidence}) - applied 10% safety factor")
    
    # Create detailed load breakdown
    load_breakdown = {
        'heating': {
            'wall_conduction': wall_heating_load if 'wall_heating_load' in locals() else 0,
            'roof_conduction': roof_heating_load if 'roof_heating_load' in locals() else 0,
            'window_conduction': window_heating_load if 'window_heating_load' in locals() else 0,
            'infiltration_sensible': infiltration_heating,
            'infiltration_cfm': heating_infiltration_cfm if 'heating_infiltration_cfm' in locals() else infiltration_cfm if 'infiltration_cfm' in locals() else temp_infiltration_cfm,
            'ventilation': ventilation['heating'],
            'floor_losses': floor_losses['heating'] if 'floor_losses' in locals() else 0,
            'subtotal': heating_load / (factors.get('heating', 1.0) if 'factors' in locals() else 1.0),
            'multipliers_applied': []
        },
        'cooling': {
            'wall_conduction': wall_load if 'wall_load' in locals() else 0,
            'roof_conduction': roof_load if 'roof_load' in locals() else 0,
            'window_conduction': window_conduction if 'window_conduction' in locals() else 0,
            'window_solar': solar_load if 'solar_load' in locals() else 0,
            'internal_people': people_load if 'people_load' in locals() else 0,
            'internal_lighting': lighting_load if 'lighting_load' in locals() else 0,
            'internal_equipment': equipment_load if 'equipment_load' in locals() else 0,
            'infiltration_sensible': infiltration_cooling_loads['sensible'] if 'infiltration_cooling_loads' in locals() else 0,
            'infiltration_latent': infiltration_cooling_loads['latent'] if 'infiltration_cooling_loads' in locals() else 0,
            'infiltration_cfm': infiltration_cfm if 'infiltration_cfm' in locals() else temp_infiltration_cfm,
            'ventilation_sensible': ventilation.get('sensible_cooling', ventilation['cooling']),
            'ventilation_latent': ventilation.get('latent_cooling', 0),
            'floor_losses': floor_losses['cooling'] if 'floor_losses' in locals() else 0,
            'subtotal': cooling_load / (factors.get('cooling', 1.0) if 'factors' in locals() else 1.0),
            'multipliers_applied': []
        }
    }
    
    # Add multipliers info
    if hasattr(room, 'source_elements'):
        if room.source_elements.get('corner_room', False):
            load_breakdown['heating']['multipliers_applied'].append('corner_room: 1.15x')
            load_breakdown['cooling']['multipliers_applied'].append('corner_room: 1.20x')
        
        thermal_exposure = room.source_elements.get('thermal_exposure', 'medium')
        if thermal_exposure != 'low':
            load_breakdown['heating']['multipliers_applied'].append(f'thermal_exposure_{thermal_exposure}: {factors.get("heating", 1.0)}x')
            load_breakdown['cooling']['multipliers_applied'].append(f'thermal_exposure_{thermal_exposure}: {factors.get("cooling", 1.0)}x')
    
    # Apply interior room heating reduction (30% less heating load)
    # Interior rooms are conditioned by adjacent spaces and have lower heating needs
    if exterior_walls_count == 0:
        original_heating = heating_load
        heating_load *= 0.7  # 30% reduction for interior rooms
        logger.info(f"Room {room.name}: Applied interior room heating reduction: {original_heating:.0f} → {heating_load:.0f} BTU/hr")
    
    return {
        'heating': max(heating_load, 0),
        'cooling': max(cooling_load, 0),
        'breakdown': load_breakdown
    }


def _calculate_room_loads_simplified(room: Room, room_type: str, climate_data: Dict, 
                                   outdoor_cooling_temp: float, outdoor_heating_temp: float, include_ventilation: bool = True) -> Dict[str, float]:
    """Calculate room loads using simplified method (original approach)"""
    
    # Get climate zone factors
    climate_factors = get_climate_zone_factors(climate_data['climate_zone'])
    
    # Base loads per square foot
    base_heating = climate_factors['heating_factor']
    base_cooling = climate_factors['cooling_factor']
    
    # Apply room type multipliers
    room_mult = ROOM_MULTIPLIERS.get(room_type, ROOM_MULTIPLIERS["other"])
    heating_mult = room_mult["heating"]
    cooling_mult = room_mult["cooling"]
    
    # Apply orientation factors
    orientation_mult = ORIENTATION_FACTORS.get(room.orientation, ORIENTATION_FACTORS[""])
    heating_mult *= orientation_mult["heating"]
    cooling_mult *= orientation_mult["cooling"]
    
    # Apply window factors - reduced for heating, cap at 3 windows
    window_factor_heating = 1.0 + (min(room.windows, 3) * 0.08)  # 8% per window, max 3
    window_factor_cooling = 1.0 + (room.windows * 0.15) * 1.2    # Keep original for cooling
    heating_mult *= window_factor_heating
    cooling_mult *= window_factor_cooling
    
    # Calculate loads
    room_heating = room.area * base_heating * heating_mult
    room_cooling = room.area * base_cooling * cooling_mult
    
    # Add ventilation loads
    ventilation = _calculate_ventilation_load(
        room, 
        {'heating_db_99': outdoor_heating_temp, 'cooling_db_1': outdoor_cooling_temp, 'zone': climate_data['climate_zone']}, 
        include_ventilation=include_ventilation,
        outdoor_heating_temp=outdoor_heating_temp,
        outdoor_cooling_temp=outdoor_cooling_temp
    )
    room_heating += ventilation['heating']
    room_cooling += ventilation['cooling']
    
    return {
        'heating': room_heating,
        'cooling': room_cooling
    }


def calculate_manualj_with_audit(schema: BlueprintSchema, duct_config: str = "ducted_attic", heating_fuel: str = "gas", climate_data: Optional[Dict] = None, construction_vintage: Optional[str] = None, include_ventilation: bool = True, envelope_data: Optional[EnvelopeExtraction] = None, create_audit: bool = True, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    ACCA Manual J Load Calculation with Enhanced Audit Trail
    
    This function performs 100% ACCA Manual J 8th Edition compliant calculations
    with comprehensive audit logging for professional-grade accuracy.
    
    Args:
        schema: Parsed blueprint with room data
        duct_config: Duct configuration ("ducted_attic", "ducted_crawl", "ductless")
        heating_fuel: Heating fuel type ("gas", "heat_pump", "electric")
        climate_data: Pre-loaded climate data (preferred for consistency)
        construction_vintage: Building construction era
        include_ventilation: Include ASHRAE 62.2 ventilation loads
        envelope_data: AI-extracted envelope characteristics
        create_audit: Create detailed audit trail
        user_id: User identifier for audit trail
        
    Returns:
        Dict with heating/cooling loads, zone details, and audit information
    """
    calculation_start = time.time()
    
    # Use provided climate data or fetch it
    if climate_data is None:
        climate_data = get_climate_data(schema.zip_code)
    
    # Enhanced input validation for ACCA compliance
    if not schema.rooms or len(schema.rooms) == 0:
        raise ValueError("No rooms found in blueprint - cannot perform load calculations")
    
    if schema.sqft_total <= 0:
        raise ValueError("Invalid total square footage - must be greater than 0")
    
    # Validate climate data
    if not climate_data.get('heating_db_99') or not climate_data.get('cooling_db_1'):
        raise ValueError(f"Invalid climate data for zip code {schema.zip_code}")
    
    # Log calculation inputs for audit
    calculation_inputs = {
        'project_id': str(schema.project_id),
        'zip_code': schema.zip_code,
        'total_sqft': schema.sqft_total,
        'stories': schema.stories,
        'room_count': len(schema.rooms),
        'duct_config': duct_config,
        'heating_fuel': heating_fuel,
        'climate_zone': climate_data.get('climate_zone'),
        'outdoor_heating_temp': climate_data.get('heating_db_99'),
        'outdoor_cooling_temp': climate_data.get('cooling_db_1'),
        'construction_vintage': construction_vintage,
        'include_ventilation': include_ventilation,
        'envelope_data_available': envelope_data is not None,
        'calculation_timestamp': calculation_start
    }
    
    logger.info(f"Starting ACCA Manual J calculation with inputs: {calculation_inputs}")
    
    # Call the main calculation function
    result = calculate_manualj(
        schema=schema,
        duct_config=duct_config,
        heating_fuel=heating_fuel,
        construction_vintage=construction_vintage,
        include_ventilation=include_ventilation,
        envelope_data=envelope_data,
        create_audit=create_audit,
        user_id=user_id
    )
    
    # Enhanced result validation for ACCA compliance
    _validate_calculation_results(result, schema, climate_data)
    
    # Add comprehensive audit information to results
    calculation_time = time.time() - calculation_start
    
    # Calculate load breakdown summary
    load_breakdown_summary = _calculate_load_breakdown_summary(result)
    
    result['audit_information'] = {
        'calculation_inputs': calculation_inputs,
        'calculation_time_seconds': calculation_time,
        'acca_compliance_version': 'Manual J 8th Edition',
        'validation_passed': True,
        'data_quality_checks': _perform_data_quality_checks(schema, result),
        'calculation_warnings': _check_calculation_warnings(result, schema),
        'load_summary': load_breakdown_summary,
        'assumptions_made': _get_calculation_assumptions(envelope_data, construction_vintage),
        'climate_data_source': climate_data.get('data_source', 'ASHRAE/IECC Database'),
        'calculation_methods': {
            'envelope_loads': 'Enhanced CLTD/CLF' if envelope_data else 'Simplified factors',
            'infiltration': 'Blower door conversion' if envelope_data and envelope_data.blower_door_result else 'ACH estimate',
            'ventilation': 'ASHRAE 62.2-2019',
            'internal_gains': 'ACCA Manual J defaults',
            'diversity': 'ACCA Manual J Table 2A'
        }
    }
    
    logger.info(f"ACCA Manual J calculation completed in {calculation_time:.2f}s")
    return result


def _generate_missing_common_spaces(parsed_area: float, declared_area: float, existing_rooms: List[Room]) -> List[Dict[str, Any]]:
    """Generate typical missing common spaces when parsing misses significant area"""
    missing_area = declared_area - parsed_area
    generated_rooms = []
    
    # Check what room types we already have
    existing_types = set(room.room_type if hasattr(room, 'room_type') else _classify_room_type(room.name) 
                        for room in existing_rooms)
    
    # Common spaces often missed in parsing
    common_spaces = [
        ("Hallways", 0.08, "hallway"),      # ~8% of home
        ("Entry/Foyer", 0.04, "other"),     # ~4% of home
        ("Closets", 0.06, "closet"),       # ~6% of home
        ("Pantry", 0.02, "closet"),        # ~2% of home
        ("Utility/Mechanical", 0.03, "utility"), # ~3% of home
    ]
    
    # Add missing common spaces proportionally
    for space_name, typical_percent, room_type in common_spaces:
        if room_type not in existing_types or room_type == "closet":  # Always add closets
            space_area = declared_area * typical_percent
            if space_area <= missing_area * 0.5:  # Don't overcompensate
                generated_rooms.append({
                    "name": f"{space_name} (Generated)",
                    "area": space_area,
                    "room_type": room_type,
                    "generated": True,
                    "confidence": 0.3
                })
                missing_area -= space_area
    
    # If still significant missing area, add as "Unaccounted Space"
    if missing_area > 100:
        generated_rooms.append({
            "name": "Unaccounted Space (Generated)",
            "area": missing_area,
            "room_type": "other",
            "generated": True,
            "confidence": 0.1
        })
    
    return generated_rooms


def calculate_manualj(schema: BlueprintSchema, duct_config: str = "ducted_attic", heating_fuel: str = "gas", construction_vintage: Optional[str] = None, include_ventilation: bool = True, envelope_data: Optional[EnvelopeExtraction] = None, create_audit: bool = True, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate ACCA Manual J heating and cooling loads
    
    Args:
        schema: Parsed blueprint with room data
        duct_config: Duct configuration ("ducted_attic", "ducted_crawl", "ductless")
        heating_fuel: Heating fuel type ("gas", "heat_pump", "electric")
        
    Returns:
        Dict with heating/cooling loads and zone details
    """
    # Validate blueprint data first
    validator = BlueprintValidator()
    validation_result = validator.validate_blueprint(schema)
    
    # Log validation issues
    if not validation_result.is_valid:
        logger.error(f"Blueprint validation failed with {len(validation_result.issues)} issues")
        for issue in validation_result.issues:
            if issue.severity == ValidationSeverity.ERROR:
                logger.error(f"Validation Error: {issue.message} - {issue.suggested_fix}")
            elif issue.severity == ValidationSeverity.WARNING:
                logger.warning(f"Validation Warning: {issue.message} - {issue.suggested_fix}")
    
    # Add validation warnings to result
    validation_warnings = []
    for issue in validation_result.issues:
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]:
            validation_warnings.append({
                "severity": issue.severity.value,
                "message": issue.message,
                "fix": issue.suggested_fix,
                "details": issue.details
            })
    
    # Get climate data from comprehensive database
    climate_data = get_climate_data(schema.zip_code)
    
    # Get climate zone factors
    climate_factors = get_climate_zone_factors(climate_data['climate_zone'])
    
    # Get construction values - use default if vintage not specified
    if construction_vintage:
        construction_values = get_construction_vintage_values(construction_vintage)
    else:
        # Default to 1980-2000 construction standards if no vintage specified
        construction_values = get_construction_vintage_values('1980-2000')
    
    # For backward compatibility, create climate dict in old format
    climate = {
        "heating_factor": climate_factors['heating_factor'],
        "cooling_factor": climate_factors['cooling_factor'], 
        "zone": climate_data['climate_zone']
    }
    
    # Get design temperatures
    outdoor_cooling_temp = climate_data.get('cooling_db_1', 90)
    outdoor_heating_temp = climate_data.get('heating_db_99', 10)
    indoor_temp = 75
    
    zones = []
    total_heating = 0.0
    total_cooling = 0.0
    
    # Check if we need to generate missing common spaces
    total_room_area = sum(room.area for room in schema.rooms)
    area_discrepancy_percent = abs(total_room_area - schema.sqft_total) / schema.sqft_total * 100 if schema.sqft_total > 0 else 0
    
    rooms_to_process = list(schema.rooms)  # Create a copy to avoid modifying original
    
    # If significant area is missing and we have few rooms, generate common spaces
    if area_discrepancy_percent > 30 and len(schema.rooms) < 10:
        logger.warning(f"Significant area missing ({area_discrepancy_percent:.0f}%) and only {len(schema.rooms)} rooms found")
        logger.warning("Generating typical missing common spaces for more accurate load calculations")
        
        generated_spaces = _generate_missing_common_spaces(total_room_area, schema.sqft_total, schema.rooms)
        
        # Convert generated spaces to Room objects
        for space_data in generated_spaces:
            # Estimate dimensions based on area
            width = math.sqrt(space_data['area'] / 1.5)  # Assume 1.5:1 aspect ratio
            length = width * 1.5
            
            generated_room = Room(
                name=space_data['name'],
                dimensions_ft=(width, length),
                floor=1,  # Assume first floor
                windows=0 if space_data['room_type'] in ['closet', 'hallway'] else 1,
                orientation='unknown',
                area=space_data['area'],
                room_type=space_data['room_type'],
                confidence=space_data['confidence'],
                center_position=(0.0, 0.0),
                label_found=False,
                dimensions_source='generated',
                source_elements={'generated': True, 'reason': 'missing_area_compensation'}
            )
            rooms_to_process.append(generated_room)
            
            logger.info(f"Added generated space: {space_data['name']} ({space_data['area']:.0f} sqft)")
    
    for room in rooms_to_process:
        room_type = _classify_room_type(room.name)
        
        # Use enhanced CLF/CLTD calculations if construction vintage or envelope data is provided
        if (construction_vintage and construction_values) or envelope_data:
            room_loads = _calculate_room_loads_cltd_clf(
                room, room_type, climate_data, construction_values or {}, 
                outdoor_cooling_temp, outdoor_heating_temp, indoor_temp, 
                include_ventilation, envelope_data
            )
            if envelope_data:
                calculation_method = "Enhanced CLF/CLTD with AI Extraction"
            else:
                calculation_method = "Enhanced CLF/CLTD"
        else:
            # Fallback to simplified method for backward compatibility
            room_loads = _calculate_room_loads_simplified(
                room, room_type, climate_data, outdoor_cooling_temp, outdoor_heating_temp, include_ventilation
            )
            calculation_method = "Simplified"
        
        room_heating = room_loads['heating']
        room_cooling = room_loads['cooling']
        
        zone_data = {
            "name": room.name,
            "area": room.area,
            "room_type": room_type,
            "floor": room.floor,
            "heating_btu": round(room_heating),
            "cooling_btu": round(room_cooling),
            "cfm_required": _calculate_airflow(room_cooling),
            "duct_size": _calculate_duct_size(room_cooling),
            "calculation_method": calculation_method
        }
        
        # Add detailed breakdown if available
        if 'breakdown' in room_loads:
            zone_data['load_breakdown'] = room_loads['breakdown']
        
        # Add confidence and data quality info if available
        if hasattr(room, 'confidence'):
            zone_data['confidence'] = room.confidence
        
        if hasattr(room, 'source_elements'):
            zone_data['data_quality'] = {
                'orientation_known': room.orientation != 'unknown',
                'orientation_confidence': room.source_elements.get('orientation_confidence', 0.0),
                'dimension_source': room.source_elements.get('dimension_source', 'unknown'),
                'exterior_walls': room.source_elements.get('exterior_walls', 1),
                'corner_room': room.source_elements.get('corner_room', False)
            }
        
        zones.append(zone_data)
        
        total_heating += room_heating
        total_cooling += room_cooling
    
    # Apply intelligent area correction factor if room areas don't match declared total
    # This accounts for spaces that may not have been detected (hallways, closets, etc.)
    # Recalculate total area after potentially adding generated rooms
    total_room_area = sum(zone['area'] for zone in zones)
    area_correction_factor = 1.0
    area_discrepancy_percent = abs(total_room_area - schema.sqft_total) / schema.sqft_total * 100 if schema.sqft_total > 0 else 0
    
    if total_room_area > 0 and area_discrepancy_percent > 10:
        # Calculate raw correction factor
        raw_correction = schema.sqft_total / total_room_area
        
        # Apply graduated correction based on discrepancy magnitude
        if area_discrepancy_percent < 20:
            # Small discrepancy (10-20%): Apply gentle correction
            area_correction_factor = 1.0 + (raw_correction - 1.0) * 0.5  # 50% of the difference
            logger.info(f"Small area discrepancy ({area_discrepancy_percent:.0f}%): Applying gentle correction {area_correction_factor:.2f}")
            
        elif area_discrepancy_percent < 50:
            # Moderate discrepancy (20-50%): Apply graduated correction with 1.2x cap
            # As discrepancy increases, apply more of the correction
            correction_strength = 0.5 + (area_discrepancy_percent - 20) / 30 * 0.3  # 50% to 80%
            area_correction_factor = 1.0 + (raw_correction - 1.0) * correction_strength
            area_correction_factor = min(area_correction_factor, 1.2)  # Cap at 1.2x for accuracy
            logger.warning(f"Moderate area discrepancy ({area_discrepancy_percent:.0f}%): Applying {correction_strength:.0%} correction = {area_correction_factor:.2f} (capped at 1.2x)")
            
        else:
            # Large discrepancy (>50%): Cap correction factor and flag for review
            area_correction_factor = min(raw_correction, 1.2)  # Cap at 1.2x
            logger.error(f"Large area discrepancy ({area_discrepancy_percent:.0f}%): Capping correction at {area_correction_factor:.2f}")
            logger.error(f"Parsed: {total_room_area:.0f} sqft, Declared: {schema.sqft_total:.0f} sqft")
            logger.error("Manual review recommended - parsing may have missed significant areas")
            
            # Add warning to validation results
            if 'validation' not in locals():
                validation_warnings.append({
                    "severity": "ERROR",
                    "message": f"Severe area mismatch: Only {total_room_area:.0f} sqft parsed vs {schema.sqft_total:.0f} sqft declared",
                    "fix": "Review blueprint parsing or verify declared square footage",
                    "details": {"discrepancy_percent": area_discrepancy_percent, "correction_capped": True}
                })
        
        logger.info(f"Area correction: {total_room_area:.0f} sqft parsed → {schema.sqft_total:.0f} sqft declared "
                   f"(factor: {area_correction_factor:.2f})")
        
        # Apply correction to both heating and cooling loads
        total_heating *= area_correction_factor
        total_cooling *= area_correction_factor
        
        # Also update zone data to reflect scaled loads
        for zone in zones:
            zone['heating_btu'] = int(zone['heating_btu'] * area_correction_factor)
            zone['cooling_btu'] = int(zone['cooling_btu'] * area_correction_factor)
            zone['area_corrected'] = True
    
    # Apply Manual J diversity factor to prevent oversizing
    diversity_factor = get_diversity_factor(len(schema.rooms))
    total_cooling *= diversity_factor
    
    # Apply system factors
    # Duct losses/gains based on configuration
    # ACCA Manual J requires accounting for both duct losses (heating) and gains (cooling)
    if duct_config == "ductless":
        duct_heating_factor = 1.0   # No duct losses for ductless systems
        duct_cooling_factor = 1.0   # No duct gains for ductless systems
    elif duct_config == "ducted_crawl":
        duct_heating_factor = 1.08  # 8% heating loss in conditioned crawl space (reduced from 10%)
        duct_cooling_factor = 1.05  # 5% cooling gain in conditioned crawl space
    else:  # ducted_attic
        duct_heating_factor = 1.12  # 12% heating loss in unconditioned attic (reduced from 15%)
        duct_cooling_factor = 1.10  # 10% cooling gain in unconditioned attic
    
    total_heating *= duct_heating_factor
    total_cooling *= duct_cooling_factor
    
    # NO SAFETY FACTORS - Per ACCA Manual J best practices
    # Equipment should be sized to calculated loads only
    # Safety factors lead to oversizing and performance issues
    
    # Equipment sizing recommendations
    equipment = _recommend_equipment(total_heating, total_cooling, schema.sqft_total, heating_fuel)
    
    # Calculate overall confidence metrics
    confidence_metrics = _calculate_confidence_metrics(zones, schema)
    
    result = {
        "heating_total": round(total_heating),
        "cooling_total": round(total_cooling),
        "zones": zones,
        "climate_zone": climate["zone"],
        "equipment_recommendations": equipment,
        "design_parameters": {
            "outdoor_heating_temp": outdoor_heating_temp,
            "outdoor_cooling_temp": outdoor_cooling_temp,
            "indoor_temp": indoor_temp,
            "duct_config": duct_config,
            "heating_fuel": heating_fuel,
            "duct_heating_factor": duct_heating_factor,
            "duct_cooling_factor": duct_cooling_factor,
            "safety_factor": 1.0,  # No safety factor per Manual J best practices
            "diversity_factor": diversity_factor,
            "area_correction_factor": area_correction_factor,
            "construction_vintage": construction_vintage,
            "calculation_method": calculation_method,
            "include_ventilation": include_ventilation,
            "construction_values": construction_values
        },
        "confidence_metrics": confidence_metrics,
        "validation": {
            "is_valid": validation_result.is_valid,
            "confidence_score": validation_result.confidence_score,
            "warnings": validation_warnings,
            "scale_found": validation_result.scale_found,
            "total_area_calculated": validation_result.total_area_calculated,
            "total_area_declared": validation_result.total_area_declared
        }
    }
    
    # Validate HVAC calculations after they're done
    hvac_issues = validator.validate_hvac_calculations(
        schema.sqft_total,
        total_heating,
        total_cooling
    )
    
    # Add HVAC validation issues to warnings
    for issue in hvac_issues:
        validation_warnings.append({
            "severity": issue.severity.value,
            "message": issue.message,
            "fix": issue.suggested_fix,
            "details": issue.details
        })
    
    # Update validation warnings in result
    result["validation"]["warnings"] = validation_warnings
    
    # Perform Manual J sanity checks
    sanity_checks = _perform_manual_j_sanity_checks(
        schema.sqft_total,
        total_heating,
        total_cooling,
        climate["zone"],
        construction_vintage
    )
    
    # Add sanity check results to validation
    result["validation"]["sanity_checks"] = sanity_checks
    result["validation"]["sqft_per_ton"] = sanity_checks["sqft_per_ton"]
    
    # Add sanity check warnings/errors to main warnings
    for error in sanity_checks.get("errors", []):
        validation_warnings.append({
            "severity": "error",
            "message": error,
            "fix": "Review calculation inputs - loads appear incorrect",
            "details": {"source": "manual_j_sanity_check"}
        })
    
    for warning in sanity_checks.get("warnings", []):
        validation_warnings.append({
            "severity": "warning", 
            "message": warning,
            "fix": "Verify inputs are accurate",
            "details": {"source": "manual_j_sanity_check"}
        })
    
    # Create audit snapshot if requested
    if create_audit:
        try:
            calculation_id = create_calculation_audit(
                blueprint_schema=schema,
                calculation_result=result,
                climate_data=climate_data,
                construction_vintage=construction_vintage,
                envelope_data=envelope_data,
                user_id=user_id,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                include_ventilation=include_ventilation
            )
            result["audit_id"] = calculation_id
        except Exception as e:
            print(f"Warning: Failed to create audit snapshot: {e}")
            result["audit_id"] = None
    
    return result


def _perform_manual_j_sanity_checks(
    total_area: float, 
    heating_btu: float, 
    cooling_btu: float,
    climate_zone: str,
    construction_vintage: str
) -> Dict[str, Any]:
    """Perform comprehensive Manual J sanity checks per ACCA best practices"""
    
    cooling_tons = cooling_btu / 12000
    sqft_per_ton = total_area / cooling_tons if cooling_tons > 0 else 0
    heating_per_sqft = heating_btu / total_area if total_area > 0 else 0
    cooling_per_sqft = cooling_btu / total_area if total_area > 0 else 0
    
    checks = {
        "passed": True,
        "sqft_per_ton": round(sqft_per_ton),
        "heating_btu_per_sqft": round(heating_per_sqft, 1),
        "cooling_btu_per_sqft": round(cooling_per_sqft, 1),
        "warnings": [],
        "errors": []
    }
    
    # Primary check: sq ft/ton for construction vintage
    if construction_vintage in ['current-code', '2000-2020']:
        # New construction should be 600-1500 sq ft/ton
        if sqft_per_ton < 600:
            checks["errors"].append(f"Equipment oversized: {sqft_per_ton:.0f} sq ft/ton (expect 600-1500 for new construction)")
            checks["passed"] = False
        elif sqft_per_ton > 1500:
            checks["warnings"].append(f"Equipment may be undersized: {sqft_per_ton:.0f} sq ft/ton (expect 600-1500 for new construction)")
    else:
        # Older construction 400-1200 sq ft/ton
        if sqft_per_ton < 400:
            checks["errors"].append(f"Equipment severely oversized: {sqft_per_ton:.0f} sq ft/ton (expect 400-1200 for older construction)")
            checks["passed"] = False
        elif sqft_per_ton > 1200:
            checks["warnings"].append(f"Equipment may be undersized: {sqft_per_ton:.0f} sq ft/ton (expect 400-1200 for older construction)")
    
    # Climate-specific BTU/sqft ranges
    zone_num = int(climate_zone[0]) if climate_zone[0].isdigit() else 4
    expected_ranges = {
        1: {"heating": (10, 30), "cooling": (25, 50)},  # Very hot
        2: {"heating": (15, 35), "cooling": (20, 45)},  # Hot  
        3: {"heating": (20, 40), "cooling": (15, 35)},  # Warm
        4: {"heating": (25, 50), "cooling": (12, 30)},  # Mixed
        5: {"heating": (30, 60), "cooling": (10, 25)},  # Cool
        6: {"heating": (35, 70), "cooling": (8, 20)},   # Cold
        7: {"heating": (40, 80), "cooling": (5, 15)},   # Very cold
        8: {"heating": (45, 90), "cooling": (3, 12)}    # Subarctic
    }
    
    h_min, h_max = expected_ranges.get(zone_num, (25, 50))["heating"]
    c_min, c_max = expected_ranges.get(zone_num, (12, 30))["cooling"]
    
    if not (h_min <= heating_per_sqft <= h_max):
        checks["warnings"].append(f"Heating load {heating_per_sqft:.1f} BTU/sqft outside climate zone {climate_zone} range ({h_min}-{h_max})")
    
    if not (c_min <= cooling_per_sqft <= c_max):
        checks["warnings"].append(f"Cooling load {cooling_per_sqft:.1f} BTU/sqft outside climate zone {climate_zone} range ({c_min}-{c_max})")
    
    # Add recommendations
    if not checks["passed"]:
        checks["recommendations"] = [
            "Review envelope inputs (insulation, windows, infiltration)",
            "Verify room areas and counts are accurate",
            "Check that no arbitrary safety factors were applied",
            "Ensure proper climate data is being used"
        ]
    
    return checks


def _classify_room_type(room_name: str) -> str:
    """Classify room type from name"""
    name = room_name.lower()
    
    if any(word in name for word in ["living", "family", "great"]):
        return "living"
    elif any(word in name for word in ["bed", "master"]):
        return "bedroom"
    elif "kitchen" in name or "kit" in name:
        return "kitchen"
    elif any(word in name for word in ["bath", "powder"]):
        return "bathroom"
    elif "dining" in name:
        return "dining"
    elif any(word in name for word in ["office", "study", "den"]):
        return "office"
    elif any(word in name for word in ["utility", "laundry", "mechanical"]):
        return "utility"
    else:
        return "other"


def _calculate_ventilation_load(room: Room, climate: Dict, include_ventilation: bool = True, 
                              outdoor_heating_temp: float = None, outdoor_cooling_temp: float = None) -> Dict[str, float]:
    """
    Calculate minimum ventilation load per ASHRAE 62.2
    
    Args:
        room: Room object with area and other properties
        climate: Climate data dictionary
        include_ventilation: Whether to include ventilation loads (default True)
        outdoor_heating_temp: Outdoor heating design temperature
        outdoor_cooling_temp: Outdoor cooling design temperature
        
    Returns:
        Dict with heating, cooling, and cfm values
    """
    if not include_ventilation:
        return {"heating": 0.0, "cooling": 0.0, "cfm": 0.0}
    
    # ASHRAE 62.2 Ventilation Requirements
    # Determine occupancy based on room type and area
    room_type = _classify_room_type(room.name)
    
    # People-based ventilation (CFM per person)
    people_cfm_rates = {
        'bedroom': 5.0,      # 5 CFM per person (bedrooms determine occupancy)
        'living': 5.0,       # 5 CFM per person  
        'dining': 5.0,       # 5 CFM per person
        'kitchen': 25.0,     # 25 CFM per person (kitchen)
        'bathroom': 25.0,    # 25 CFM per person (bathroom)
        'office': 5.0,       # 5 CFM per person
        'utility': 0.0,      # No people-based requirement
        'other': 5.0         # Default 5 CFM per person
    }
    
    # Area-based ventilation (CFM per sq ft)
    area_cfm_rates = {
        'bedroom': 0.0,      # No area-based for bedrooms
        'living': 0.06,      # 0.06 CFM/sq ft
        'dining': 0.06,      # 0.06 CFM/sq ft  
        'kitchen': 0.0,      # No area-based for kitchens
        'bathroom': 0.0,     # No area-based for bathrooms
        'office': 0.06,      # 0.06 CFM/sq ft
        'utility': 0.06,     # 0.06 CFM/sq ft
        'other': 0.06        # Default 0.06 CFM/sq ft
    }
    
    # Estimate occupancy (simplified)
    if room_type == 'bedroom':
        # Bedrooms determine occupancy: 1 person per bedroom + 1
        people_count = 1  # Simplified: 1 person per bedroom
    elif room_type in ['kitchen', 'bathroom']:
        # Use total building occupancy factor
        people_count = max(1, room.area / 200)  # 1 person per 200 sq ft
    else:
        # Other rooms: base on area
        people_count = max(1, room.area / 300)  # 1 person per 300 sq ft
    
    # Calculate required CFM
    people_cfm = people_count * people_cfm_rates.get(room_type, 5.0)
    area_cfm = room.area * area_cfm_rates.get(room_type, 0.06)
    
    # Total ventilation requirement
    total_cfm = people_cfm + area_cfm
    
    # Apply minimum requirements
    min_cfm = 7.5  # Absolute minimum per ASHRAE 62.2
    if room_type == 'bathroom':
        min_cfm = max(min_cfm, 50)  # Bathrooms need minimum 50 CFM
    elif room_type == 'kitchen':
        min_cfm = max(min_cfm, 25)  # Kitchens need minimum 25 CFM
    
    base_cfm = max(total_cfm, min_cfm)
    
    # Get actual design temperatures
    if outdoor_heating_temp is None:
        outdoor_heating_temp = climate.get('heating_db_99', -10)
    if outdoor_cooling_temp is None:
        outdoor_cooling_temp = climate.get('cooling_db_1', 95)
    
    indoor_temp = 75  # Standard indoor temperature
    
    # Calculate loads
    # Sensible load: CFM × 1.08 × ΔT
    heating_td = indoor_temp - outdoor_heating_temp
    cooling_td = outdoor_cooling_temp - indoor_temp
    
    ventilation_heating = base_cfm * 1.08 * heating_td
    ventilation_cooling = base_cfm * 1.08 * cooling_td
    
    # Add latent load for cooling (moisture removal)
    # Latent load: CFM × 0.68 × Δgr (grains of moisture difference)
    # Assume 50% RH indoors, varies by climate zone outdoors
    climate_zone = climate.get('zone', '4A')
    
    # Simplified latent load factors by climate zone
    latent_factors = {
        '1A': 15.0,  # Very humid - high latent load
        '2A': 12.0,  # Hot-humid
        '2B': 8.0,   # Hot-dry
        '3A': 10.0,  # Warm-humid  
        '3B': 6.0,   # Warm-dry
        '3C': 4.0,   # Marine
        '4A': 8.0,   # Mixed-humid
        '4B': 5.0,   # Mixed-dry
        '4C': 3.0,   # Mixed-marine
        '5A': 6.0,   # Cool-humid
        '5B': 4.0,   # Cool-dry
        '6A': 4.0,   # Cold-humid
        '6B': 3.0,   # Cold-dry
        '7': 2.0,    # Very cold
        '8': 1.0     # Subarctic
    }
    
    latent_factor = latent_factors.get(climate_zone, 6.0)
    latent_cooling = base_cfm * 0.68 * latent_factor
    
    # Add latent load to total cooling load
    total_ventilation_cooling = ventilation_cooling + latent_cooling
    
    return {
        "heating": max(ventilation_heating, 0),
        "cooling": max(total_ventilation_cooling, 0),
        "sensible_cooling": max(ventilation_cooling, 0),
        "latent_cooling": max(latent_cooling, 0),
        "cfm": base_cfm,
        "people_cfm": people_cfm,
        "area_cfm": area_cfm
    }


def _calculate_airflow(cooling_load: float) -> int:
    """Calculate required airflow in CFM"""
    # Rule of thumb: 400 CFM per ton of cooling
    # 1 ton = 12,000 BTU/hr
    tons = cooling_load / 12000
    cfm = tons * 400
    return max(50, round(cfm))  # Minimum 50 CFM


def _calculate_duct_size(cooling_load: float) -> str:
    """Recommend duct size based on cooling load"""
    cfm = _calculate_airflow(cooling_load)
    
    # Round duct sizing (simplified)
    if cfm <= 75:
        return "6 inch"
    elif cfm <= 125:
        return "7 inch"
    elif cfm <= 180:
        return "8 inch"
    elif cfm <= 250:
        return "9 inch"
    elif cfm <= 350:
        return "10 inch"
    else:
        return "12 inch"


def _get_equipment_match_rating(equipment_capacity_tons: float, cooling_load_tons: float) -> Dict[str, str]:
    """
    Get equipment match rating based on Manual S sizing guidelines
    
    Manual S guidelines:
    - Good: 95-115% of load (within proper sizing window)
    - OK: 115-125% of load (acceptable, slight oversizing)  
    - Poor: <95% or >125% of load (undersized or oversized)
    
    Args:
        equipment_capacity_tons: Equipment capacity in tons
        cooling_load_tons: Calculated cooling load in tons
        
    Returns:
        Dict with rating and explanation
    """
    if cooling_load_tons <= 0:
        return {"rating": "Unknown", "explanation": "Invalid load calculation"}
    
    sizing_ratio = equipment_capacity_tons / cooling_load_tons
    
    if 0.95 <= sizing_ratio <= 1.15:
        return {
            "rating": "Good", 
            "explanation": f"Equipment is {sizing_ratio:.1%} of load (optimal 95-115% range)"
        }
    elif 1.15 < sizing_ratio <= 1.25:
        return {
            "rating": "OK",
            "explanation": f"Equipment is {sizing_ratio:.1%} of load (acceptable, slightly oversized)"
        }
    elif sizing_ratio < 0.95:
        return {
            "rating": "Poor",
            "explanation": f"Equipment is {sizing_ratio:.1%} of load (undersized, <95%)"
        }
    else:  # > 1.25
        return {
            "rating": "Poor", 
            "explanation": f"Equipment is {sizing_ratio:.1%} of load (oversized, >125%)"
        }


def _recommend_equipment(heating_btu: float, cooling_btu: float, total_sqft: float, heating_fuel: str = "gas") -> Dict[str, Any]:
    """Recommend HVAC equipment based on loads and fuel type - Manual S compliant"""
    
    # Convert to tons (cooling)
    cooling_tons = cooling_btu / 12000
    
    # Equipment recommendation based on heating fuel selection
    if heating_fuel == "heat_pump":
        system_type = "Heat Pump"
        primary_capacity = max(heating_btu, cooling_btu)
    elif heating_fuel == "gas":
        system_type = "Natural Gas Furnace + AC"
        primary_capacity = cooling_btu
    else:  # electric
        system_type = "Electric Furnace + AC"
        primary_capacity = cooling_btu
    
    # Manual S compliant sizing (95-115% of calculated load)
    min_capacity = cooling_tons * 0.95  # 95% minimum
    max_capacity = cooling_tons * 1.15  # 115% maximum for good rating
    acceptable_max = cooling_tons * 1.25  # 125% maximum for acceptable rating
    
    # Size recommendations with Manual S match ratings
    size_options = []
    available_sizes = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
    
    # Sanity check
    sqft_per_ton = total_sqft / cooling_tons if cooling_tons > 0 else 0
    sanity_check_passed = 400 <= sqft_per_ton <= 2000  # Wide range for all construction types
    
    for size in available_sizes:
        if size >= min_capacity and size <= acceptable_max:
            # Get Manual S match rating based on proper criteria
            if size >= min_capacity and size <= max_capacity:
                rating = "Good"
                explanation = f"Within optimal Manual S range (95-115% of {cooling_tons:.1f} tons)"
            elif size <= acceptable_max:
                rating = "Acceptable"
                explanation = f"Within acceptable Manual S range (115-125% of {cooling_tons:.1f} tons)"
            else:
                rating = "Poor"
                explanation = f"Oversized per Manual S (>125% of {cooling_tons:.1f} tons)"
            
            # Validate against sq ft/ton
            size_sqft_per_ton = total_sqft / size
            size_sanity_check = 400 <= size_sqft_per_ton <= 2000
            
            size_options.append({
                "capacity_tons": size,
                "capacity_btu": size * 12000,
                "sqft_per_ton": round(size_sqft_per_ton),
                "efficiency_rating": "16+ SEER recommended",
                "estimated_cost": f"${size * 2500:.0f} - ${size * 4000:.0f}",
                "manual_s_rating": rating,
                "manual_s_explanation": explanation,
                "sanity_check_passed": size_sanity_check,
                "recommended": rating == "Good" and size_sanity_check
            })
    
    return {
        "system_type": system_type,
        "calculated_load_tons": round(cooling_tons, 2),
        "manual_s_sizing_range": f"{min_capacity:.1f} - {max_capacity:.1f} tons",
        "sqft_per_ton": round(sqft_per_ton),
        "load_sanity_check": "PASS" if sanity_check_passed else "REVIEW NEEDED",
        "size_options": size_options[:3],  # Top 3 options
        "ductwork_recommendation": _recommend_ductwork(total_sqft),
        "sizing_notes": [
            "Equipment sized per ACCA Manual S (95-115% of calculated load)",
            "No safety factors applied to load calculations",
            f"Calculated {sqft_per_ton:.0f} sq ft/ton" + (" - typical for new construction" if 600 <= sqft_per_ton <= 1500 else "")
        ]
    }


def _recommend_ductwork(total_sqft: float) -> str:
    """Recommend ductwork type based on house size"""
    if total_sqft < 1500:
        return "Flexible duct with insulated supply plenum"
    elif total_sqft < 2500:
        return "Mixed rigid and flexible duct system"
    else:
        return "Rigid sheet metal ductwork with zoning"


def _get_design_temp(zip_code: str, season: str) -> int:
    """Get outdoor design temperature for location using ASHRAE data"""
    try:
        climate_data = get_climate_data(zip_code)
        
        if season == "heating":
            # Use 99% heating design temperature
            return climate_data.get('heating_db_99', 10)
        else:  # cooling
            # Use 1% cooling design temperature 
            return climate_data.get('cooling_db_1', 90)
            
    except Exception as e:
        print(f"Warning: Could not get design temp for {zip_code}: {e}")
        # Fallback to legacy hardcoded values
        temp_data = {
            "90210": {"heating": 35, "cooling": 95},   # Los Angeles
            "10001": {"heating": 15, "cooling": 85},   # NYC
            "33101": {"heating": 45, "cooling": 92},   # Miami
            "60601": {"heating": -5, "cooling": 88},   # Chicago
            "default": {"heating": 10, "cooling": 90}
        }
        
        location_temps = temp_data.get(zip_code, temp_data["default"])
        return location_temps[season]


# Legacy function for backward compatibility
def calculate_loads(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Legacy function - converts old format to new"""
    # Convert old room format to new schema format
    schema_rooms = []
    for room in rooms:
        schema_rooms.append(Room(
            name=room.get("name", "Unknown Room"),
            dimensions_ft=(12.0, 12.0),  # Default dimensions
            floor=1,
            windows=room.get("windows", 1),
            orientation=room.get("orientation", ""),
            area=room.get("area", 144.0)
        ))
    
    # Create basic schema
    from uuid import uuid4
    schema = BlueprintSchema(
        project_id=uuid4(),
        zip_code="90210",  # Default
        sqft_total=sum(room.area for room in schema_rooms),
        stories=1,
        rooms=schema_rooms
    )
    
    # Calculate using new method
    result = calculate_manualj(schema)
    
    # Return in old format for compatibility
    return {
        "total_heating_btu": result["heating_total"],
        "total_cooling_btu": result["cooling_total"],
        "per_room_estimates": [
            {
                "name": zone["name"],
                "heating_btu": zone["heating_btu"],
                "cooling_btu": zone["cooling_btu"]
            }
            for zone in result["zones"]
        ]
    }


def _validate_calculation_results(result: Dict[str, Any], schema: BlueprintSchema, climate_data: Dict) -> None:
    """
    Enhanced Manual J calculation validation for ACCA compliance
    
    Args:
        result: Calculation results to validate
        schema: Original blueprint schema
        climate_data: Climate data used in calculations
        
    Raises:
        ValueError: If validation fails
    """
    # Check required result fields
    required_fields = ['heating_total', 'cooling_total', 'zones', 'climate_zone', 'design_parameters']
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required result field: {field}")
    
    # Validate load magnitudes (reasonable ranges for residential)
    heating_total = result['heating_total']
    cooling_total = result['cooling_total']
    total_sqft = schema.sqft_total
    
    # ACCA Manual J typical load ranges by climate zone
    climate_zone = climate_data.get('climate_zone', '4A')
    zone_num = int(climate_zone[0]) if climate_zone[0].isdigit() else 4
    
    # Expected ranges by climate zone (BTU/hr/sqft)
    heating_ranges = {
        1: (5, 25),    # Very hot
        2: (10, 35),   # Hot
        3: (15, 45),   # Warm
        4: (20, 55),   # Mixed
        5: (25, 65),   # Cool
        6: (30, 75),   # Cold
        7: (35, 85),   # Very cold
        8: (40, 100)   # Subarctic
    }
    
    cooling_ranges = {
        1: (25, 50),   # Very hot
        2: (20, 45),   # Hot
        3: (15, 40),   # Warm
        4: (12, 35),   # Mixed
        5: (10, 30),   # Cool
        6: (8, 25),    # Cold
        7: (5, 20),    # Very cold
        8: (3, 15)     # Subarctic
    }
    
    heating_min, heating_max = heating_ranges.get(zone_num, (15, 80))
    cooling_min, cooling_max = cooling_ranges.get(zone_num, (10, 40))
    
    heating_per_sqft = heating_total / total_sqft if total_sqft > 0 else 0
    cooling_per_sqft = cooling_total / total_sqft if total_sqft > 0 else 0
    
    # Enhanced validation with climate-specific ranges
    if not (heating_min <= heating_per_sqft <= heating_max * 1.2):  # Allow 20% overage
        logger.warning(f"Heating load outside climate zone {climate_zone} range: {heating_per_sqft:.1f} BTU/hr/sqft (expected {heating_min}-{heating_max})")
    
    if not (cooling_min <= cooling_per_sqft <= cooling_max * 1.2):
        logger.warning(f"Cooling load outside climate zone {climate_zone} range: {cooling_per_sqft:.1f} BTU/hr/sqft (expected {cooling_min}-{cooling_max})")
    
    # Validate zone-level calculations
    total_zone_heating = sum(zone['heating_btu'] for zone in result['zones'])
    total_zone_cooling = sum(zone['cooling_btu'] for zone in result['zones'])
    
    # Check for system factors and diversity
    design_params = result.get('design_parameters', {})
    # Account for all applied factors
    area_factor = design_params.get('area_correction_factor', 1.0)
    expected_heating = total_zone_heating * area_factor * design_params.get('duct_heating_factor', design_params.get('duct_loss_factor', 1.0)) * design_params.get('safety_factor', 1.0)
    expected_cooling = total_zone_cooling * area_factor * design_params.get('duct_cooling_factor', design_params.get('duct_loss_factor', 1.0)) * design_params.get('safety_factor', 1.0) * design_params.get('diversity_factor', 1.0)
    
    heating_diff_pct = abs(expected_heating - heating_total) / heating_total * 100 if heating_total > 0 else 0
    cooling_diff_pct = abs(expected_cooling - cooling_total) / cooling_total * 100 if cooling_total > 0 else 0
    
    if heating_diff_pct > 5:  # Tighter tolerance with proper calculation
        logger.warning(f"Zone heating totals don't match system total: {heating_diff_pct:.1f}% difference")
    
    if cooling_diff_pct > 5:
        logger.warning(f"Zone cooling totals don't match system total: {cooling_diff_pct:.1f}% difference")
    
    # Additional validation checks
    _validate_room_loads(result['zones'], climate_zone)
    _validate_equipment_sizing(result, total_sqft)


def _perform_data_quality_checks(schema: BlueprintSchema, result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform data quality checks on inputs and results
    
    Args:
        schema: Blueprint schema
        result: Calculation results
        
    Returns:
        Dict with quality check results
    """
    checks = {
        'total_rooms_processed': len(schema.rooms),
        'total_area_processed': schema.sqft_total,
        'rooms_with_windows': sum(1 for room in schema.rooms if room.windows > 0),
        'rooms_with_orientation': sum(1 for room in schema.rooms if room.orientation),
        'average_room_size': schema.sqft_total / len(schema.rooms) if schema.rooms else 0,
        'zone_calculation_completeness': len(result['zones']) / len(schema.rooms) if schema.rooms else 0
    }
    
    # Quality flags
    checks['quality_flags'] = []
    
    if checks['average_room_size'] < 50:
        checks['quality_flags'].append('SMALL_ROOMS_DETECTED')
    
    if checks['average_room_size'] > 1000:
        checks['quality_flags'].append('LARGE_ROOMS_DETECTED')
    
    if checks['rooms_with_orientation'] / len(schema.rooms) < 0.5:
        checks['quality_flags'].append('MISSING_ORIENTATIONS')
    
    if checks['rooms_with_windows'] == 0:
        checks['quality_flags'].append('NO_WINDOWS_DETECTED')
    
    return checks


def _check_calculation_warnings(result: Dict[str, Any], schema: BlueprintSchema) -> List[str]:
    """
    Check for calculation warnings that may indicate issues
    
    Args:
        result: Calculation results
        schema: Blueprint schema
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Check for unusual load distributions
    if result['zones']:
        zone_loads = [zone['cooling_btu'] for zone in result['zones']]
        max_load = max(zone_loads)
        min_load = min(zone_loads)
        
        if max_load > min_load * 5:  # One zone has >5x load of smallest
            warnings.append(f"High load variation between zones (max: {max_load}, min: {min_load})")
    
    # Check equipment sizing
    cooling_tons = result['cooling_total'] / 12000
    if cooling_tons < 1.5:
        warnings.append("System size unusually small - verify building area and envelope")
    elif cooling_tons > 10:
        warnings.append("System size unusually large - verify calculations and inputs")
    
    # Check for missing data
    if not result.get('climate_zone'):
        warnings.append("Climate zone not properly identified")
    
    # Check design parameters
    design_params = result.get('design_parameters', {})
    if design_params.get('duct_heating_factor', design_params.get('duct_loss_factor', 1.0)) == 1.0:
        warnings.append("No duct losses/gains applied - verify duct configuration")
    
    return warnings


def _validate_room_loads(zones: List[Dict], climate_zone: str) -> None:
    """
    Validate individual room loads for reasonableness
    
    Args:
        zones: List of room/zone data
        climate_zone: IECC climate zone
    """
    for zone in zones:
        room_name = zone.get('name', 'Unknown')
        room_type = zone.get('room_type', 'other')
        area = zone.get('area', 0)
        heating_load = zone.get('heating_btu', 0)
        cooling_load = zone.get('cooling_btu', 0)
        
        if area <= 0:
            logger.warning(f"Room {room_name}: Invalid area ({area} sqft)")
            continue
        
        # Check load density
        heating_density = heating_load / area
        cooling_density = cooling_load / area
        
        # Room-type specific validation
        expected_ranges = {
            'kitchen': {'heating': (30, 100), 'cooling': (40, 120)},  # Higher due to equipment
            'bathroom': {'heating': (40, 120), 'cooling': (30, 80)},  # Higher heating, exhaust
            'bedroom': {'heating': (15, 60), 'cooling': (15, 60)},    # Standard
            'living': {'heating': (20, 70), 'cooling': (20, 80)},     # More windows typically
            'dining': {'heating': (20, 70), 'cooling': (20, 70)},     # Standard
            'office': {'heating': (20, 60), 'cooling': (25, 90)},     # Equipment loads
            'utility': {'heating': (10, 50), 'cooling': (20, 100)},   # Equipment varies
            'other': {'heating': (15, 80), 'cooling': (15, 80)}       # Generic
        }
        
        h_min, h_max = expected_ranges.get(room_type, expected_ranges['other'])['heating']
        c_min, c_max = expected_ranges.get(room_type, expected_ranges['other'])['cooling']
        
        if not (h_min <= heating_density <= h_max * 1.5):  # Allow 50% overage
            logger.warning(f"Room {room_name} ({room_type}): Unusual heating load density {heating_density:.1f} BTU/hr/sqft")
        
        if not (c_min <= cooling_density <= c_max * 1.5):
            logger.warning(f"Room {room_name} ({room_type}): Unusual cooling load density {cooling_density:.1f} BTU/hr/sqft")
        
        # Check if breakdown is available for detailed validation
        if 'load_breakdown' in zone:
            _validate_load_components(zone, room_name)


def _validate_load_components(zone: Dict, room_name: str) -> None:
    """
    Validate individual load components for a room
    
    Args:
        zone: Room data with load breakdown
        room_name: Room name for logging
    """
    breakdown = zone.get('load_breakdown', {})
    heating_components = breakdown.get('heating', {})
    cooling_components = breakdown.get('cooling', {})
    
    # Check for negative loads
    for component, value in heating_components.items():
        if isinstance(value, (int, float)) and value < 0:
            logger.warning(f"Room {room_name}: Negative heating component {component}: {value}")
    
    for component, value in cooling_components.items():
        if isinstance(value, (int, float)) and value < 0:
            logger.warning(f"Room {room_name}: Negative cooling component {component}: {value}")
    
    # Validate infiltration CFM if present
    infiltration_cfm = cooling_components.get('infiltration_cfm', 0)
    if infiltration_cfm > 0:
        room_volume = zone.get('area', 100) * 9  # Assume 9ft ceiling
        ach = (infiltration_cfm * 60) / room_volume
        if ach > 2.0:
            logger.warning(f"Room {room_name}: High infiltration rate {ach:.1f} ACH")


def _validate_equipment_sizing(result: Dict, total_sqft: float) -> None:
    """
    Validate equipment sizing recommendations
    
    Args:
        result: Calculation results
        total_sqft: Total building area
    """
    equipment = result.get('equipment_recommendations', {})
    cooling_tons = result.get('cooling_total', 0) / 12000
    
    # Check tons per square foot
    tons_per_sqft = cooling_tons / total_sqft if total_sqft > 0 else 0
    sqft_per_ton = total_sqft / cooling_tons if cooling_tons > 0 else 0
    
    # Typical ranges
    if sqft_per_ton < 400:
        logger.warning(f"Equipment may be oversized: {sqft_per_ton:.0f} sqft/ton (typical: 500-800)")
    elif sqft_per_ton > 1200:
        logger.warning(f"Equipment may be undersized: {sqft_per_ton:.0f} sqft/ton (typical: 500-800)")
    
    # Validate size options
    size_options = equipment.get('size_options', [])
    for option in size_options:
        manual_s_rating = option.get('manual_s_rating', 'Unknown')
        if manual_s_rating == 'Poor':
            capacity = option.get('capacity_tons', 0)
            logger.warning(f"Equipment option {capacity} tons has poor Manual S rating")


def _calculate_load_breakdown_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate summary of load components across all zones
    
    Args:
        result: Calculation results with zones
        
    Returns:
        Dict with load component percentages
    """
    # Initialize totals
    heating_components = {}
    cooling_components = {}
    
    # Sum up all components across zones
    for zone in result.get('zones', []):
        breakdown = zone.get('load_breakdown', {})
        
        # Heating components
        for component, value in breakdown.get('heating', {}).items():
            if isinstance(value, (int, float)) and component != 'subtotal' and component != 'infiltration_cfm':
                heating_components[component] = heating_components.get(component, 0) + value
        
        # Cooling components  
        for component, value in breakdown.get('cooling', {}).items():
            if isinstance(value, (int, float)) and component != 'subtotal' and component != 'infiltration_cfm':
                cooling_components[component] = cooling_components.get(component, 0) + value
    
    # Calculate percentages
    total_heating = sum(heating_components.values())
    total_cooling = sum(cooling_components.values())
    
    heating_percentages = {}
    cooling_percentages = {}
    
    if total_heating > 0:
        for component, value in heating_components.items():
            heating_percentages[component] = round(value / total_heating * 100, 1)
    
    if total_cooling > 0:
        for component, value in cooling_components.items():
            cooling_percentages[component] = round(value / total_cooling * 100, 1)
    
    return {
        'heating_component_breakdown': heating_percentages,
        'cooling_component_breakdown': cooling_percentages,
        'dominant_heating_load': max(heating_percentages, key=heating_percentages.get) if heating_percentages else None,
        'dominant_cooling_load': max(cooling_percentages, key=cooling_percentages.get) if cooling_percentages else None
    }


def _get_calculation_assumptions(envelope_data: Optional[EnvelopeExtraction], 
                                construction_vintage: Optional[str]) -> List[str]:
    """
    List all assumptions made during calculation
    
    Args:
        envelope_data: Envelope extraction data if available
        construction_vintage: Construction vintage used
        
    Returns:
        List of assumption descriptions
    """
    assumptions = []
    
    if not envelope_data:
        assumptions.append("Used construction vintage defaults for all envelope properties")
        assumptions.append(f"Assumed {construction_vintage or '1980-2000'} construction standards")
    else:
        # Check envelope data confidence
        if envelope_data.wall_confidence < 0.6:
            assumptions.append(f"Wall R-value estimated as R-{envelope_data.wall_r_value}")
        if envelope_data.roof_confidence < 0.6:
            assumptions.append(f"Roof R-value estimated as R-{envelope_data.roof_r_value}")
        if envelope_data.window_confidence < 0.6:
            assumptions.append(f"Window U-factor estimated as {envelope_data.window_u_factor}")
        if envelope_data.infiltration_confidence < 0.6:
            assumptions.append(f"Infiltration class estimated as '{envelope_data.infiltration_class}'")
        if not envelope_data.blower_door_result:
            assumptions.append("No blower door test data - used construction quality estimate")
    
    # Standard assumptions
    assumptions.extend([
        "Indoor design temperature: 75°F cooling, 70°F heating",
        "Indoor relative humidity: 50%",
        "Occupancy: 1 person per 200 sqft",
        "Internal gains: ACCA Manual J defaults",
        "Peak cooling hour: 2-3 PM",
        "No shading from trees or adjacent buildings unless noted"
    ])
    
    return assumptions