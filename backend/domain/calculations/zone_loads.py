"""
Zone-Based Load Calculator
Implements ACCA Manual J calculations at the zone level
Handles complex configurations like bonus-over-garage
"""

import logging
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from domain.models.zones import ThermalZone, ZoneType, BuildingThermalModel
from domain.models.spaces import Space, SpaceType, BoundaryCondition, Surface

logger = logging.getLogger(__name__)


@dataclass
class ZoneLoadComponents:
    """Breakdown of load components for a zone"""
    # Envelope loads
    walls: float = 0
    windows: float = 0
    doors: float = 0
    ceiling: float = 0
    floor: float = 0
    
    # Infiltration
    infiltration: float = 0
    
    # Internal gains (cooling only)
    people: float = 0
    equipment: float = 0
    lighting: float = 0
    
    # Solar gains (cooling only)
    solar: float = 0
    
    @property
    def total(self) -> float:
        """Total load from all components"""
        return (
            self.walls + self.windows + self.doors + 
            self.ceiling + self.floor + self.infiltration +
            self.people + self.equipment + self.lighting + self.solar
        )


@dataclass
class ZoneLoadResult:
    """Result of zone load calculation"""
    zone_id: str
    zone_name: str
    heating_load_btu_hr: float
    cooling_load_btu_hr: float
    heating_components: ZoneLoadComponents
    cooling_components: ZoneLoadComponents
    
    # Zone characteristics
    area_sqft: float
    volume_cuft: float
    is_bonus: bool
    is_primary: bool
    
    # Load intensities
    heating_btu_per_sqft: float = 0
    cooling_btu_per_sqft: float = 0
    
    def __post_init__(self):
        """Calculate intensities"""
        if self.area_sqft > 0:
            self.heating_btu_per_sqft = self.heating_load_btu_hr / self.area_sqft
            self.cooling_btu_per_sqft = self.cooling_load_btu_hr / self.area_sqft


class ZoneLoadCalculator:
    """
    Calculates heating and cooling loads for thermal zones.
    Implements ACCA Manual J procedures with zone-specific adjustments.
    """
    
    def __init__(self):
        # Default thermal properties
        self.default_wall_u = 0.05  # R-20 wall
        self.default_window_u = 0.30
        self.default_window_shgc = 0.30
        self.default_door_u = 0.20
        
        # Internal gain defaults (BTU/hr)
        self.people_gain = 230  # Sensible per person
        self.equipment_w_per_sqft = 1.0  # Watts per sqft
        self.lighting_w_per_sqft = 1.0
        
        # Solar factors
        self.solar_factors = {
            'N': 20,   # BTU/hr·sqft
            'S': 40,
            'E': 35,
            'W': 35
        }
    
    def calculate_zone_loads(
        self,
        zone: ThermalZone,
        building_model: BuildingThermalModel,
        climate_data: Dict[str, Any],
        envelope_properties: Dict[str, Any],
        thermal_intelligence: Optional[Dict[str, Any]] = None
    ) -> ZoneLoadResult:
        """
        Calculate heating and cooling loads for a zone.
        
        Args:
            zone: Thermal zone to calculate
            building_model: Complete building model for context
            climate_data: Climate design conditions
            envelope_properties: Insulation levels, infiltration, etc.
            
        Returns:
            ZoneLoadResult with detailed load breakdown
        """
        logger.info(f"Calculating loads for zone: {zone.name}")
        
        # Design temperature differences
        indoor_winter = zone.heating_setpoint_f
        indoor_summer = zone.cooling_setpoint_f
        outdoor_winter = climate_data['winter_99']
        outdoor_summer = climate_data['summer_1']
        
        delta_t_heating = indoor_winter - outdoor_winter
        delta_t_cooling = outdoor_summer - indoor_summer
        
        # Initialize component trackers
        heating_components = ZoneLoadComponents()
        cooling_components = ZoneLoadComponents()
        
        # 1. Calculate envelope loads for each space in zone
        for space in zone.spaces:
            space_heating, space_cooling = self._calculate_space_envelope_loads(
                space, 
                delta_t_heating, 
                delta_t_cooling,
                envelope_properties
            )
            
            # Add to zone totals
            heating_components.walls += space_heating.walls
            heating_components.windows += space_heating.windows
            heating_components.doors += space_heating.doors
            heating_components.ceiling += space_heating.ceiling
            heating_components.floor += space_heating.floor
            
            cooling_components.walls += space_cooling.walls
            cooling_components.windows += space_cooling.windows
            cooling_components.doors += space_cooling.doors
            cooling_components.ceiling += space_cooling.ceiling
            cooling_components.floor += space_cooling.floor
        
        # 2. Calculate infiltration for zone
        infiltration_heating = self._calculate_zone_infiltration(
            zone, 
            delta_t_heating, 
            is_heating=True,
            envelope_properties=envelope_properties,
            thermal_intelligence=thermal_intelligence
        )
        infiltration_cooling = self._calculate_zone_infiltration(
            zone, 
            delta_t_cooling, 
            is_heating=False,
            envelope_properties=envelope_properties,
            thermal_intelligence=thermal_intelligence
        )
        
        heating_components.infiltration = infiltration_heating
        cooling_components.infiltration = infiltration_cooling
        
        # 3. Internal gains (cooling only)
        if zone.is_conditioned:
            internal_gains = self._calculate_internal_gains(zone)
            cooling_components.people = internal_gains['people']
            cooling_components.equipment = internal_gains['equipment']
            cooling_components.lighting = internal_gains['lighting']
        
        # 4. Solar gains (cooling only)
        solar_gain = self._calculate_solar_gains(zone, climate_data, thermal_intelligence)
        cooling_components.solar = solar_gain
        
        # 5. Apply zone-specific modifiers
        zone_heating_modifier = self._get_zone_heating_modifier(zone, building_model)
        zone_cooling_modifier = self._get_zone_cooling_modifier(zone, building_model)
        
        # 6. Calculate total loads
        base_heating = heating_components.total
        base_cooling = cooling_components.total
        
        final_heating = base_heating * zone_heating_modifier
        final_cooling = base_cooling * zone_cooling_modifier
        
        # Log details for bonus zones
        if zone.is_bonus_zone:
            logger.info(f"Bonus zone {zone.name}: base heating={base_heating:.0f}, "
                       f"modifier={zone_heating_modifier:.2f}, "
                       f"final={final_heating:.0f} BTU/hr")
        
        result = ZoneLoadResult(
            zone_id=zone.zone_id,
            zone_name=zone.name,
            heating_load_btu_hr=final_heating,
            cooling_load_btu_hr=final_cooling,
            heating_components=heating_components,
            cooling_components=cooling_components,
            area_sqft=zone.total_area_sqft,
            volume_cuft=zone.total_volume_cuft,
            is_bonus=zone.is_bonus_zone,
            is_primary=zone.primary_occupancy
        )
        
        return result
    
    def _calculate_space_envelope_loads(
        self,
        space: Space,
        delta_t_heating: float,
        delta_t_cooling: float,
        envelope_properties: Dict[str, Any]
    ) -> Tuple[ZoneLoadComponents, ZoneLoadComponents]:
        """Calculate envelope loads for a single space"""
        
        heating = ZoneLoadComponents()
        cooling = ZoneLoadComponents()
        
        # Get U-values from envelope properties
        wall_u = 1.0 / envelope_properties.get('wall_r_value', 20)
        window_u = envelope_properties.get('window_u_value', self.default_window_u)
        door_u = envelope_properties.get('door_u_value', self.default_door_u)
        ceiling_u = 1.0 / envelope_properties.get('ceiling_r_value', 49)
        floor_u = 1.0 / envelope_properties.get('floor_r_value', 30)
        
        # If we have detailed surfaces, use them
        if space.surfaces:
            for surface in space.surfaces:
                area = surface.net_wall_area if surface.surface_type == "wall" else surface.area_sqft
                u_value = surface.u_value if surface.u_value > 0 else wall_u
                
                # Calculate heat transfer based on boundary condition
                if surface.boundary_condition == BoundaryCondition.EXTERIOR:
                    # Full delta T to exterior
                    heating_load = u_value * area * delta_t_heating
                    cooling_load = u_value * area * delta_t_cooling
                    
                elif surface.boundary_condition == BoundaryCondition.GARAGE:
                    # Garage is semi-buffered (warmer in winter, cooler in summer)
                    garage_winter_temp = envelope_properties.get('outdoor_winter', 0) + 10  # 10°F warmer
                    garage_summer_temp = envelope_properties.get('outdoor_summer', 95) - 5  # 5°F cooler
                    
                    heating_delta = 70 - garage_winter_temp
                    cooling_delta = garage_summer_temp - 75
                    
                    heating_load = u_value * area * heating_delta
                    cooling_load = u_value * area * cooling_delta
                    
                elif surface.boundary_condition == BoundaryCondition.CRAWLSPACE:
                    # Vented crawl - use reduced delta T
                    crawl_reduction = 0.7  # 30% reduction
                    heating_load = u_value * area * delta_t_heating * crawl_reduction
                    cooling_load = u_value * area * delta_t_cooling * crawl_reduction
                    
                elif surface.boundary_condition == BoundaryCondition.GROUND:
                    # Ground contact - use F-factor method for slabs
                    if surface.surface_type == "floor":
                        # Simplified - use reduced delta T
                        heating_load = u_value * area * delta_t_heating * 0.5
                        cooling_load = 0  # No cooling load through ground
                    else:
                        heating_load = cooling_load = 0
                        
                else:
                    # Interior or adiabatic - no load
                    heating_load = cooling_load = 0
                
                # Add to appropriate component
                if surface.surface_type == "wall":
                    heating.walls += heating_load
                    cooling.walls += cooling_load
                    
                    # Add window loads
                    heating.windows += surface.window_area * window_u * delta_t_heating
                    cooling.windows += surface.window_area * window_u * delta_t_cooling
                    
                elif surface.surface_type == "ceiling" or surface.surface_type == "roof":
                    heating.ceiling += heating_load
                    cooling.ceiling += cooling_load
                    
                elif surface.surface_type == "floor":
                    heating.floor += heating_load
                    cooling.floor += cooling_load
        
        else:
            # Simplified calculation without detailed surfaces
            # Estimate based on space area and typical geometry
            
            # Wall area estimate (perimeter × height)
            perimeter = 4 * math.sqrt(space.area_sqft)  # Assume square
            wall_area = perimeter * space.ceiling_height_ft
            
            # Window area (18% of wall area)
            window_area = wall_area * 0.18
            net_wall_area = wall_area - window_area
            
            # Special handling for bonus over garage
            if space.is_over_garage:
                # 5-sided heat loss (4 walls + ceiling, floor to garage)
                
                # Walls - full exterior exposure
                heating.walls = net_wall_area * wall_u * delta_t_heating
                cooling.walls = net_wall_area * wall_u * delta_t_cooling
                
                # Windows - full exposure
                heating.windows = window_area * window_u * delta_t_heating
                cooling.windows = window_area * window_u * delta_t_cooling
                
                # Ceiling - to attic
                heating.ceiling = space.area_sqft * ceiling_u * delta_t_heating
                cooling.ceiling = space.area_sqft * ceiling_u * delta_t_cooling
                
                # Floor - to garage (semi-buffered)
                garage_winter = envelope_properties.get('outdoor_winter', 0) + 10
                garage_summer = envelope_properties.get('outdoor_summer', 95) - 5
                
                floor_heating_delta = 70 - garage_winter
                floor_cooling_delta = garage_summer - 75
                
                heating.floor = space.area_sqft * floor_u * floor_heating_delta
                cooling.floor = space.area_sqft * floor_u * floor_cooling_delta
                
            else:
                # Standard space calculation
                heating.walls = net_wall_area * wall_u * delta_t_heating
                cooling.walls = net_wall_area * wall_u * delta_t_cooling
                
                heating.windows = window_area * window_u * delta_t_heating
                cooling.windows = window_area * window_u * delta_t_cooling
                
                # Ceiling/floor based on position
                if space.floor_level == 1:
                    # First floor - floor to ground/crawl
                    if space.floor_over == BoundaryCondition.CRAWLSPACE:
                        heating.floor = space.area_sqft * floor_u * delta_t_heating * 0.7
                        cooling.floor = space.area_sqft * floor_u * delta_t_cooling * 0.7
                    elif space.floor_over == BoundaryCondition.GROUND:
                        heating.floor = space.area_sqft * floor_u * delta_t_heating * 0.5
                        cooling.floor = 0
                    
                    # Ceiling to second floor (if exists)
                    if envelope_properties.get('floor_count', 1) > 1:
                        # Interior ceiling - no load
                        heating.ceiling = 0
                        cooling.ceiling = 0
                    else:
                        # Ceiling to attic
                        heating.ceiling = space.area_sqft * ceiling_u * delta_t_heating
                        cooling.ceiling = space.area_sqft * ceiling_u * delta_t_cooling
                        
                elif space.floor_level == 2:
                    # Second floor - ceiling to attic, floor to first floor
                    heating.ceiling = space.area_sqft * ceiling_u * delta_t_heating
                    cooling.ceiling = space.area_sqft * ceiling_u * delta_t_cooling
                    
                    # Floor to conditioned space below (no load unless over garage)
                    if space.is_over_garage:
                        garage_winter = envelope_properties.get('outdoor_winter', 0) + 10
                        garage_summer = envelope_properties.get('outdoor_summer', 95) - 5
                        
                        floor_heating_delta = 70 - garage_winter
                        floor_cooling_delta = garage_summer - 75
                        
                        heating.floor = space.area_sqft * floor_u * floor_heating_delta
                        cooling.floor = space.area_sqft * floor_u * floor_cooling_delta
        
        return heating, cooling
    
    def _calculate_zone_infiltration(
        self,
        zone: ThermalZone,
        delta_t: float,
        is_heating: bool,
        envelope_properties: Dict[str, Any],
        thermal_intelligence: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate infiltration load for zone"""
        
        # Get ACH50 from envelope
        ach50 = envelope_properties.get('ach50', 10.0)
        
        # Apply AI construction quality intelligence
        if thermal_intelligence:
            construction = thermal_intelligence.get('construction_method', {})
            quality = construction.get('thermal_mass', 'low')
            
            # Adjust infiltration based on AI assessment
            if quality == 'high':
                ach50 *= 0.8  # Better construction = tighter
            elif quality == 'low':
                ach50 *= 1.1  # Poorer construction = leakier
        
        # Convert to natural ACH
        # Using simplified LBL model
        ach_natural = ach50 / 20  # Typical conversion
        
        # Apply zone modifier (stack effect increases upper floor infiltration)
        zone_modifier = zone.get_infiltration_modifier(is_heating)
        ach_natural *= zone_modifier
        
        # Calculate CFM
        cfm = (ach_natural * zone.total_volume_cuft) / 60
        
        # Special handling for bonus zones
        if zone.is_bonus_zone:
            # Bonus rooms have more infiltration due to complex geometry
            cfm *= 1.2
        
        # Calculate sensible load
        # Q = 1.08 × CFM × ΔT
        sensible_load = 1.08 * cfm * abs(delta_t)
        
        return sensible_load
    
    def _calculate_internal_gains(self, zone: ThermalZone) -> Dict[str, float]:
        """Calculate internal gains for cooling"""
        
        gains = {
            'people': 0,
            'equipment': 0,
            'lighting': 0
        }
        
        # People gains
        total_occupants = sum(s.design_occupants for s in zone.spaces)
        if total_occupants == 0:
            # Estimate based on zone type
            if zone.zone_type == ZoneType.SLEEPING:
                total_occupants = len(zone.spaces) * 1.5  # 1.5 per bedroom
            elif zone.zone_type == ZoneType.MAIN_LIVING:
                total_occupants = 3  # Typical family
            elif zone.zone_type == ZoneType.BONUS:
                total_occupants = 2  # Occasional use
        
        gains['people'] = total_occupants * self.people_gain
        
        # Equipment gains
        equipment_watts = zone.total_area_sqft * self.equipment_w_per_sqft
        gains['equipment'] = equipment_watts * 3.412  # Convert W to BTU/hr
        
        # Lighting gains
        lighting_watts = zone.total_area_sqft * self.lighting_w_per_sqft
        gains['lighting'] = lighting_watts * 3.412
        
        # Apply diversity based on zone type
        if zone.zone_type == ZoneType.BONUS:
            # Bonus rooms have lower internal gains
            for key in gains:
                gains[key] *= 0.5
        elif zone.zone_type == ZoneType.SLEEPING:
            # Bedrooms have lower equipment/lighting during day
            gains['equipment'] *= 0.3
            gains['lighting'] *= 0.2
        
        return gains
    
    def _calculate_solar_gains(
        self,
        zone: ThermalZone,
        climate_data: Dict[str, Any],
        thermal_intelligence: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate solar heat gain for cooling"""
        
        total_solar = 0
        
        # Get window areas by orientation - use AI intelligence if available
        if thermal_intelligence and 'window_orientation' in thermal_intelligence:
            window_info = thermal_intelligence['window_orientation']
            
            # Use AI-detected window ratios
            total_window_area = zone.total_area_sqft * 0.18  # 18% total window-to-floor ratio
            window_distribution = {
                'N': total_window_area * window_info.get('north_facing_ratio', 0.2),
                'S': total_window_area * window_info.get('south_facing_ratio', 0.4),
                'E': total_window_area * (1 - window_info.get('south_facing_ratio', 0.4) - window_info.get('north_facing_ratio', 0.2)) * 0.5,
                'W': total_window_area * (1 - window_info.get('south_facing_ratio', 0.4) - window_info.get('north_facing_ratio', 0.2)) * 0.5
            }
            
            # Adjust solar factors based on AI solar exposure assessment
            solar_exposure = window_info.get('solar_exposure', 'medium')
            if solar_exposure == 'high':
                exposure_multiplier = 1.2
            elif solar_exposure == 'low':
                exposure_multiplier = 0.8
            else:
                exposure_multiplier = 1.0
        else:
            # Default window distribution
            window_distribution = {
                'N': zone.total_area_sqft * 0.03,   # 3% of floor area north
                'S': zone.total_area_sqft * 0.06,   # 6% south
                'E': zone.total_area_sqft * 0.045,  # 4.5% east
                'W': zone.total_area_sqft * 0.045   # 4.5% west
            }
            exposure_multiplier = 1.0
        
        # Calculate solar gain for each orientation
        for orientation, window_area in window_distribution.items():
            solar_factor = self.solar_factors[orientation] * exposure_multiplier
            shgc = 0.30  # Default SHGC
            
            # Solar gain = Area × SHGC × Solar Factor
            total_solar += window_area * shgc * solar_factor
        
        # Reduce solar for shaded bonus rooms
        if zone.is_bonus_zone:
            total_solar *= 0.7  # 30% shading from roof overhang
        
        return total_solar
    
    def _get_zone_heating_modifier(
        self,
        zone: ThermalZone,
        building_model: BuildingThermalModel
    ) -> float:
        """Get heating load modifier for zone"""
        
        modifier = 1.0
        
        # Bonus over garage needs extra capacity
        if zone.is_bonus_zone and zone.has_garage_below:
            modifier *= 1.3  # 30% extra per our analysis
            logger.info(f"Applying 30% bonus room heating modifier to {zone.name}")
        
        # Upper floors need slightly more due to stack effect
        elif zone.floor_level > 1:
            modifier *= 1.1  # 10% extra for upper floors
        
        # Zones with vaulted ceilings
        if any(s.has_cathedral_ceiling for s in zone.spaces):
            modifier *= 1.15  # 15% extra for cathedral ceilings
        
        return modifier
    
    def _get_zone_cooling_modifier(
        self,
        zone: ThermalZone,
        building_model: BuildingThermalModel
    ) -> float:
        """Get cooling load modifier for zone"""
        
        modifier = 1.0
        
        # Bonus rooms may not need full cooling if not primary occupied
        if zone.is_bonus_zone and not zone.primary_occupancy:
            modifier *= 0.7  # 70% cooling for non-primary bonus
            logger.info(f"Applying 70% cooling reduction to non-primary {zone.name}")
        
        # Upper floors need more cooling (heat rises)
        if zone.floor_level > 1:
            modifier *= 1.15  # 15% extra for upper floors
        
        # West-facing zones need more cooling
        # (This would be more sophisticated with actual orientation data)
        
        return modifier


# Singleton instance
_zone_calculator = None


def get_zone_load_calculator() -> ZoneLoadCalculator:
    """Get or create the global zone load calculator"""
    global _zone_calculator
    if _zone_calculator is None:
        _zone_calculator = ZoneLoadCalculator()
    return _zone_calculator