"""
HVAC Calculator - ACCA Manual J load calculations
Calculates heating and cooling loads based on blueprint data and climate zone
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from services.takeoff_schema import (
    BlueprintTakeoff, Room, BuildingEnvelope, ClimateData,
    HVACLoad, RoomType
)
try:
    from services.multi_story_calculator import MultiStoryCalculator, BuildingLoad
    MULTI_STORY_AVAILABLE = True
except ImportError:
    logger.warning("MultiStoryCalculator not available - using simple calculations")
    MULTI_STORY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ClimateZoneData:
    """Climate zone specific data for HVAC calculations"""
    zone: str
    winter_design_temp: float  # °F
    summer_design_temp: float  # °F
    summer_humidity: float  # %
    heating_degree_days: float
    cooling_degree_days: float


class HVACCalculator:
    """Calculate HVAC loads using ACCA Manual J methodology"""
    
    # Climate zone data by ZIP code prefix
    CLIMATE_ZONES = {
        "010": {"zone": "5A", "winter": 5, "summer": 88, "humidity": 70},  # MA
        "020": {"zone": "5A", "winter": 5, "summer": 88, "humidity": 70},  # MA
        "030": {"zone": "5A", "winter": 0, "summer": 86, "humidity": 70},  # NH
        "040": {"zone": "6A", "winter": -5, "summer": 85, "humidity": 70},  # ME
        "050": {"zone": "5A", "winter": -5, "summer": 87, "humidity": 70},  # VT
        "060": {"zone": "5A", "winter": 1, "summer": 88, "humidity": 73},  # CT
        "070": {"zone": "4A", "winter": 14, "summer": 91, "humidity": 73},  # NJ
        "100": {"zone": "4A", "winter": 15, "summer": 91, "humidity": 72},  # NY
        "150": {"zone": "5A", "winter": 9, "summer": 89, "humidity": 72},  # PA
        "200": {"zone": "4A", "winter": 20, "summer": 93, "humidity": 73},  # DC
        "300": {"zone": "3A", "winter": 25, "summer": 94, "humidity": 74},  # GA
        "320": {"zone": "2A", "winter": 40, "summer": 93, "humidity": 77},  # FL
        "330": {"zone": "2A", "winter": 44, "summer": 92, "humidity": 77},  # FL
        "350": {"zone": "3A", "winter": 25, "summer": 95, "humidity": 75},  # AL
        "370": {"zone": "3A", "winter": 20, "summer": 95, "humidity": 76},  # TN
        "400": {"zone": "4A", "winter": 15, "summer": 93, "humidity": 74},  # KY
        "430": {"zone": "5A", "winter": 6, "summer": 89, "humidity": 73},  # OH
        "460": {"zone": "5A", "winter": 3, "summer": 89, "humidity": 74},  # IN
        "480": {"zone": "5A", "winter": 1, "summer": 89, "humidity": 73},  # MI
        "500": {"zone": "5A", "winter": -7, "summer": 89, "humidity": 73},  # IA
        "530": {"zone": "6A", "winter": -11, "summer": 89, "humidity": 73},  # WI
        "550": {"zone": "6A", "winter": -12, "summer": 89, "humidity": 72},  # MN
        "600": {"zone": "5A", "winter": 3, "summer": 91, "humidity": 74},  # IL
        "630": {"zone": "4A", "winter": 6, "summer": 94, "humidity": 74},  # MO
        "700": {"zone": "3A", "winter": 19, "summer": 97, "humidity": 74},  # LA
        "750": {"zone": "3A", "winter": 22, "summer": 99, "humidity": 73},  # TX
        "770": {"zone": "2A", "winter": 32, "summer": 95, "humidity": 75},  # TX
        "800": {"zone": "5B", "winter": 7, "summer": 94, "humidity": 35},  # CO
        "850": {"zone": "3B", "winter": 34, "summer": 108, "humidity": 31},  # AZ
        "870": {"zone": "4B", "winter": 17, "summer": 95, "humidity": 38},  # NM
        "900": {"zone": "3C", "winter": 42, "summer": 83, "humidity": 68},  # CA
        "940": {"zone": "3C", "winter": 40, "summer": 75, "humidity": 73},  # CA
        "970": {"zone": "4C", "winter": 25, "summer": 85, "humidity": 64},  # OR
        "980": {"zone": "4C", "winter": 26, "summer": 84, "humidity": 64},  # WA
        "990": {"zone": "4C", "winter": 22, "summer": 82, "humidity": 65},  # WA
    }
    
    # Room-specific load factors (BTU/hr per sq ft)
    ROOM_LOAD_FACTORS = {
        RoomType.KITCHEN: {"heating": 25, "cooling": 35},  # Higher due to appliances
        RoomType.BATHROOM: {"heating": 22, "cooling": 28},
        RoomType.MASTER_BATHROOM: {"heating": 22, "cooling": 28},
        RoomType.LIVING_ROOM: {"heating": 20, "cooling": 30},  # More windows typically
        RoomType.FAMILY_ROOM: {"heating": 20, "cooling": 30},
        RoomType.GREAT_ROOM: {"heating": 22, "cooling": 32},  # Large volume
        RoomType.BEDROOM: {"heating": 18, "cooling": 25},
        RoomType.MASTER_BEDROOM: {"heating": 18, "cooling": 25},
        RoomType.DINING_ROOM: {"heating": 20, "cooling": 28},
        RoomType.OFFICE: {"heating": 20, "cooling": 30},  # Equipment heat
        RoomType.DEN: {"heating": 18, "cooling": 25},
        RoomType.GARAGE: {"heating": 10, "cooling": 15},  # If conditioned
        RoomType.BASEMENT: {"heating": 15, "cooling": 20},  # Ground coupling
        RoomType.ATTIC: {"heating": 25, "cooling": 35},  # If conditioned
        RoomType.HALLWAY: {"heating": 15, "cooling": 20},
        RoomType.CLOSET: {"heating": 12, "cooling": 18},
        RoomType.WALK_IN_CLOSET: {"heating": 12, "cooling": 18},
        RoomType.LAUNDRY: {"heating": 20, "cooling": 30},  # Equipment heat
        RoomType.UTILITY: {"heating": 18, "cooling": 25},
        RoomType.FOYER: {"heating": 20, "cooling": 28},
        RoomType.ENTRY: {"heating": 22, "cooling": 30},  # Air infiltration
        RoomType.PANTRY: {"heating": 15, "cooling": 20},
        RoomType.REC_ROOM: {"heating": 20, "cooling": 28},
        RoomType.OTHER: {"heating": 18, "cooling": 25},
    }
    
    def calculate_loads(self, takeoff: BlueprintTakeoff) -> BlueprintTakeoff:
        """
        Calculate HVAC loads for the building
        
        Args:
            takeoff: BlueprintTakeoff with room and building data
            
        Returns:
            BlueprintTakeoff with calculated HVAC loads
        """
        logger.info(f"Calculating HVAC loads for {takeoff.num_rooms} rooms")
        
        # Get climate data
        climate_data = self._get_climate_data(takeoff.climate_data)
        
        # Calculate room-by-room loads
        room_loads = {}
        total_heating = 0
        total_cooling = 0
        
        # Check if this is a multi-story building
        floors = {}
        for room in takeoff.rooms:
            floor_num = room.floor_number if hasattr(room, 'floor_number') else 1
            if floor_num not in floors:
                floors[floor_num] = []
            floors[floor_num].append(room)
        
        is_multi_story = len(floors) > 1
        
        if is_multi_story and MULTI_STORY_AVAILABLE:
            logger.info(f"Multi-story building with {len(floors)} floors - using advanced calculator")
            
            # Use MultiStoryCalculator for proper physics
            multi_calc = MultiStoryCalculator(climate_zone=climate_data.zone)
            
            # Convert floors dict to list
            floor_list = [floors[k] for k in sorted(floors.keys())]
            
            # Get design temperatures
            outdoor_heating = climate_data.winter_design_temp
            outdoor_cooling = climate_data.summer_design_temp
            
            # Calculate with multi-story physics
            building_load = multi_calc.calculate_building_loads(
                floors=floor_list,
                outdoor_temp_heating=outdoor_heating,
                outdoor_temp_cooling=outdoor_cooling,
                indoor_temp=70
            )
            
            # Update rooms with calculated loads
            for floor_load in building_load.floor_loads:
                for room in floor_load.rooms:
                    # Distribute floor load to rooms proportionally
                    room_fraction = room.area_sqft / sum(r.area_sqft for r in floor_load.rooms)
                    room.heating_btu_hr = floor_load.heating_load * room_fraction
                    room.cooling_btu_hr = floor_load.cooling_load * room_fraction
            
            total_heating = building_load.total_heating_btu_hr
            total_cooling = building_load.total_cooling_btu_hr
            
            logger.info(f"Multi-story calculation complete: {total_heating:.0f} BTU/hr heating, "
                       f"{total_cooling:.0f} BTU/hr cooling")
            
            # Track room loads for consistency
            room_loads = {}
            for room in takeoff.rooms:
                room_loads[room.id] = {
                    "heating": room.heating_btu_hr or 0,
                    "cooling": room.cooling_btu_hr or 0
                }
        else:
            # Single floor or fallback - use existing simple calculation
            if is_multi_story:
                logger.info("Multi-story building but using simple calculator (advanced not available)")
            else:
                logger.info("Single floor building - using standard calculator")
            
            room_loads = {}
            total_heating = 0
            total_cooling = 0
            
            for room in takeoff.rooms:
                heating_load, cooling_load = self._calculate_room_load(
                    room=room,
                    climate_data=climate_data,
                    envelope=takeoff.building_envelope
                )
                
                # Update room with calculated loads
                room.heating_btu_hr = heating_load
                room.cooling_btu_hr = cooling_load
                
                # Track totals
                room_loads[room.id] = {
                    "heating": heating_load,
                    "cooling": cooling_load
                }
                total_heating += heating_load
                total_cooling += cooling_load
        
        # Calculate load components
        heating_components = self._calculate_heating_components(
            takeoff=takeoff,
            climate_data=climate_data
        )
        
        cooling_components = self._calculate_cooling_components(
            takeoff=takeoff,
            climate_data=climate_data
        )
        
        # Apply safety factor
        safety_factor = 1.1
        total_heating *= safety_factor
        total_cooling *= safety_factor
        
        # Convert to tons (12,000 BTU/hr = 1 ton)
        heating_tons = total_heating / 12000
        cooling_tons = total_cooling / 12000
        
        # Create HVAC load object
        hvac_load = HVACLoad(
            room_loads=room_loads,
            total_heating_btu_hr=total_heating,
            total_cooling_btu_hr=total_cooling,
            heating_system_tons=round(heating_tons, 2),
            cooling_system_tons=round(cooling_tons, 2),
            heating_components=heating_components,
            cooling_components=cooling_components,
            calculation_method="ACCA Manual J",
            safety_factor=safety_factor
        )
        
        # Update takeoff with HVAC loads
        takeoff.hvac_loads = hvac_load
        
        logger.info(f"HVAC calculation complete: {heating_tons:.1f} tons heating, {cooling_tons:.1f} tons cooling")
        
        return takeoff
    
    def _get_climate_data(self, climate_data: ClimateData) -> ClimateZoneData:
        """Get climate zone data from ZIP code"""
        zip_prefix = climate_data.zip_code[:3] if len(climate_data.zip_code) >= 3 else "980"
        
        # Look up climate zone data
        zone_data = self.CLIMATE_ZONES.get(zip_prefix, {
            "zone": "4A",
            "winter": 20,
            "summer": 90,
            "humidity": 50
        })
        
        # Use provided temperatures if available, otherwise use defaults
        return ClimateZoneData(
            zone=climate_data.climate_zone or zone_data["zone"],
            winter_design_temp=climate_data.winter_design_temp_f or zone_data["winter"],
            summer_design_temp=climate_data.summer_design_temp_f or zone_data["summer"],
            summer_humidity=climate_data.summer_design_humidity or zone_data["humidity"],
            heating_degree_days=6500,  # Typical value
            cooling_degree_days=1500   # Typical value
        )
    
    def _calculate_room_load(
        self,
        room: Room,
        climate_data: ClimateZoneData,
        envelope: BuildingEnvelope
    ) -> tuple[float, float]:
        """
        Calculate heating and cooling loads for a single room
        
        Args:
            room: Room to calculate loads for
            climate_data: Climate zone data
            envelope: Building envelope characteristics
            
        Returns:
            Tuple of (heating_btu_hr, cooling_btu_hr)
        """
        # Get base load factors for room type
        load_factors = self.ROOM_LOAD_FACTORS.get(
            room.room_type,
            self.ROOM_LOAD_FACTORS[RoomType.OTHER]
        )
        
        # Base loads from room area
        base_heating = room.area_sqft * load_factors["heating"]
        base_cooling = room.area_sqft * load_factors["cooling"]
        
        # Adjust for exterior walls
        if room.exterior_walls > 0:
            # Assume 10 ft wall height, U-value based on R-value
            wall_u_value = 1 / envelope.wall_r_value
            wall_area = room.exterior_walls * (room.width_ft + room.length_ft) / 2 * room.ceiling_height_ft
            
            # Temperature differences
            winter_delta_t = 70 - climate_data.winter_design_temp  # Indoor - outdoor
            summer_delta_t = climate_data.summer_design_temp - 75  # Outdoor - indoor
            
            # Wall heat transfer
            wall_heating = wall_area * wall_u_value * winter_delta_t
            wall_cooling = wall_area * wall_u_value * summer_delta_t
            
            base_heating += wall_heating
            base_cooling += wall_cooling
        
        # Adjust for windows
        if room.windows:
            window_area = room.window_area_sqft
            # Double pane window U-value approximately 0.5
            window_u_value = 0.5
            
            # Window heat transfer
            window_heating = window_area * window_u_value * (70 - climate_data.winter_design_temp)
            window_cooling = window_area * window_u_value * (climate_data.summer_design_temp - 75)
            
            # Solar heat gain (cooling only)
            # SHGC (Solar Heat Gain Coefficient) typically 0.3 for double pane
            solar_gain = window_area * 150  # 150 BTU/hr/sq ft typical solar load
            
            base_heating += window_heating
            base_cooling += window_cooling + solar_gain * 0.3
        
        # Adjust for infiltration
        room_volume = room.volume_cuft
        air_changes = envelope.air_changes_per_hour
        
        # Infiltration load (CFM * 1.08 * delta_T)
        infiltration_cfm = (room_volume * air_changes) / 60
        infiltration_heating = infiltration_cfm * 1.08 * (70 - climate_data.winter_design_temp)
        infiltration_cooling_sensible = infiltration_cfm * 1.08 * (climate_data.summer_design_temp - 75)
        
        # Latent cooling load (humidity removal)
        infiltration_cooling_latent = infiltration_cfm * 0.68 * (climate_data.summer_humidity - 50)
        
        base_heating += infiltration_heating
        base_cooling += infiltration_cooling_sensible + infiltration_cooling_latent
        
        # Floor level adjustments only for simple calculator
        # Multi-story calculator handles this with proper physics
        if hasattr(room, 'floor_number'):
            if room.floor_number == 0:  # Basement
                base_heating *= 0.8  # Ground coupling reduces heating load
                base_cooling *= 0.9  # Less cooling needed
            elif room.floor_number > 1 and not MULTI_STORY_AVAILABLE:  # Upper floors (only if not using multi-story calc)
                base_heating *= 1.05  # Heat rises
                base_cooling *= 1.1   # More cooling needed upstairs
        
        # Internal gains (people, lights, equipment) - cooling only
        internal_gains = room.area_sqft * 3  # 3 BTU/hr/sq ft typical
        base_cooling += internal_gains
        
        # Ensure positive values
        heating_load = max(0, base_heating)
        cooling_load = max(0, base_cooling)
        
        return heating_load, cooling_load
    
    def _calculate_heating_components(
        self,
        takeoff: BlueprintTakeoff,
        climate_data: ClimateZoneData
    ) -> Dict[str, float]:
        """Calculate heating load components"""
        envelope = takeoff.building_envelope
        delta_t = 70 - climate_data.winter_design_temp
        
        # Wall losses
        wall_area = takeoff.total_area_sqft * 0.4  # Estimate wall area as 40% of floor area
        wall_load = wall_area * (1 / envelope.wall_r_value) * delta_t
        
        # Window losses
        window_area = sum(r.window_area_sqft for r in takeoff.rooms)
        window_load = window_area * 0.5 * delta_t  # U-value 0.5 for double pane
        
        # Infiltration losses
        total_volume = sum(r.volume_cuft for r in takeoff.rooms)
        infiltration_cfm = (total_volume * envelope.air_changes_per_hour) / 60
        infiltration_load = infiltration_cfm * 1.08 * delta_t
        
        # Door losses
        num_exterior_doors = max(1, takeoff.num_rooms // 10)  # Estimate
        door_load = num_exterior_doors * 21 * 0.5 * delta_t  # 3x7 ft door, U-value 0.5
        
        # Floor losses (if not slab)
        floor_load = 0
        if envelope.foundation_type != "slab":
            floor_area = takeoff.total_area_sqft / envelope.num_floors
            floor_load = floor_area * (1 / envelope.floor_r_value) * delta_t * 0.5
        
        return {
            "walls": wall_load,
            "windows": window_load,
            "infiltration": infiltration_load,
            "doors": door_load,
            "floors": floor_load
        }
    
    def _calculate_cooling_components(
        self,
        takeoff: BlueprintTakeoff,
        climate_data: ClimateZoneData
    ) -> Dict[str, float]:
        """Calculate cooling load components"""
        envelope = takeoff.building_envelope
        delta_t = climate_data.summer_design_temp - 75
        
        # Wall gains
        wall_area = takeoff.total_area_sqft * 0.4
        wall_load = wall_area * (1 / envelope.wall_r_value) * delta_t
        
        # Window gains (conduction + solar)
        window_area = sum(r.window_area_sqft for r in takeoff.rooms)
        window_conduction = window_area * 0.5 * delta_t
        window_solar = window_area * 150 * 0.3  # 150 BTU/hr/sq ft * SHGC 0.3
        
        # Internal gains (people, lights, equipment)
        internal_load = takeoff.total_area_sqft * 3  # 3 BTU/hr/sq ft
        
        # Infiltration gains (sensible + latent)
        total_volume = sum(r.volume_cuft for r in takeoff.rooms)
        infiltration_cfm = (total_volume * envelope.air_changes_per_hour) / 60
        infiltration_sensible = infiltration_cfm * 1.08 * delta_t
        infiltration_latent = infiltration_cfm * 0.68 * (climate_data.summer_humidity - 50)
        
        return {
            "walls": wall_load,
            "windows": window_conduction + window_solar,
            "solar": window_solar,
            "internal": internal_load,
            "infiltration": infiltration_sensible + infiltration_latent
        }


# Global calculator instance
hvac_calculator = HVACCalculator()