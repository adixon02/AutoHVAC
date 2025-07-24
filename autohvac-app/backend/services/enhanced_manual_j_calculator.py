"""
Enhanced Manual J Load Calculator
Component-by-component ACCA Manual J 8th Edition implementation
Following o3-model systematic approach for maximum accuracy
"""
import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ComponentLoad:
    """Individual component heat transfer calculation"""
    component_type: str  # "wall", "ceiling", "window", "infiltration", "internal", "solar"
    heating_btuh: float
    cooling_btuh: float
    area_ft2: Optional[float] = None
    u_factor: Optional[float] = None
    temp_diff: Optional[float] = None
    details: Dict[str, Any] = None

@dataclass
class RoomLoadBreakdown:
    """Detailed room load calculation with component breakdown"""
    room_name: str
    total_heating_btuh: float
    total_cooling_btuh: float
    components: List[ComponentLoad]
    geometry: Dict[str, float]  # dimensions, areas, volumes
    validation_flags: List[str] = None

@dataclass 
class SystemLoadCalculation:
    """Complete system load calculation with detailed breakdown"""
    project_id: str
    total_heating_btuh: float
    total_cooling_btuh: float
    heating_tons: float
    cooling_tons: float
    room_loads: List[RoomLoadBreakdown]
    climate_data: Dict[str, Any]
    building_characteristics: Dict[str, Any]
    calculation_assumptions: List[str]
    validation_results: Dict[str, Any]
    calculated_at: datetime

class EnhancedManualJCalculator:
    """
    ACCA Manual J 8th Edition compliant calculator
    Component-by-component approach with comprehensive validation
    """
    
    def __init__(self):
        self.constants = self._initialize_constants()
        logger.info("Enhanced Manual J Calculator initialized")
    
    def _initialize_constants(self) -> Dict[str, Any]:
        """Initialize Manual J constants following ACCA standards"""
        return {
            # Heat transfer coefficients
            "sensible_heat_factor": 1.08,  # BTU factor for sensible heat (CFM × ΔT)
            "latent_heat_factor": 0.68,    # BTU factor for latent heat (CFM × Δgr)
            
            # Solar heat gain factors (BTU/hr/ft² by orientation)
            "solar_factors": {
                "south": 180,    # Reduced for more realistic gain
                "east": 130,
                "west": 130, 
                "north": 35,
                "horizontal": 200  # Skylights
            },
            
            # Shade factors
            "shade_factors": {
                "none": 1.0,
                "partial": 0.8,
                "full": 0.6,
                "overhang": 0.7
            },
            
            # Internal gain defaults (BTU/hr)
            "occupant_sensible": 230,  # per person
            "occupant_latent": 200,    # per person  
            "lighting_factor": 3.412,  # watts to BTU/hr
            "equipment_factor": 3.412, # watts to BTU/hr
            
            # Safety and diversity factors - REDUCED to avoid compounding
            "safety_factors": {
                "heating": 1.00,  # No additional safety factor (included in component calcs)
                "cooling": 1.00   # No additional safety factor (included in component calcs)
            },
            
            "diversity_factors": {
                "heating": 1.00,  # No diversity reduction
                "cooling": 1.00   # No diversity reduction
            },
            
            # Distribution losses
            "duct_losses": {
                "heating": 1.15,  # 15% ductwork losses
                "cooling": 1.10   # 10% ductwork losses (reduced)
            },
            
            # Design conditions
            "indoor_conditions": {
                "heating_db": 70.0,  # °F
                "cooling_db": 75.0,  # °F
                "cooling_rh": 50.0   # % relative humidity
            },
            
            # Sherman-Grimsrud infiltration conversion
            "infiltration_conversion": {
                "n_factor": 17,  # Typical for tight construction
                "wind_factor": 0.67,
                "stack_factor": 0.33
            }
        }
    
    async def calculate_system_loads(
        self,
        project_id: str,
        building_data: Dict[str, Any],
        room_data: List[Dict[str, Any]],
        climate_data: Dict[str, Any]
    ) -> SystemLoadCalculation:
        """
        Calculate complete system loads with component-by-component breakdown
        
        Args:
            project_id: Project identifier
            building_data: Building envelope and characteristics
            room_data: Individual room data with dimensions and features
            climate_data: Climate design conditions
            
        Returns:
            SystemLoadCalculation with detailed component breakdown
        """
        try:
            logger.info(f"Starting enhanced Manual J calculation for project {project_id}")
            
            # Calculate design temperature differences
            design_temps = self._calculate_design_temperatures(climate_data)
            
            # Calculate room-by-room loads
            room_loads = []
            total_heating = 0.0
            total_cooling = 0.0
            
            for room in room_data:
                room_breakdown = await self._calculate_room_loads_detailed(
                    room, building_data, design_temps
                )
                room_loads.append(room_breakdown)
                
                total_heating += room_breakdown.total_heating_btuh
                total_cooling += room_breakdown.total_cooling_btuh
                
                logger.info(f"Room '{room_breakdown.room_name}': "
                          f"{room_breakdown.total_heating_btuh:.0f} heating, "
                          f"{room_breakdown.total_cooling_btuh:.0f} cooling BTU/hr")
            
            # Apply diversity factors
            total_heating *= self.constants["diversity_factors"]["heating"]
            total_cooling *= self.constants["diversity_factors"]["cooling"]
            
            # Apply duct losses
            total_heating *= self.constants["duct_losses"]["heating"]
            total_cooling *= self.constants["duct_losses"]["cooling"]
            
            # Apply safety factors
            total_heating *= self.constants["safety_factors"]["heating"]
            total_cooling *= self.constants["safety_factors"]["cooling"]
            
            # Apply minimum load requirements based on building area
            # ACCA Manual J suggests minimum 400 BTU/hr per 100 sq ft for heating
            # and 800 BTU/hr per 100 sq ft for cooling
            min_heating = building_data["floor_area_ft2"] * 4  # 4 BTU/hr/sq ft minimum
            min_cooling = building_data["floor_area_ft2"] * 8  # 8 BTU/hr/sq ft minimum
            
            total_heating = max(total_heating, min_heating)
            total_cooling = max(total_cooling, min_cooling)
            
            # Convert to tons
            heating_tons = total_heating / 12000
            cooling_tons = total_cooling / 12000
            
            # Perform validation
            validation_results = self._validate_load_calculations(
                total_heating, total_cooling, building_data
            )
            
            # Document assumptions
            assumptions = self._document_calculation_assumptions(building_data, climate_data)
            
            system_calculation = SystemLoadCalculation(
                project_id=project_id,
                total_heating_btuh=total_heating,
                total_cooling_btuh=total_cooling,
                heating_tons=heating_tons,
                cooling_tons=cooling_tons,
                room_loads=room_loads,
                climate_data=climate_data,
                building_characteristics=building_data,
                calculation_assumptions=assumptions,
                validation_results=validation_results,
                calculated_at=datetime.now()
            )
            
            logger.info(f"Enhanced Manual J complete: {heating_tons:.1f} tons heating, "
                       f"{cooling_tons:.1f} tons cooling")
            
            return system_calculation
            
        except Exception as e:
            logger.error(f"Enhanced Manual J calculation failed: {e}")
            raise
    
    def _calculate_design_temperatures(self, climate_data: Dict) -> Dict[str, float]:
        """Calculate heating and cooling design temperature differences"""
        outdoor_heating = climate_data.get("winter_design_temp", 5)  # Default for Spokane
        outdoor_cooling = climate_data.get("summer_design_temp", 89)
        
        heating_temp_diff = self.constants["indoor_conditions"]["heating_db"] - outdoor_heating
        cooling_temp_diff = outdoor_cooling - self.constants["indoor_conditions"]["cooling_db"]
        
        return {
            "heating_temp_diff": heating_temp_diff,
            "cooling_temp_diff": cooling_temp_diff,
            "outdoor_heating": outdoor_heating,
            "outdoor_cooling": outdoor_cooling
        }
    
    async def _calculate_room_loads_detailed(
        self,
        room: Dict[str, Any],
        building: Dict[str, Any],
        design_temps: Dict[str, float]
    ) -> RoomLoadBreakdown:
        """Calculate detailed room loads with component breakdown"""
        
        room_name = room.get("name", "Unknown Room")
        components = []
        
        # Room geometry
        room_area = room.get("area_ft2", room.get("area", 250))  # Default if missing
        ceiling_height = room.get("ceiling_height", building.get("ceiling_height", 9.0))
        room_volume = room_area * ceiling_height
        
        # Calculate wall loads
        wall_component = self._calculate_wall_loads(
            room, building, design_temps, room_area, ceiling_height
        )
        components.append(wall_component)
        
        # Calculate ceiling loads  
        ceiling_component = self._calculate_ceiling_loads(
            room, building, design_temps, room_area
        )
        components.append(ceiling_component)
        
        # Calculate window loads
        window_component = self._calculate_window_loads(
            room, building, design_temps
        )
        components.append(window_component)
        
        # Calculate solar gains
        solar_component = self._calculate_solar_gains(room, building)
        components.append(solar_component)
        
        # Calculate infiltration loads
        infiltration_component = self._calculate_infiltration_loads(
            room, building, design_temps, room_volume
        )
        components.append(infiltration_component)
        
        # Calculate internal gains
        internal_component = self._calculate_internal_gains(room, room_area)
        components.append(internal_component)
        
        # Sum component loads
        total_heating = sum(comp.heating_btuh for comp in components)
        total_cooling = sum(comp.cooling_btuh for comp in components)
        
        # Ensure non-negative loads
        total_heating = max(0, total_heating)
        total_cooling = max(0, total_cooling)
        
        # Geometry data for validation
        geometry = {
            "area_ft2": room_area,
            "ceiling_height": ceiling_height,
            "volume_ft3": room_volume,
            "perimeter_ft": room.get("perimeter_ft", 4 * math.sqrt(room_area))
        }
        
        # Validation flags
        validation_flags = self._validate_room_loads(
            room_name, total_heating, total_cooling, room_area
        )
        
        return RoomLoadBreakdown(
            room_name=room_name,
            total_heating_btuh=total_heating,
            total_cooling_btuh=total_cooling,
            components=components,
            geometry=geometry,
            validation_flags=validation_flags
        )
    
    def _calculate_wall_loads(
        self, 
        room: Dict, 
        building: Dict, 
        design_temps: Dict,
        room_area: float,
        ceiling_height: float
    ) -> ComponentLoad:
        """Calculate wall heat transfer loads"""
        
        # Get wall R-value from building data
        wall_insulation = building.get("wall_insulation", {})
        wall_r_value = wall_insulation.get("effective_r", 19)  # Default R-19
        wall_u_factor = 1.0 / wall_r_value
        
        # Calculate wall area using actual room dimensions if available
        if "perimeter_ft" in room:
            # Use actual perimeter
            perimeter = room["perimeter_ft"]
        elif "length_ft" in room and "width_ft" in room:
            # Calculate from dimensions
            perimeter = 2 * (room["length_ft"] + room["width_ft"])
        else:
            # Estimate from area (square room assumption)
            perimeter = 4 * math.sqrt(room_area)
        
        # Only exterior walls transfer heat
        exterior_wall_fraction = room.get("exterior_walls", 2) / 4  # Default 2 exterior walls
        wall_area = perimeter * ceiling_height * exterior_wall_fraction
        
        # Subtract window and door area
        window_area = room.get("window_area", room_area * 0.12)  # Default 12% of floor area
        door_area = room.get("door_area", 20)  # Default door area
        net_wall_area = max(0, wall_area - window_area - door_area)
        
        # Calculate heat transfer
        heating_btuh = net_wall_area * wall_u_factor * design_temps["heating_temp_diff"]
        cooling_btuh = net_wall_area * wall_u_factor * design_temps["cooling_temp_diff"]
        
        return ComponentLoad(
            component_type="wall",
            heating_btuh=heating_btuh,
            cooling_btuh=cooling_btuh,
            area_ft2=net_wall_area,
            u_factor=wall_u_factor,
            temp_diff=design_temps["heating_temp_diff"],
            details={
                "gross_wall_area": wall_area,
                "window_area_subtracted": window_area,
                "door_area_subtracted": door_area,
                "r_value": wall_r_value,
                "perimeter_ft": perimeter,
                "exterior_wall_fraction": exterior_wall_fraction
            }
        )
    
    def _calculate_ceiling_loads(
        self, 
        room: Dict, 
        building: Dict, 
        design_temps: Dict,
        room_area: float
    ) -> ComponentLoad:
        """Calculate ceiling/attic heat transfer loads"""
        
        # Get ceiling R-value from building data
        ceiling_r_value = building.get("ceiling_insulation", 38)  # Default R-38
        ceiling_u_factor = 1.0 / ceiling_r_value
        
        # Ceiling area equals floor area for typical construction
        ceiling_area = room_area
        
        # Calculate heat transfer
        heating_btuh = ceiling_area * ceiling_u_factor * design_temps["heating_temp_diff"]
        cooling_btuh = ceiling_area * ceiling_u_factor * design_temps["cooling_temp_diff"]
        
        return ComponentLoad(
            component_type="ceiling",
            heating_btuh=heating_btuh,
            cooling_btuh=cooling_btuh,
            area_ft2=ceiling_area,
            u_factor=ceiling_u_factor,
            temp_diff=design_temps["heating_temp_diff"],
            details={
                "r_value": ceiling_r_value,
                "assembly_type": "attic"
            }
        )
    
    def _calculate_window_loads(
        self, 
        room: Dict, 
        building: Dict, 
        design_temps: Dict
    ) -> ComponentLoad:
        """Calculate window heat transfer loads"""
        
        # Get window specifications
        window_schedule = building.get("window_schedule", {})
        window_u_factor = window_schedule.get("u_value", 0.30)  # Default energy code minimum
        
        # Window area
        window_area = room.get("window_area", room.get("area", 250) * 0.12)
        
        # Calculate conductive heat transfer
        heating_btuh = window_area * window_u_factor * design_temps["heating_temp_diff"]
        cooling_btuh = window_area * window_u_factor * design_temps["cooling_temp_diff"]
        
        return ComponentLoad(
            component_type="window",
            heating_btuh=heating_btuh,
            cooling_btuh=cooling_btuh,
            area_ft2=window_area,
            u_factor=window_u_factor,
            temp_diff=design_temps["heating_temp_diff"],
            details={
                "shgc": window_schedule.get("shgc", 0.65),
                "frame_type": "insulated",
                "glazing_layers": "double"
            }
        )
    
    def _calculate_solar_gains(self, room: Dict, building: Dict) -> ComponentLoad:
        """Calculate solar heat gains through windows"""
        
        window_schedule = building.get("window_schedule", {})
        shgc = window_schedule.get("shgc", 0.65)
        window_area = room.get("window_area", room.get("area", 250) * 0.12)
        
        # Determine window orientations if available
        window_orientations = room.get("window_orientations", ["south"])  # Default assumption
        shade_factor = self.constants["shade_factors"]["partial"]  # Assume partial shading
        
        total_solar_gain = 0.0
        for orientation in window_orientations:
            orientation_area = window_area / len(window_orientations)  # Distribute evenly
            solar_factor = self.constants["solar_factors"].get(orientation.lower(), 150)
            
            orientation_gain = orientation_area * shgc * solar_factor * shade_factor
            total_solar_gain += orientation_gain
        
        return ComponentLoad(
            component_type="solar",
            heating_btuh=0.0,  # Solar gain only affects cooling
            cooling_btuh=total_solar_gain,
            area_ft2=window_area,
            details={
                "shgc": shgc,
                "orientations": window_orientations,
                "shade_factor": shade_factor
            }
        )
    
    def _calculate_infiltration_loads(
        self, 
        room: Dict, 
        building: Dict, 
        design_temps: Dict,
        room_volume: float
    ) -> ComponentLoad:
        """Calculate infiltration air leakage loads"""
        
        # Get air tightness
        air_tightness = building.get("air_tightness", 5.0)  # Default 5 ACH50
        
        # Convert ACH50 to natural air changes using Sherman-Grimsrud
        n_factor = self.constants["infiltration_conversion"]["n_factor"]
        natural_ach = air_tightness / n_factor
        
        # Calculate infiltration CFM
        infiltration_cfm = (natural_ach * room_volume) / 60
        
        # Sensible load
        sensible_heating = infiltration_cfm * self.constants["sensible_heat_factor"] * design_temps["heating_temp_diff"]
        sensible_cooling = infiltration_cfm * self.constants["sensible_heat_factor"] * design_temps["cooling_temp_diff"]
        
        # Latent cooling load (assume 50% RH difference)
        latent_cooling = infiltration_cfm * self.constants["latent_heat_factor"] * 30  # grains moisture difference
        
        total_heating = sensible_heating
        total_cooling = sensible_cooling + latent_cooling
        
        return ComponentLoad(
            component_type="infiltration",
            heating_btuh=total_heating,
            cooling_btuh=total_cooling,
            details={
                "ach50": air_tightness,
                "natural_ach": natural_ach,
                "infiltration_cfm": infiltration_cfm,
                "sensible_heating": sensible_heating,
                "sensible_cooling": sensible_cooling,
                "latent_cooling": latent_cooling
            }
        )
    
    def _calculate_internal_gains(self, room: Dict, room_area: float) -> ComponentLoad:
        """Calculate internal heat gains from occupants, lighting, equipment"""
        
        # Occupant gains - more conservative estimate
        occupants = room.get("occupants", max(1, room_area // 300))  # 1 person per 300 sq ft
        occupant_sensible = occupants * self.constants["occupant_sensible"]
        occupant_latent = occupants * self.constants["occupant_latent"]
        
        # Lighting gains - modern LED lighting uses less power
        lighting_watts = room.get("lighting_watts", room_area * 0.5)  # 0.5 W/sq ft for LED
        lighting_gain = lighting_watts * self.constants["lighting_factor"]
        
        # Equipment gains - reduced for typical residential
        equipment_watts = room.get("equipment_watts", room_area * 0.3)  # 0.3 W/sq ft default
        equipment_gain = equipment_watts * self.constants["equipment_factor"]
        
        total_sensible = occupant_sensible + lighting_gain + equipment_gain
        total_latent = occupant_latent
        
        # Internal gains reduce heating load but only by a fraction (50% diversity)
        # This accounts for nighttime/unoccupied periods
        heating_credit = total_sensible * 0.5  # Only 50% credit for heating
        
        return ComponentLoad(
            component_type="internal",
            heating_btuh=-heating_credit,  # Reduced credit for heating
            cooling_btuh=total_sensible + total_latent,
            details={
                "occupants": occupants,
                "occupant_sensible": occupant_sensible,
                "occupant_latent": occupant_latent,
                "lighting_watts": lighting_watts,
                "lighting_gain": lighting_gain,
                "equipment_watts": equipment_watts,
                "equipment_gain": equipment_gain,
                "heating_credit_factor": 0.5
            }
        )
    
    def _validate_room_loads(
        self, 
        room_name: str, 
        heating_btuh: float, 
        cooling_btuh: float, 
        room_area: float
    ) -> List[str]:
        """Validate room loads against reasonable ranges"""
        
        validation_flags = []
        
        # Check heating load density (10-25 BTU/hr/sq ft typical)
        heating_density = heating_btuh / room_area if room_area > 0 else 0
        if heating_density < 10:
            validation_flags.append(f"Low heating density: {heating_density:.1f} BTU/hr/sq ft")
        elif heating_density > 25:
            validation_flags.append(f"High heating density: {heating_density:.1f} BTU/hr/sq ft")
        
        # Check cooling load density (15-35 BTU/hr/sq ft typical)
        cooling_density = cooling_btuh / room_area if room_area > 0 else 0
        if cooling_density < 15:
            validation_flags.append(f"Low cooling density: {cooling_density:.1f} BTU/hr/sq ft")
        elif cooling_density > 35:
            validation_flags.append(f"High cooling density: {cooling_density:.1f} BTU/hr/sq ft")
        
        return validation_flags
    
    def _validate_load_calculations(
        self, 
        total_heating: float, 
        total_cooling: float, 
        building_data: Dict
    ) -> Dict[str, Any]:
        """Validate total system loads"""
        
        floor_area = building_data.get("floor_area_ft2", 1500)
        heating_tons_per_1000 = (total_heating / 12000) / (floor_area / 1000)
        cooling_tons_per_1000 = (total_cooling / 12000) / (floor_area / 1000)
        
        validation = {
            "heating_density_btuh_sqft": total_heating / floor_area,
            "cooling_density_btuh_sqft": total_cooling / floor_area,
            "heating_tons_per_1000sqft": heating_tons_per_1000,
            "cooling_tons_per_1000sqft": cooling_tons_per_1000,
            "warnings": []
        }
        
        # Typical ranges: 0.5-1.5 tons per 1000 sq ft
        if heating_tons_per_1000 < 0.5:
            validation["warnings"].append("Heating load may be too low")
        elif heating_tons_per_1000 > 1.5:
            validation["warnings"].append("Heating load may be too high")
            
        if cooling_tons_per_1000 < 0.8:
            validation["warnings"].append("Cooling load may be too low") 
        elif cooling_tons_per_1000 > 1.8:
            validation["warnings"].append("Cooling load may be too high")
        
        return validation
    
    def _document_calculation_assumptions(
        self, 
        building_data: Dict, 
        climate_data: Dict
    ) -> List[str]:
        """Document all assumptions made in calculation"""
        
        assumptions = [
            f"Indoor design conditions: {self.constants['indoor_conditions']['heating_db']}°F heating, {self.constants['indoor_conditions']['cooling_db']}°F cooling",
            f"Outdoor design conditions: {climate_data.get('winter_design_temp', 5)}°F heating, {climate_data.get('summer_design_temp', 89)}°F cooling",
            f"Safety factors: {self.constants['safety_factors']['heating']*100-100:.0f}% heating, {self.constants['safety_factors']['cooling']*100-100:.0f}% cooling",
            f"Diversity factors: {self.constants['diversity_factors']['heating']*100:.0f}% heating, {self.constants['diversity_factors']['cooling']*100:.0f}% cooling",
            f"Duct losses: {self.constants['duct_losses']['heating']*100-100:.0f}% heating, {self.constants['duct_losses']['cooling']*100-100:.0f}% cooling"
        ]
        
        # Add building-specific assumptions
        if not building_data.get("wall_insulation"):
            assumptions.append("Wall insulation: Assumed R-19 (no data extracted)")
            
        if not building_data.get("ceiling_insulation"):
            assumptions.append("Ceiling insulation: Assumed R-38 (no data extracted)")
            
        if not building_data.get("window_schedule"):
            assumptions.append("Windows: Assumed U-0.30, SHGC-0.65 (energy code minimum)")
            
        if not building_data.get("air_tightness"):
            assumptions.append("Air tightness: Assumed 5 ACH50 (typical construction)")
        
        return assumptions