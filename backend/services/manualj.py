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
from .envelope_extractor import EnvelopeExtraction
from .audit_tracker import get_audit_tracker, create_calculation_audit
import math


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
    "living": {"heating": 1.2, "cooling": 1.3},  # High activity, large windows
    "bedroom": {"heating": 0.9, "cooling": 1.0}, # Lower activity
    "kitchen": {"heating": 1.1, "cooling": 1.4}, # Heat gain from appliances
    "bathroom": {"heating": 1.3, "cooling": 1.1}, # High moisture, heating needs
    "dining": {"heating": 1.0, "cooling": 1.1},
    "office": {"heating": 0.9, "cooling": 1.2},   # Equipment heat gain
    "utility": {"heating": 0.8, "cooling": 1.3},  # Equipment heat gain
    "other": {"heating": 1.0, "cooling": 1.0}
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
    
    # Estimate building envelope areas (simplified - would be better from actual blueprints)
    # Assume room is rectangular with typical proportions
    room_width = math.sqrt(room.area * 0.75)  # Assume 4:3 aspect ratio
    room_length = room.area / room_width
    
    # Calculate envelope areas
    wall_area = 2 * (room_width + room_length) * ceiling_height
    
    # Subtract door area (assume one door per room)
    door_area = 7 * 3  # 7ft x 3ft door
    wall_area -= door_area
    
    # Calculate window area
    window_area = room.windows * 12.0  # Assume 3x4 ft windows
    wall_area -= window_area
    
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
    
    # 1. Wall conduction load
    if wall_area > 0:
        wall_load = calculate_wall_load_cltd(
            wall_area, wall_u_factor, wall_type, room.orientation,
            outdoor_cooling_temp, indoor_temp
        )
        cooling_load += wall_load
    
    # 2. Roof conduction load
    if roof_area > 0:
        roof_load = calculate_roof_load_cltd(
            roof_area, roof_u_factor, roof_type,
            outdoor_cooling_temp, indoor_temp
        )
        cooling_load += roof_load
    
    # 3. Window conduction load
    if window_area > 0:
        window_conduction = calculate_window_conduction_load(
            window_area, window_u_factor, outdoor_cooling_temp, indoor_temp
        )
        cooling_load += window_conduction
    
    # 4. Window solar load
    if window_area > 0:
        solar_load = calculate_window_solar_load(
            window_area, window_shgc, room.orientation
        )
        cooling_load += solar_load
    
    # 5. Internal loads with CLF
    # People load (assume 1 person per 200 sq ft)
    people_count = max(1, room.area / 200)
    people_load = calculate_internal_load_clf(people_count * 250, 'people')  # 250 BTU/hr per person sensible
    cooling_load += people_load
    
    # Lighting load (assume 2 W/sq ft)
    lighting_load = calculate_internal_load_clf(room.area * 2 * 3.41, 'lighting')  # Convert W to BTU/hr
    cooling_load += lighting_load
    
    # Equipment load varies by room type
    equipment_loads = {
        'kitchen': room.area * 5.0,  # High equipment load
        'office': room.area * 3.0,   # Computer equipment
        'living': room.area * 1.5,   # TV, electronics
        'bedroom': room.area * 1.0,  # Minimal equipment
        'bathroom': room.area * 2.0, # Exhaust fans, lighting
        'other': room.area * 1.0
    }
    equipment_heat = equipment_loads.get(room_type, equipment_loads['other'])
    equipment_load = calculate_internal_load_clf(equipment_heat, 'equipment')
    cooling_load += equipment_load
    
    # 6. Ventilation load (ASHRAE 62.2)
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
    
    # Wall conduction
    if wall_area > 0:
        heating_load += wall_u_factor * wall_area * (indoor_temp - outdoor_heating_temp)
    
    # Roof conduction
    if roof_area > 0:
        heating_load += roof_u_factor * roof_area * (indoor_temp - outdoor_heating_temp)
    
    # Window conduction
    if window_area > 0:
        heating_load += window_u_factor * window_area * (indoor_temp - outdoor_heating_temp)
    
    # Infiltration heating load - use envelope data if available
    if envelope_data and envelope_data.infiltration_confidence >= 0.6:
        # Map infiltration class to ACH
        infiltration_class_to_ach = {
            "tight": 0.25,
            "code": 0.35,
            "loose": 0.50
        }
        ach = infiltration_class_to_ach.get(envelope_data.infiltration_class, 0.35)
    else:
        ach = construction_values['infiltration_ach']
    
    room_volume = room.area * ceiling_height
    infiltration_cfm = (room_volume * ach) / 60
    infiltration_heating = infiltration_cfm * 1.08 * (indoor_temp - outdoor_heating_temp)
    heating_load += infiltration_heating
    
    # Add ventilation heating load
    heating_load += ventilation['heating']
    
    return {
        'heating': max(heating_load, 0),
        'cooling': max(cooling_load, 0)
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
    
    # Apply window factors
    window_factor = 1.0 + (room.windows * 0.15)
    heating_mult *= window_factor
    cooling_mult *= window_factor * 1.2
    
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
    # Get climate data from comprehensive database
    climate_data = get_climate_data(schema.zip_code)
    
    # Get climate zone factors
    climate_factors = get_climate_zone_factors(climate_data['climate_zone'])
    
    # Get construction values if vintage specified
    construction_values = None
    if construction_vintage:
        construction_values = get_construction_vintage_values(construction_vintage)
    
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
    
    for room in schema.rooms:
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
        
        zones.append({
            "name": room.name,
            "area": room.area,
            "room_type": room_type,
            "floor": room.floor,
            "heating_btu": round(room_heating),
            "cooling_btu": round(room_cooling),
            "cfm_required": _calculate_airflow(room_cooling),
            "duct_size": _calculate_duct_size(room_cooling),
            "calculation_method": calculation_method
        })
        
        total_heating += room_heating
        total_cooling += room_cooling
    
    # Apply Manual J diversity factor to prevent oversizing
    diversity_factor = get_diversity_factor(len(schema.rooms))
    total_cooling *= diversity_factor
    
    # Apply system factors
    # Duct losses based on configuration
    if duct_config == "ductless":
        duct_loss_factor = 1.0  # No duct losses for ductless systems
    elif duct_config == "ducted_crawl":
        duct_loss_factor = 1.10  # Lower losses in conditioned crawl space
    else:  # ducted_attic
        duct_loss_factor = 1.15  # Higher losses in unconditioned attic
    
    total_heating *= duct_loss_factor
    total_cooling *= duct_loss_factor
    
    # Safety factor
    safety_factor = 1.1
    total_heating *= safety_factor
    total_cooling *= safety_factor
    
    # Equipment sizing recommendations
    equipment = _recommend_equipment(total_heating, total_cooling, schema.sqft_total, heating_fuel)
    
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
            "duct_loss_factor": duct_loss_factor,
            "safety_factor": safety_factor,
            "diversity_factor": diversity_factor,
            "construction_vintage": construction_vintage,
            "calculation_method": calculation_method,
            "include_ventilation": include_ventilation,
            "construction_values": construction_values
        }
    }
    
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
    """Recommend HVAC equipment based on loads and fuel type"""
    
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
    
    # Size recommendations with Manual S match ratings
    size_options = []
    available_sizes = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
    
    for size in available_sizes:
        if size >= cooling_tons * 0.85 and size <= cooling_tons * 1.3:  # Broader range for options
            # Get Manual S match rating
            match_rating = _get_equipment_match_rating(size, cooling_tons)
            
            efficiency = "Standard" if size <= cooling_tons * 1.1 else "High Efficiency"
            size_options.append({
                "capacity_tons": size,
                "capacity_btu": size * 12000,
                "efficiency_rating": efficiency,
                "estimated_cost": f"${size * 2500:.0f} - ${size * 4000:.0f}",
                "manual_s_rating": match_rating["rating"],
                "manual_s_explanation": match_rating["explanation"],
                "recommended": match_rating["rating"] == "Good"
            })
    
    return {
        "system_type": system_type,
        "recommended_size_tons": round(cooling_tons, 1),
        "size_options": size_options[:3],  # Top 3 options
        "ductwork_recommendation": _recommend_ductwork(total_sqft),
        "estimated_install_time": f"{max(1, round(cooling_tons))} - {max(2, round(cooling_tons) + 1)} days"
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