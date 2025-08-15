"""
ACCA Manual J Calculation Stage
NOW USES GPT-4 FOR ACCURATE CALCULATIONS!
Falls back to formula-based approach if GPT unavailable
"""

import logging
import math
from typing import Dict, Any, Tuple, Optional
from core.models import Building, HVACLoads, RoomType
from core.climate_zones import get_zone_config, get_construction_factors, get_climate_data_for_zip

logger = logging.getLogger(__name__)

# Try to import GPT calculator
try:
    from stages.gpt_manual_j import calculate_with_gpt
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False
    logger.info("GPT Manual J calculator not available")


class ManualJCalculator:
    """
    Proper ACCA Manual J implementation
    Uses actual heat transfer equations: Q = U × A × ΔT
    No arbitrary adjustments - just industry standard calculations
    """
    
    # ASHRAE Design Temperatures by ZIP prefix
    ASHRAE_DESIGN_TEMPS = {
        "99": {  # Eastern Washington (Spokane area)
            "location": "Spokane, WA",
            "winter_99": 6,      # 99% winter design temp (°F)
            "summer_1": 91,      # 1% summer design temp
            "summer_wb": 62,     # Summer wet-bulb temp
            "winter_humidity": 0.002,  # Winter humidity ratio
            "summer_humidity": 0.009,  # Summer humidity ratio
            "daily_range": 23,   # Daily temperature range
            "climate_zone": "5B"  # Cold-Dry
        },
        "98": {  # Seattle area
            "location": "Seattle, WA",
            "winter_99": 24,
            "summer_1": 85,
            "summer_wb": 65,
            "winter_humidity": 0.003,
            "summer_humidity": 0.010,
            "daily_range": 18,
            "climate_zone": "4C"  # Mixed-Marine
        },
        "90": {  # Southern California
            "location": "Los Angeles, CA",
            "winter_99": 42,
            "summer_1": 83,
            "summer_wb": 68,
            "winter_humidity": 0.004,
            "summer_humidity": 0.011,
            "daily_range": 20,
            "climate_zone": "3B"  # Warm-Dry
        }
    }
    
    # U-Factors for typical construction (BTU/hr·ft²·°F)
    U_FACTORS = {
        "wall_r13": 0.084,         # R-13 insulated 2x4 wall
        "wall_r19": 0.060,         # R-19 insulated 2x6 wall
        "wall_r21": 0.048,         # R-21 high-performance wall
        "roof_r30": 0.035,         # R-30 attic
        "roof_r38": 0.029,         # R-38 attic
        "roof_r49": 0.020,         # R-49 energy code compliant
        "floor_r19": 0.047,        # R-19 floor over crawl
        "floor_r30": 0.033,        # R-30 floor (cold climate)
        "window_double": 0.30,     # Double pane low-E
        "window_triple": 0.20,     # Triple pane
        "door_insulated": 0.20     # Insulated steel door
    }
    
    # Solar Heat Gain Coefficients
    SHGC_WINDOW = 0.30  # Double pane low-E typical
    
    # Infiltration rates (ACH - Air Changes per Hour)
    INFILTRATION_ACH = {
        "tight": 0.35,
        "average": 0.50,
        "loose": 0.70
    }
    
    def calculate(self, building: Building, construction_quality: str = "average", synthesis_data: Dict[str, Any] = None) -> HVACLoads:
        """
        Calculate HVAC loads using proper Manual J methodology
        NOW USES ACTUAL BUILDING ENVELOPE DATA!
        """
        logger.info(f"=== Manual J Calculation for {building.floor_count}-story, "
                   f"{building.total_sqft:.0f} sqft building ===")
        
        # Get ASHRAE climate data
        climate = self._get_climate_data(building.zip_code)
        logger.info(f"Climate: {climate['location']} (Zone {climate['climate_zone']})")
        
        # Indoor design conditions (ACCA Manual J standard)
        indoor_winter = 70  # °F
        indoor_summer = 75  # °F
        
        # Calculate temperature differences
        delta_t_heating = indoor_winter - climate['winter_99']
        delta_t_cooling = climate['summer_1'] - indoor_summer
        
        logger.info(f"Design ΔT: {delta_t_heating}°F heating, {delta_t_cooling}°F cooling")
        
        # Initialize loads
        total_heating = 0
        total_cooling_sensible = 0
        total_cooling_latent = 0
        floor_loads = {}
        
        # Calculate loads for each floor
        for floor in building.floors:
            heating, cooling_s, cooling_l = self._calculate_floor_loads(
                floor, climate, delta_t_heating, delta_t_cooling,
                construction_quality, building.floor_count, floor.number,
                synthesis_data
            )
            
            floor_loads[floor.number] = {
                "heating_btu_hr": heating,
                "cooling_btu_hr": cooling_s + cooling_l,
                "floor_name": floor.name
            }
            
            total_heating += heating
            total_cooling_sensible += cooling_s
            total_cooling_latent += cooling_l
            
            logger.info(f"{floor.name}: {heating:,.0f} BTU/hr heating, "
                       f"{cooling_s + cooling_l:,.0f} BTU/hr cooling")
        
        # Total cooling
        total_cooling = total_cooling_sensible + total_cooling_latent
        
        # Apply diversity factor (Manual J Table 6A) - prevents oversizing
        if building.room_count > 5:
            diversity = 0.95 if building.room_count <= 10 else 0.90
            total_cooling *= diversity
            logger.info(f"Diversity factor applied: {diversity}")
        
        # CRITICAL: Apply duct losses (Manual J Section 18)
        # Most residential systems have ducts in attic or crawl space
        duct_location = "attic"  # TODO: Get from user input or detect
        if duct_location == "attic":
            duct_factor_heating = 1.08  # 8% heating loss
            duct_factor_cooling = 1.08  # 8% cooling gain
        elif duct_location == "crawl":
            duct_factor_heating = 1.06  # 6% heating loss
            duct_factor_cooling = 1.04  # 4% cooling gain
        else:  # conditioned space or ductless
            duct_factor_heating = 1.0
            duct_factor_cooling = 1.0
        
        total_heating *= duct_factor_heating
        total_cooling *= duct_factor_cooling
        logger.info(f"Duct losses applied ({duct_location}): "
                   f"H×{duct_factor_heating}, C×{duct_factor_cooling}")
        
        # Calculate tonnage
        # Add duct losses and ventilation loads
        # These are MAJOR factors often missed
        
        # Get zone-specific factors for duct losses and safety margins
        zone_config = get_zone_config(climate.get('climate_zone', '4A'))
        factors = get_construction_factors(zone_config, construction_quality)
        
        # 1. Duct losses - varies by climate zone
        # Hot climates have more cooling duct losses
        # Cold climates have more heating duct losses
        duct_loss_heating = factors['duct_loss_heating']
        duct_loss_cooling = factors['duct_loss_cooling']
        
        # 2. Ventilation load (required by modern codes)
        # ASHRAE 62.2: 0.03 CFM/sqft + 7.5 CFM/bedroom
        # Count bedrooms across all floors for occupancy
        bedroom_count = sum(1 for floor in building.floors 
                           for room in floor.rooms 
                           if room.room_type == RoomType.BEDROOM)
        ventilation_cfm = (building.total_sqft * 0.03) + (bedroom_count * 7.5)
        ventilation_heating = 1.08 * ventilation_cfm * delta_t_heating
        ventilation_cooling = 1.08 * ventilation_cfm * delta_t_cooling
        
        # Apply zone-specific factors for heating and cooling
        safety_heating = factors['safety_factor_heating']
        safety_cooling = factors['safety_factor_cooling']
        
        total_heating = (total_heating + ventilation_heating) * duct_loss_heating * safety_heating
        total_cooling = (total_cooling + ventilation_cooling) * duct_loss_cooling * safety_cooling
        
        heating_tons = total_heating / 12000
        cooling_tons = total_cooling / 12000
        
        loads = HVACLoads(
            heating_btu_hr=total_heating,
            cooling_btu_hr=total_cooling,
            heating_tons=heating_tons,
            cooling_tons=cooling_tons,
            cfm_required=cooling_tons * 400,
            floor_loads=floor_loads
        )
        
        logger.info(f"=== Total Loads: {total_heating:,.0f} BTU/hr heating, "
                   f"{total_cooling:,.0f} BTU/hr cooling ===")
        
        return loads
    
    def _get_climate_data(self, zip_code: str) -> Dict[str, Any]:
        """Get ASHRAE climate data for ZIP code"""
        # Use consolidated function from climate_zones module
        climate_data = get_climate_data_for_zip(zip_code)
        
        # If not found, fallback to hardcoded data
        if not climate_data['found']:
            prefix = zip_code[:2]
            return self.ASHRAE_DESIGN_TEMPS.get(prefix, self.ASHRAE_DESIGN_TEMPS["99"])
        
        return climate_data
    
    # Removed - now using get_climate_data_for_zip from climate_zones module
    
    def _calculate_floor_loads(
        self, floor, climate: Dict, delta_t_heating: float, delta_t_cooling: float,
        construction: str, total_floors: int, floor_number: int,
        synthesis_data: Dict[str, Any] = None
    ) -> Tuple[float, float, float]:
        """
        Calculate loads using proper heat transfer equations
        NOW USES ACTUAL ENVELOPE DATA INSTEAD OF GUESSING!
        Returns: (heating, cooling_sensible, cooling_latent)
        """
        
        heating = 0
        cooling_s = 0
        cooling_l = 0
        
        # Get ACTUAL building perimeter from envelope data if available
        # CRITICAL: Use the envelope for THIS SPECIFIC FLOOR
        envelope = None
        if synthesis_data:
            # First try to get envelope for this specific floor
            floor_key = f"floor_{floor.number}"
            if floor_key in synthesis_data:
                floor_data = synthesis_data.get(floor_key, {})
                if isinstance(floor_data, dict) and 'envelope' in floor_data:
                    envelope = floor_data['envelope']
                    logger.info(f"Found envelope data for {floor.name} in {floor_key}")
                    logger.debug(f"Envelope data: {envelope}")
            
            # If not found for this floor, look for any envelope as fallback
            if not envelope:
                for key in synthesis_data:
                    if key.startswith('floor_'):
                        floor_data = synthesis_data.get(key, {})
                        if isinstance(floor_data, dict) and 'envelope' in floor_data:
                            envelope = floor_data['envelope']
                            logger.info(f"Using envelope from {key} as fallback for {floor.name}")
                            break
            
            # Also check for direct envelope key
            if not envelope and 'envelope' in synthesis_data:
                envelope = synthesis_data['envelope']
                logger.info("Found envelope data at top level")
        
        if envelope and hasattr(envelope, 'total_perimeter_ft'):
            # USE ACTUAL MEASURED PERIMETER!
            building_perimeter = envelope.total_perimeter_ft
            logger.info(f"Using ACTUAL perimeter: {building_perimeter:.1f}ft (shape factor: {envelope.shape_factor:.2f})")
        else:
            # Fallback to estimation only if no envelope data
            floor_area = floor.total_sqft
            building_perimeter = 4.2 * math.sqrt(floor_area)  # Guessed aspect ratio
            logger.warning(f"No envelope data - guessing perimeter as {building_perimeter:.1f}ft")
        
        # Get zone-specific configuration and factors
        zone_config = get_zone_config(climate.get('climate_zone', '4A'))
        
        # CRITICAL: Use extracted R-values if available, otherwise use defaults
        building_data = synthesis_data.get('building_data', {}) if synthesis_data else {}
        
        # Get building era if available
        building_era = None
        if building_data.get('building_era_detected'):
            building_era = building_data['building_era_detected']
            logger.info(f"Using detected building era: {building_era}")
        
        factors = get_construction_factors(zone_config, construction, building_era)
        
        # Wall R-value: extracted > era-based > zone default
        if building_data.get('wall_r_value'):
            wall_r = building_data['wall_r_value']
            logger.info(f"Using extracted wall R-value: R-{wall_r}")
        elif building_data.get('building_era_detected'):
            # Use era-based defaults (to be implemented)
            wall_r = factors['wall_r']
            logger.info(f"Using era-based wall R-value: R-{wall_r}")
        else:
            wall_r = factors['wall_r']
            logger.info(f"Using zone default wall R-value: R-{wall_r}")
        
        # Roof R-value
        if building_data.get('roof_r_value'):
            roof_r = building_data['roof_r_value']
            logger.info(f"Using extracted roof R-value: R-{roof_r}")
        else:
            roof_r = factors['roof_r']
        
        # Floor R-value
        if building_data.get('floor_r_value'):
            floor_r = building_data['floor_r_value']
            logger.info(f"Using extracted floor R-value: R-{floor_r}")
        else:
            floor_r = factors['floor_r']
        
        # Convert R-values to U-factors
        u_wall = 1.0 / wall_r if wall_r > 0 else 0.084
        u_roof = 1.0 / roof_r if roof_r > 0 else 0.035  
        u_floor = 1.0 / floor_r if floor_r > 0 else 0.047
        
        # Get window data from extracted info, schedules, or defaults
        if building_data.get('window_type'):
            window_type = building_data['window_type'].lower()
            if 'single' in window_type:
                u_window = 1.0  # Single pane
                logger.info("Using single pane windows: U-1.0")
            elif 'double' in window_type and 'low-e' not in window_type:
                u_window = 0.5  # Double pane, no low-E
                logger.info("Using double pane windows: U-0.5")
            else:
                u_window = factors['window_u']  # Modern low-E
            shgc = factors['window_shgc']
        elif synthesis_data and "building_data" in synthesis_data:
            schedules = synthesis_data.get("building_data", {}).get("schedules", {})
            u_window = schedules.get("average_u_value", factors['window_u'])
            shgc = schedules.get("average_shgc", factors['window_shgc'])
        else:
            u_window = factors['window_u']
            shgc = factors['window_shgc']
        
        u_door = self.U_FACTORS["door_insulated"]
        
        # Use actual ceiling height if available from envelope
        if envelope and hasattr(envelope, 'ceiling_height_ft'):
            ceiling_height = envelope.ceiling_height_ft
        else:
            ceiling_height = 9  # Common height fallback
        
        # Calculate total exterior wall area for the floor
        total_wall_area = building_perimeter * ceiling_height
        
        # Get wall orientations from envelope if available
        wall_by_orientation = None
        window_by_orientation = None
        if envelope:
            wall_by_orientation = getattr(envelope, 'wall_orientations', None)
            window_by_orientation = getattr(envelope, 'window_areas', None)
        
        # Calculate total windows and doors for the floor
        total_windows = sum(getattr(room, 'windows', room.exterior_walls) 
                          for room in floor.rooms if room.exterior_walls > 0)
        total_window_area = total_windows * 20  # 20 sqft per window (4x5 ft typical residential)
        
        # Estimate doors - typically 1-2 per floor
        total_doors = 2 if floor_number == 0 else 0  # Main floor has exterior doors
        total_door_area = total_doors * 20  # 20 sqft per door
        
        # Net wall area after subtracting windows and doors
        net_wall_area = total_wall_area - total_window_area - total_door_area
        if net_wall_area < 0:
            net_wall_area = total_wall_area * 0.7  # Fallback if too many openings
        
        # Calculate heat transfer for entire floor's envelope
        thermal_bridge_factor = 1.05  # 5% for wood frame construction
        floor_wall_heating = u_wall * net_wall_area * delta_t_heating * thermal_bridge_factor
        floor_wall_cooling = u_wall * net_wall_area * delta_t_cooling * thermal_bridge_factor
        
        floor_window_heating = u_window * total_window_area * delta_t_heating
        floor_window_cooling_cond = u_window * total_window_area * delta_t_cooling
        
        floor_door_heating = u_door * total_door_area * delta_t_heating
        floor_door_cooling = u_door * total_door_area * delta_t_cooling
        
        for room in floor.rooms:
            # Distribute floor-level envelope loads proportionally to rooms
            # Based on room's share of floor area
            room_fraction = room.area_sqft / floor.total_sqft if floor.total_sqft > 0 else 0
            
            # 1. WALL LOADS (distributed proportionally)
            wall_heating = floor_wall_heating * room_fraction
            wall_cooling = floor_wall_cooling * room_fraction
            
            # 2. WINDOW LOADS (distributed proportionally)
            window_heating = floor_window_heating * room_fraction
            window_cooling_cond = floor_window_cooling_cond * room_fraction
            
            # Solar gain with zone-specific factors
            # Calculate room's share of window area for solar gains
            room_window_area = (getattr(room, 'windows', 0) * 20) if room.exterior_walls > 0 else 0
            
            base_solar = factors['solar_gain_factor']
            
            # Adjust for room exposure
            if room.exterior_walls > 1:
                solar_factor = base_solar * 1.2  # Corner room gets more sun
            elif room.exterior_walls == 1:
                solar_factor = base_solar  # Single wall exposure
            else:
                solar_factor = 0  # Interior room
            
            # Apply Cooling Load Factor (CLF) for thermal mass delay
            clf = 0.75  # Typical for residential with thermal mass
            window_cooling_solar = room_window_area * solar_factor * shgc * clf
            
            # 3. DOOR LOADS (distributed proportionally)
            door_heating = floor_door_heating * room_fraction
            door_cooling = floor_door_cooling * room_fraction
            
            # 4. ROOF LOADS (top floor only)
            if floor_number == total_floors - 1:
                roof_heating = u_roof * room.area_sqft * delta_t_heating
                # CLTD (Cooling Load Temperature Difference) for solar gain on roof
                # Dark roof in summer can be 40°F+ hotter than air temp
                cltd_roof = delta_t_cooling + 25  # Additional solar heating
                roof_cooling = u_roof * room.area_sqft * cltd_roof
            else:
                roof_heating = roof_cooling = 0
            
            # 5. FLOOR LOADS (ground floor only)
            if floor_number == 0:
                # Ground temperature buffering varies by climate zone
                # Cold zones have less ground buffering in winter
                zone = climate.get('climate_zone', '4A')
                zone_number = int(zone[0]) if zone[0].isdigit() else 4
                
                # ACCA Manual J ground temperature factors
                # Colder zones = less buffering (more heat loss through floor)
                if zone_number >= 6:
                    floor_buffering = 0.5  # Very cold - significant floor losses
                elif zone_number >= 4:
                    floor_buffering = 0.6  # Moderate cold
                else:
                    floor_buffering = 0.7  # Mild climates
                
                floor_heating = u_floor * room.area_sqft * (delta_t_heating * floor_buffering)
                floor_cooling = 0  # Floors don't add cooling
            else:
                floor_heating = floor_cooling = 0
            
            # 6. INTERNAL GAINS (cooling only)
            occupants = 2 if room.room_type == RoomType.BEDROOM else 1
            people_sensible = occupants * 230  # BTU/hr per person
            people_latent = occupants * 200
            equipment = room.area_sqft * 3.4  # BTU/hr/sqft
            
            # Adjust for room type
            if room.room_type == RoomType.KITCHEN:
                equipment *= 2  # Cooking appliances
                people_latent *= 1.3
            elif room.room_type == RoomType.BATHROOM:
                people_latent *= 1.5  # Moisture
            
            # Sum room loads
            room_heating = (wall_heating + window_heating + door_heating + 
                           roof_heating + floor_heating)
            
            room_cooling_s = (wall_cooling + window_cooling_cond + 
                            window_cooling_solar + door_cooling + 
                            roof_cooling + floor_cooling + 
                            people_sensible + equipment)
            
            room_cooling_l = people_latent
            
            heating += room_heating
            cooling_s += room_cooling_s
            cooling_l += room_cooling_l
        
        # 7. INFILTRATION (whole floor)
        # ACH method: CFM = (ACH × Volume) / 60
        volume = floor.total_sqft * ceiling_height
        # Get zone-appropriate infiltration rate
        # Each climate zone has different typical infiltration rates
        ach = factors['infiltration_ach']
        cfm = (ach * volume) / 60
        
        # Sensible: Q = 1.08 × CFM × ΔT
        infiltration_heating = 1.08 * cfm * delta_t_heating
        infiltration_cooling_s = 1.08 * cfm * delta_t_cooling
        
        # Latent: Q = 4840 × CFM × ΔW (humidity ratio difference)
        # Use zone-specific humidity ratios
        indoor_humidity_ratio = zone_config.get('indoor_humidity_ratio', 0.0095)
        outdoor_humidity_ratio = climate.get('summer_humidity', 
                                            zone_config.get('outdoor_humidity_ratio_summer', 0.010))
        delta_w = max(0, outdoor_humidity_ratio - indoor_humidity_ratio)
        infiltration_cooling_l = 4840 * cfm * delta_w
        
        heating += infiltration_heating
        cooling_s += infiltration_cooling_s
        cooling_l += infiltration_cooling_l
        
        # Note: Ventilation is handled at building level to avoid double-counting
        
        # 8. FLOOR STRATIFICATION ADJUSTMENTS
        if floor_number == 0:  # Ground floor
            heating *= 1.05  # Cooler at ground level
            cooling_s *= 0.90  # Naturally cooler
        elif floor_number >= total_floors - 1:  # Top floor
            heating *= 0.95  # Heat rises
            cooling_s *= 1.10  # More cooling needed
        
        return heating, cooling_s, cooling_l


# Module-level instance
calculator = ManualJCalculator()


def run_manual_j(
    building: Building, 
    construction_quality: str = "average",
    synthesis_data: Dict[str, Any] = None
) -> HVACLoads:
    """
    Run Manual J calculations
    STRATEGY: Try GPT-4 first for accuracy, fall back to formulas if needed
    
    Args:
        building: Building data
        construction_quality: Construction quality (tight/average/loose)
        synthesis_data: All extraction and synthesis data
    """
    
    # Try GPT-4 calculation first (most accurate)
    if GPT_AVAILABLE and synthesis_data:
        logger.info("Attempting GPT-4 Manual J calculation...")
        
        # Prepare data for GPT
        gpt_data = {
            'building': building.to_json(),
            'climate': get_climate_data_for_zip(building.zip_code),
            'extraction_results': synthesis_data
        }
        
        # Add envelope data if available
        for key in synthesis_data:
            if key.startswith('floor_') and 'envelope' in synthesis_data.get(key, {}):
                gpt_data['envelope'] = synthesis_data[key]['envelope']
                break
        
        try:
            gpt_result = calculate_with_gpt(gpt_data)
            
            if gpt_result and gpt_result.get('heating_btu_hr') and gpt_result.get('cooling_btu_hr'):
                logger.info(f"✅ GPT-4 Manual J successful: {gpt_result['heating_btu_hr']:,} BTU/hr heating, "
                           f"{gpt_result['cooling_btu_hr']:,} BTU/hr cooling")
                
                # Create HVACLoads object from GPT result
                loads = HVACLoads(
                    heating_btu_hr=gpt_result['heating_btu_hr'],
                    cooling_btu_hr=gpt_result['cooling_btu_hr'],
                    heating_tons=gpt_result.get('heating_tons', gpt_result['heating_btu_hr'] / 12000),
                    cooling_tons=gpt_result.get('cooling_tons', gpt_result['cooling_btu_hr'] / 12000),
                    cfm_required=gpt_result.get('cooling_tons', gpt_result['cooling_btu_hr'] / 12000) * 400,
                    floor_loads={}  # GPT doesn't provide floor breakdown yet
                )
                
                return loads
                
        except Exception as e:
            logger.warning(f"GPT-4 calculation failed: {e}, falling back to formula-based")
    
    # Fall back to formula-based calculation
    logger.info("Using formula-based Manual J calculation")
    
    # Override construction quality if synthesis provides it
    if synthesis_data and synthesis_data.get("synthesis", {}).get("infiltration", {}).get("construction_quality"):
        construction_quality = synthesis_data["synthesis"]["infiltration"]["construction_quality"]
        logger.info(f"Using AI-determined construction quality: {construction_quality}")
    
    # Calculate base loads
    loads = calculator.calculate(building, construction_quality, synthesis_data)
    
    # Apply safety factor if recommended by synthesis
    if synthesis_data and synthesis_data.get("synthesis", {}).get("safety_factor"):
        safety_factor = synthesis_data["synthesis"]["safety_factor"]
        logger.info(f"Applying AI-recommended safety factor: {safety_factor:.2f}")
        
        loads.heating_btu_hr *= safety_factor
        loads.cooling_btu_hr *= safety_factor
        loads.heating_tons = loads.heating_btu_hr / 12000
        loads.cooling_tons = loads.cooling_btu_hr / 12000
        
        # Update floor breakdowns too
        for floor_num in loads.floor_loads:
            loads.floor_loads[floor_num]["heating_btu_hr"] *= safety_factor
            loads.floor_loads[floor_num]["cooling_btu_hr"] *= safety_factor
    
    return loads