"""
Multi-Story Building HVAC Load Calculator
Implements proper building physics for accurate multi-floor load calculations
Per ACCA Manual J and ASHRAE standards
"""

import logging
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from app.parser.schema import Room
from services.takeoff_schema import Room as TakeoffRoom, HVACLoad

logger = logging.getLogger(__name__)


class Season(Enum):
    """Season for load calculations"""
    HEATING = "heating"
    COOLING = "cooling"


@dataclass
class FloorLoad:
    """Load for a single floor"""
    floor_number: int
    floor_name: str
    heating_load: float  # BTU/hr
    cooling_load: float  # BTU/hr
    infiltration_cfm: float
    rooms: List[Room]


@dataclass
class BuildingLoad:
    """Complete building load with inter-floor effects"""
    total_heating_btu_hr: float
    total_cooling_btu_hr: float
    floor_loads: List[FloorLoad]
    stack_effect_adjustment: float  # Percentage adjustment
    inter_floor_transfer: float  # BTU/hr between floors
    neutral_pressure_plane_height: float  # feet
    notes: List[str]


class MultiStoryCalculator:
    """
    Calculate HVAC loads for multi-story buildings with proper physics
    
    Key features:
    - Stack effect pressure calculations
    - Inter-floor heat transfer
    - Proper infiltration distribution by floor
    - Interior vs exterior surface classification
    """
    
    # Standard floor heights (feet)
    FLOOR_HEIGHT_RESIDENTIAL = 9.0  # 8' ceiling + 1' floor assembly
    FLOOR_HEIGHT_BASEMENT = 8.0
    
    # Inter-floor assembly R-values (typical)
    R_VALUE_FLOOR_CEILING = 19.0  # R-19 insulation typical
    R_VALUE_UNINSULATED = 3.0  # Uninsulated floor/ceiling
    
    # Stack effect constants
    STACK_COEFFICIENT = 0.00598  # Imperial units coefficient
    NPP_RATIO = 0.4  # Neutral pressure plane at 40% of height (typical)
    
    def __init__(self, climate_zone: str = "4A"):
        """Initialize with climate zone for location-specific calculations"""
        self.climate_zone = climate_zone
        self.notes = []
    
    def calculate_building_loads(
        self,
        floors: List[List[Room]],
        outdoor_temp_heating: float = 0,
        outdoor_temp_cooling: float = 95,
        indoor_temp: float = 70,
        total_cfm50: float = None,
        building_typology: Optional[Dict] = None
    ) -> BuildingLoad:
        """
        Calculate complete building loads with multi-floor effects
        
        Args:
            floors: List of floors, each containing list of rooms
            outdoor_temp_heating: Winter design temperature (°F)
            outdoor_temp_cooling: Summer design temperature (°F)
            indoor_temp: Indoor design temperature (°F)
            total_cfm50: Total building infiltration at 50 Pa
            
        Returns:
            BuildingLoad with all calculations
        """
        # Use building typology if provided
        if building_typology:
            building_type = building_typology.get('building_type', 'unknown')
            has_bonus = building_typology.get('has_bonus_room', False)
            bonus_area = building_typology.get('bonus_room_area', 0)
            
            logger.info(f"Calculating loads for {building_type} building")
            if has_bonus:
                logger.info(f"Building has bonus room: {bonus_area:.0f} sqft")
                self.notes.append(f"Bonus room over garage: {bonus_area:.0f} sqft with enhanced load factors")
        else:
            logger.info(f"Calculating loads for {len(floors)}-story building")
        
        # Calculate building geometry
        building_height = self._calculate_building_height(floors)
        npp_height = building_height * self.NPP_RATIO
        
        # Step 1: Calculate exterior envelope loads only
        floor_loads = self._calculate_exterior_loads(
            floors, outdoor_temp_heating, outdoor_temp_cooling, indoor_temp
        )
        
        # Step 2: Calculate and distribute infiltration with stack effect
        if total_cfm50:
            self._distribute_infiltration_stack_effect(
                floor_loads, building_height, npp_height,
                outdoor_temp_heating, outdoor_temp_cooling, indoor_temp, total_cfm50
            )
        
        # Step 3: Calculate inter-floor heat transfer
        inter_floor_transfer = self._calculate_inter_floor_transfer(
            floor_loads, indoor_temp
        )
        
        # Step 4: Apply thermal coupling corrections
        stack_adjustment = self._apply_thermal_coupling(
            floor_loads, inter_floor_transfer
        )
        
        # Calculate totals
        total_heating = sum(fl.heating_load for fl in floor_loads)
        total_cooling = sum(fl.cooling_load for fl in floor_loads)
        
        # Log summary
        logger.info(f"Building totals: {total_heating:.0f} BTU/hr heating, "
                   f"{total_cooling:.0f} BTU/hr cooling")
        logger.info(f"Stack effect adjustment: {stack_adjustment:.1f}%")
        logger.info(f"Inter-floor heat transfer: {inter_floor_transfer:.0f} BTU/hr")
        
        return BuildingLoad(
            total_heating_btu_hr=total_heating,
            total_cooling_btu_hr=total_cooling,
            floor_loads=floor_loads,
            stack_effect_adjustment=stack_adjustment,
            inter_floor_transfer=inter_floor_transfer,
            neutral_pressure_plane_height=npp_height,
            notes=self.notes
        )
    
    def _calculate_building_height(self, floors: List[List[Room]]) -> float:
        """Calculate total building height based on number of floors"""
        height = 0
        for floor_idx, floor_rooms in enumerate(floors):
            if floor_idx == 0 and any(r.floor == 0 for r in floor_rooms):
                # Basement floor
                height += self.FLOOR_HEIGHT_BASEMENT
            else:
                # Regular floor
                height += self.FLOOR_HEIGHT_RESIDENTIAL
        return height
    
    def _calculate_exterior_loads(
        self,
        floors: List[List[Room]],
        outdoor_heating: float,
        outdoor_cooling: float,
        indoor: float
    ) -> List[FloorLoad]:
        """
        Calculate loads for exterior surfaces only
        Interior surfaces between conditioned spaces have no load
        """
        floor_loads = []
        
        for floor_idx, floor_rooms in enumerate(floors):
            if not floor_rooms:
                continue
            
            floor_num = floor_rooms[0].floor if hasattr(floor_rooms[0], 'floor') else floor_idx + 1
            floor_name = f"Floor {floor_num}"
            
            # Check if this is a bonus floor
            is_bonus_floor = any('bonus' in r.name.lower() for r in floor_rooms)
            if is_bonus_floor:
                floor_name = "Bonus Floor"
                logger.info(f"Detected bonus floor with {len(floor_rooms)} rooms")
            
            heating_total = 0
            cooling_total = 0
            
            for room in floor_rooms:
                # Check if this specific room is a bonus room
                is_bonus_room = 'bonus' in room.name.lower() or is_bonus_floor
                
                # Only calculate load for EXTERIOR surfaces
                heating, cooling = self._calculate_room_exterior_load(
                    room, outdoor_heating, outdoor_cooling, indoor, floor_num,
                    is_bonus_room=is_bonus_room
                )
                heating_total += heating
                cooling_total += cooling
            
            floor_loads.append(FloorLoad(
                floor_number=floor_num,
                floor_name=floor_name,
                heating_load=heating_total,
                cooling_load=cooling_total,
                infiltration_cfm=0,  # Will be set by infiltration distribution
                rooms=floor_rooms
            ))
        
        return floor_loads
    
    def _calculate_room_exterior_load(
        self,
        room: Room,
        outdoor_heating: float,
        outdoor_cooling: float,
        indoor: float,
        floor_num: int,
        is_bonus_room: bool = False
    ) -> Tuple[float, float]:
        """
        Calculate load for exterior surfaces of a room
        
        This is simplified - in production, would use full Manual J calculations
        """
        heating_load = 0
        cooling_load = 0
        
        # Temperature differences
        delta_t_heating = indoor - outdoor_heating
        delta_t_cooling = outdoor_cooling - indoor
        
        # Get exterior wall count (default to 1 if not specified)
        exterior_walls = getattr(room, 'exterior_walls', 1)
        if hasattr(room, 'surfaces'):
            exterior_walls = room.surfaces.exterior_walls
        
        # Wall loads (only exterior walls)
        wall_area_per_wall = room.area ** 0.5 * 8  # Approximate wall area
        exterior_wall_area = wall_area_per_wall * exterior_walls
        
        # Typical R-values
        wall_r_value = 13  # R-13 typical
        
        if exterior_wall_area > 0:
            heating_load += exterior_wall_area * delta_t_heating / wall_r_value
            cooling_load += exterior_wall_area * delta_t_cooling / wall_r_value
        
        # Ceiling load (only if exterior - to attic/roof)
        has_exterior_ceiling = getattr(room, 'has_exterior_ceiling', floor_num == 2)
        if hasattr(room, 'surfaces'):
            has_exterior_ceiling = room.surfaces.has_exterior_ceiling
        
        if has_exterior_ceiling:
            ceiling_r_value = 30  # R-30 typical attic
            heating_load += room.area * delta_t_heating / ceiling_r_value
            cooling_load += room.area * delta_t_cooling / ceiling_r_value
        
        # Floor load (only if exterior - over unconditioned space)
        has_exterior_floor = getattr(room, 'has_exterior_floor', floor_num == 1)
        if hasattr(room, 'surfaces'):
            has_exterior_floor = room.surfaces.has_exterior_floor
        
        # Special handling for bonus rooms over garage
        if is_bonus_room or 'bonus' in room.name.lower():
            # Bonus rooms have exposed floor over unconditioned garage
            has_exterior_floor = True
            floor_r_value = 11  # Often less insulated over garage
            
            # Higher infiltration for bonus rooms
            infiltration_multiplier = 1.5
            
            # Exposed floor load (garage is semi-conditioned)
            garage_temp_winter = outdoor_heating + 10  # Garage warmer than outside
            garage_temp_summer = outdoor_cooling - 5   # Garage cooler than outside
            
            floor_delta_t_heating = indoor - garage_temp_winter
            floor_delta_t_cooling = garage_temp_summer - indoor
            
            heating_load += room.area * floor_delta_t_heating / floor_r_value
            cooling_load += room.area * max(0, floor_delta_t_cooling) / floor_r_value
            
            # Additional infiltration load for bonus rooms
            heating_load *= infiltration_multiplier
            cooling_load *= infiltration_multiplier
            
            logger.debug(f"Bonus room '{room.name}': Additional floor load due to garage exposure")
            
        elif has_exterior_floor:
            floor_r_value = 19  # R-19 typical
            if floor_num == 0:  # Basement
                # Ground coupling reduces load
                heating_load += room.area * delta_t_heating / floor_r_value * 0.5
                cooling_load += room.area * delta_t_cooling / floor_r_value * 0.3
            else:
                heating_load += room.area * delta_t_heating / floor_r_value
                cooling_load += room.area * delta_t_cooling / floor_r_value
        
        # Window loads (simplified)
        window_area = room.area * 0.15  # Assume 15% window-to-floor ratio
        window_r_value = 3  # R-3 for double-pane
        
        heating_load += window_area * delta_t_heating / window_r_value
        cooling_load += window_area * delta_t_cooling / window_r_value
        
        # Solar gain (cooling only)
        cooling_load += window_area * 20  # 20 BTU/hr/sq ft solar gain
        
        return heating_load, cooling_load
    
    def _distribute_infiltration_stack_effect(
        self,
        floor_loads: List[FloorLoad],
        building_height: float,
        npp_height: float,
        outdoor_heating: float,
        outdoor_cooling: float,
        indoor: float,
        total_cfm50: float
    ):
        """
        Distribute infiltration by floor based on stack effect pressures
        
        Winter: More infiltration at bottom (cold air infiltrates low)
        Summer: More infiltration at top (hot air infiltrates high)
        """
        # Convert CFM50 to natural CFM (rough approximation)
        cfm_natural = total_cfm50 / 20  # Typical conversion factor
        
        # Calculate pressure at each floor for both seasons
        for season in [Season.HEATING, Season.COOLING]:
            outdoor_temp = outdoor_heating if season == Season.HEATING else outdoor_cooling
            
            # Skip if no temperature difference
            if abs(outdoor_temp - indoor) < 1:
                continue
            
            # Calculate pressure difference at each floor
            floor_pressures = []
            for floor_load in floor_loads:
                # Height of floor center above ground
                floor_height = (floor_load.floor_number - 0.5) * self.FLOOR_HEIGHT_RESIDENTIAL
                
                # Distance from neutral pressure plane
                delta_h = floor_height - npp_height
                
                # Stack pressure (inches water column)
                # ΔP = 0.00598 × h × (1/To - 1/Ti) × 460
                temp_factor = (460 / (outdoor_temp + 460)) - (460 / (indoor + 460))
                delta_p = abs(self.STACK_COEFFICIENT * delta_h * temp_factor * 460)
                
                floor_pressures.append(delta_p)
            
            # Normalize pressures to distribute total CFM
            total_pressure = sum(floor_pressures)
            if total_pressure > 0:
                for i, floor_load in enumerate(floor_loads):
                    fraction = floor_pressures[i] / total_pressure
                    floor_cfm = cfm_natural * fraction
                    
                    # Add infiltration load
                    if season == Season.HEATING:
                        infiltration_load = floor_cfm * 1.08 * (indoor - outdoor_heating)
                        floor_load.heating_load += infiltration_load
                    else:
                        infiltration_load = floor_cfm * 1.08 * (outdoor_cooling - indoor)
                        floor_load.cooling_load += infiltration_load
                    
                    floor_load.infiltration_cfm = floor_cfm
            
            # Log distribution
            if season == Season.HEATING:
                self.notes.append(f"Winter infiltration distribution: " +
                    ", ".join([f"F{fl.floor_number}={fl.infiltration_cfm:.0f}CFM" 
                              for fl in floor_loads]))
    
    def _calculate_inter_floor_transfer(
        self,
        floor_loads: List[FloorLoad],
        indoor_temp: float
    ) -> float:
        """
        Calculate heat transfer between floors
        
        Only applies if there's a temperature difference between floors
        (e.g., thermostat setback, zoning, or uneven heating/cooling)
        """
        total_transfer = 0
        
        # For adjacent floors
        for i in range(len(floor_loads) - 1):
            lower_floor = floor_loads[i]
            upper_floor = floor_loads[i + 1]
            
            # Estimate temperature difference between floors
            # In heating: upper floor warmer (heat rises)
            # In cooling: upper floor warmer (more solar gain, heat rises)
            temp_diff_heating = 2.0  # Upper floor 2°F warmer in winter
            temp_diff_cooling = 3.0  # Upper floor 3°F warmer in summer
            
            # Average floor area for heat transfer
            shared_area = min(
                sum(r.area for r in lower_floor.rooms),
                sum(r.area for r in upper_floor.rooms)
            )
            
            # Heat transfer: Q = U × A × ΔT
            u_value = 1 / self.R_VALUE_FLOOR_CEILING
            
            # Heating season transfer (heat goes up, reduces lower floor load)
            transfer_heating = u_value * shared_area * temp_diff_heating
            lower_floor.heating_load -= transfer_heating * 0.5
            upper_floor.heating_load -= transfer_heating * 0.5  # Both benefit
            
            # Cooling season transfer (heat goes up, increases upper floor load)
            transfer_cooling = u_value * shared_area * temp_diff_cooling
            upper_floor.cooling_load += transfer_cooling * 0.5
            
            total_transfer += max(transfer_heating, transfer_cooling)
        
        if total_transfer > 0:
            self.notes.append(f"Inter-floor heat transfer: {total_transfer:.0f} BTU/hr")
        
        return total_transfer
    
    def _apply_thermal_coupling(
        self,
        floor_loads: List[FloorLoad],
        inter_floor_transfer: float
    ) -> float:
        """
        Apply thermal coupling corrections for multi-floor buildings
        
        Multi-floor buildings have better thermal performance due to:
        - Reduced exterior surface area per unit volume
        - Internal heat sharing between floors
        - Thermal mass effects
        """
        if len(floor_loads) <= 1:
            return 0  # No coupling for single floor
        
        # Calculate coupling factor based on number of floors
        num_floors = len(floor_loads)
        
        # More floors = more coupling benefit
        # 2 floors: 5% reduction
        # 3 floors: 8% reduction
        # 4+ floors: 10% reduction
        if num_floors == 2:
            coupling_factor = 0.95
        elif num_floors == 3:
            coupling_factor = 0.92
        else:
            coupling_factor = 0.90
        
        # Apply coupling to all floor loads
        for floor_load in floor_loads:
            original_heating = floor_load.heating_load
            original_cooling = floor_load.cooling_load
            
            floor_load.heating_load *= coupling_factor
            floor_load.cooling_load *= coupling_factor
            
            logger.debug(f"Floor {floor_load.floor_number} coupling adjustment: "
                        f"Heating {original_heating:.0f} -> {floor_load.heating_load:.0f}, "
                        f"Cooling {original_cooling:.0f} -> {floor_load.cooling_load:.0f}")
        
        adjustment_percent = (1 - coupling_factor) * 100
        self.notes.append(f"Thermal coupling reduction: {adjustment_percent:.1f}%")
        
        return adjustment_percent


def calculate_multi_story_loads(
    blueprint_data: Dict,
    climate_zone: str = "4A"
) -> BuildingLoad:
    """
    Convenience function to calculate multi-story loads from blueprint data
    
    Args:
        blueprint_data: Parsed blueprint data with rooms and floors
        climate_zone: Climate zone for location
        
    Returns:
        Complete building load calculation
    """
    calculator = MultiStoryCalculator(climate_zone)
    
    # Group rooms by floor
    floors_dict = {}
    for room in blueprint_data.get('rooms', []):
        floor_num = room.get('floor', 1)
        if floor_num not in floors_dict:
            floors_dict[floor_num] = []
        floors_dict[floor_num].append(room)
    
    # Convert to list of floors
    floors = [floors_dict[k] for k in sorted(floors_dict.keys())]
    
    # Get design temperatures from climate data
    outdoor_heating = blueprint_data.get('design_temps', {}).get('heating', 0)
    outdoor_cooling = blueprint_data.get('design_temps', {}).get('cooling', 95)
    
    # Calculate loads
    return calculator.calculate_building_loads(
        floors,
        outdoor_temp_heating=outdoor_heating,
        outdoor_temp_cooling=outdoor_cooling
    )