"""
ACCA Manual J Calculator V2
Complete implementation following ACCA Manual J 8th Edition
Uses all extracted data for accurate load calculations
"""

import logging
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np

from domain.core.thermal_envelope import ThermalModel, ThermalZone
from domain.calculations.infiltration_aim2 import AIM2InfiltrationModel, BuildingLeakage, InfiltrationFactors
from domain.calculations.parallel_path import get_parallel_path_calculator
from infrastructure.extractors.foundation import FoundationExtractor
from infrastructure.extractors.mechanical import MechanicalExtractor

logger = logging.getLogger(__name__)


@dataclass
class LoadComponents:
    """Detailed breakdown of heating/cooling loads"""
    # Envelope loads
    walls: float = 0
    windows_conduction: float = 0
    windows_solar: float = 0
    doors: float = 0
    roof: float = 0
    floor: float = 0
    foundation: float = 0
    
    # Infiltration/Ventilation
    infiltration_sensible: float = 0
    infiltration_latent: float = 0
    ventilation_sensible: float = 0
    ventilation_latent: float = 0
    
    # Internal gains (cooling only)
    people_sensible: float = 0
    people_latent: float = 0
    equipment: float = 0
    lighting: float = 0
    
    # Duct losses
    duct_loss: float = 0
    
    @property
    def total_sensible(self) -> float:
        """Total sensible load"""
        return sum([
            self.walls, self.windows_conduction, self.windows_solar,
            self.doors, self.roof, self.floor, self.foundation,
            self.infiltration_sensible, self.ventilation_sensible,
            self.people_sensible, self.equipment, self.lighting,
            self.duct_loss
        ])
    
    @property
    def total_latent(self) -> float:
        """Total latent load"""
        return sum([
            self.infiltration_latent, self.ventilation_latent,
            self.people_latent
        ])
    
    @property
    def total(self) -> float:
        """Total load"""
        return self.total_sensible + self.total_latent


@dataclass  
class ManualJResults:
    """Complete Manual J calculation results"""
    heating_load_btu_hr: float
    cooling_load_btu_hr: float
    heating_tons: float
    cooling_tons: float
    
    # Detailed breakdown
    heating_components: LoadComponents
    cooling_components: LoadComponents
    
    # Zone-by-zone loads
    zone_loads: Dict[str, Dict[str, float]]
    
    # System requirements
    required_cfm: float
    required_heating_capacity: float
    required_cooling_capacity: float
    
    # Metrics
    heating_load_per_sqft: float
    cooling_load_per_sqft: float
    sensible_heat_ratio: float
    
    # Validation
    confidence_score: float
    warnings: List[str]


class ManualJCalculatorV2:
    """
    Complete ACCA Manual J 8th Edition implementation
    Uses all properly extracted data for accurate calculations
    """
    
    # ASHRAE solar gain factors (BTU/hr·ft²)
    SOLAR_GAIN_FACTORS = {
        # By orientation and latitude
        'N': {'low': 20, 'mid': 25, 'high': 30},
        'S': {'low': 100, 'mid': 85, 'high': 70},
        'E': {'low': 80, 'mid': 75, 'high': 70},
        'W': {'low': 80, 'mid': 75, 'high': 70},
        'NE': {'low': 45, 'mid': 50, 'high': 55},
        'NW': {'low': 45, 'mid': 50, 'high': 55},
        'SE': {'low': 75, 'mid': 70, 'high': 65},
        'SW': {'low': 75, 'mid': 70, 'high': 65},
        'H': {'low': 200, 'mid': 180, 'high': 160},  # Horizontal (roof)
    }
    
    # Internal gain schedules (ASHRAE)
    INTERNAL_GAINS = {
        'people_sensible': 230,  # BTU/hr per person
        'people_latent': 200,    # BTU/hr per person
        'equipment': 2.56,        # BTU/hr per sqft (0.75 W/sqft × 3.41 = residential standard)
        'lighting': 0.75,         # W/sqft (residential standard, not commercial)
    }
    
    # Cooling Load Temperature Differences (CLTD)
    ROOF_CLTD = {
        # By roof type and design temp difference
        'light': 25,   # Light color roof
        'medium': 30,  # Medium color
        'dark': 40,    # Dark color roof
    }
    
    def __init__(self):
        self.aim2_model = AIM2InfiltrationModel()
        self.foundation_extractor = FoundationExtractor()
        self.mechanical_extractor = MechanicalExtractor()
        self.parallel_path = get_parallel_path_calculator()
        
    def calculate(
        self,
        thermal_model: ThermalModel,
        design_conditions: Optional[Dict[str, Any]] = None
    ) -> ManualJResults:
        """
        Calculate heating and cooling loads per ACCA Manual J
        
        Args:
            thermal_model: Complete thermal model from ThermalEnvelopeBuilder
            design_conditions: Override design temperatures if needed
            
        Returns:
            Complete Manual J results with detailed breakdown
        """
        logger.info("=== ACCA Manual J V2 Calculation Starting ===")
        logger.info(f"Building: {thermal_model.envelope.total_area_sqft:.0f} sqft, "
                   f"{thermal_model.envelope.number_of_floors} floors")
        
        # 1. Get design conditions
        conditions = self._get_design_conditions(thermal_model, design_conditions)
        logger.info(f"Design conditions: {conditions['winter_outdoor']}°F winter, "
                   f"{conditions['summer_outdoor']}°F summer")
        
        # 2. Calculate zone-by-zone loads
        zone_loads = {}
        total_heating_components = LoadComponents()
        total_cooling_components = LoadComponents()
        
        for zone in thermal_model.zones:
            heating, cooling = self._calculate_zone_loads(
                zone, thermal_model, conditions
            )
            
            zone_loads[zone.zone_id] = {
                'heating': heating.total,
                'cooling': cooling.total,
                'name': zone.name
            }
            
            # Accumulate totals
            self._accumulate_loads(total_heating_components, heating)
            self._accumulate_loads(total_cooling_components, cooling)
        
        # 3. Calculate whole-building loads (not zone sums)
        # These don't scale linearly with zones
        
        # Foundation loads
        foundation_heating, foundation_cooling = self._calculate_foundation_loads(
            thermal_model, conditions
        )
        total_heating_components.foundation = foundation_heating
        total_cooling_components.foundation = foundation_cooling
        
        # Infiltration (whole building)
        infil_heating, infil_cooling = self._calculate_infiltration_loads(
            thermal_model, conditions
        )
        total_heating_components.infiltration_sensible = infil_heating['sensible']
        total_heating_components.infiltration_latent = 0  # No latent in heating
        total_cooling_components.infiltration_sensible = infil_cooling['sensible']
        total_cooling_components.infiltration_latent = infil_cooling['latent']
        
        # Ventilation (whole building)
        vent_heating, vent_cooling = self._calculate_ventilation_loads(
            thermal_model, conditions
        )
        total_heating_components.ventilation_sensible = vent_heating
        total_cooling_components.ventilation_sensible = vent_cooling['sensible']
        total_cooling_components.ventilation_latent = vent_cooling['latent']
        
        # 4. Apply duct losses
        duct_factor_heating, duct_factor_cooling = self._get_duct_factors(thermal_model)
        
        # Calculate subtotals before duct losses
        heating_subtotal = total_heating_components.total
        cooling_subtotal = total_cooling_components.total
        
        # Duct losses
        total_heating_components.duct_loss = heating_subtotal * (duct_factor_heating - 1.0)
        total_cooling_components.duct_loss = cooling_subtotal * (duct_factor_cooling - 1.0)
        
        # 5. Final totals
        total_heating = total_heating_components.total
        total_cooling = total_cooling_components.total
        
        # 6. Apply safety factors (per ACCA guidelines)
        safety_heating = 1.10  # Up to 140% allowed for heating
        safety_cooling = 1.00  # 95-115% for cooling (we're at 100%)
        
        final_heating = total_heating * safety_heating
        final_cooling = total_cooling * safety_cooling
        
        # 7. Calculate system requirements
        heating_tons = final_heating / 12000
        cooling_tons = final_cooling / 12000
        required_cfm = cooling_tons * 400  # 400 CFM/ton typical
        
        # 8. Calculate metrics
        heating_per_sqft = final_heating / thermal_model.envelope.total_area_sqft
        cooling_per_sqft = final_cooling / thermal_model.envelope.total_area_sqft
        
        shr = (total_cooling_components.total_sensible / 
               total_cooling_components.total if total_cooling_components.total > 0 else 1.0)
        
        # 9. Validation and warnings
        warnings = self._validate_results(
            final_heating, final_cooling, thermal_model
        )
        
        # 10. Calculate confidence
        confidence = self._calculate_confidence(thermal_model, warnings)
        
        results = ManualJResults(
            heating_load_btu_hr=final_heating,
            cooling_load_btu_hr=final_cooling,
            heating_tons=heating_tons,
            cooling_tons=cooling_tons,
            heating_components=total_heating_components,
            cooling_components=total_cooling_components,
            zone_loads=zone_loads,
            required_cfm=required_cfm,
            required_heating_capacity=final_heating,
            required_cooling_capacity=final_cooling,
            heating_load_per_sqft=heating_per_sqft,
            cooling_load_per_sqft=cooling_per_sqft,
            sensible_heat_ratio=shr,
            confidence_score=confidence,
            warnings=warnings
        )
        
        logger.info(f"=== Manual J Complete ===")
        logger.info(f"Heating: {final_heating:,.0f} BTU/hr ({heating_tons:.1f} tons)")
        logger.info(f"Cooling: {final_cooling:,.0f} BTU/hr ({cooling_tons:.1f} tons)")
        logger.info(f"Per sqft: {heating_per_sqft:.1f} heating, {cooling_per_sqft:.1f} cooling")
        logger.info(f"Confidence: {confidence:.1%}")
        
        if warnings:
            logger.warning(f"Warnings: {', '.join(warnings)}")
        
        return results
    
    def _get_design_conditions(
        self,
        model: ThermalModel,
        overrides: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get design conditions from climate data"""
        climate = model.climate_data
        
        conditions = {
            'winter_outdoor': climate.get('winter_99', 10),
            'summer_outdoor': climate.get('summer_1', 95),
            'summer_wetbulb': climate.get('summer_wb', 75),
            'winter_indoor': 70,
            'summer_indoor': 75,
            'indoor_rh': 0.50,
            'latitude': self._get_latitude_band(climate.get('climate_zone', '4A'))
        }
        
        if overrides:
            conditions.update(overrides)
        
        return conditions
    
    def _calculate_zone_loads(
        self,
        zone: ThermalZone,
        model: ThermalModel,
        conditions: Dict
    ) -> Tuple[LoadComponents, LoadComponents]:
        """Calculate loads for a single zone"""
        heating = LoadComponents()
        cooling = LoadComponents()
        
        # Temperature differences
        delta_t_heating = conditions['winter_indoor'] - conditions['winter_outdoor']
        delta_t_cooling = conditions['summer_outdoor'] - conditions['summer_indoor']
        
        # 1. WALLS - Using PARALLEL PATH for accurate U-value
        wall_area = sum(w.get('area', 0) for w in zone.exterior_walls)
        if wall_area == 0:
            # Estimate from zone area and perimeter
            wall_area = math.sqrt(zone.area_sqft) * 4 * 9  # Rough estimate
        
        # CRITICAL FIX: Use parallel path calculation for framing effects
        # The critique specifically requires this for accurate wall U-values
        nominal_r = model.envelope.wall_r_value
        
        # Determine framing type based on R-value
        if nominal_r >= 19:
            framing_type = '16oc_2x6'  # 2x6 wall for R-19+
        else:
            framing_type = '16oc_2x4'  # 2x4 wall for R-13
        
        # Calculate effective U-value with thermal bridging
        wall_u_effective = self.parallel_path.calculate_wall_u_value(
            nominal_r_value=nominal_r - 2,  # Subtract for films/sheathing already in calc
            framing_type=framing_type,
            is_steel=False  # Wood framing typical
        )
        
        heating.walls = wall_u_effective * wall_area * delta_t_heating
        cooling.walls = wall_u_effective * wall_area * delta_t_cooling
        
        # 2. WINDOWS - Conduction
        window_area = sum(w.get('area', 0) for w in zone.windows)
        if window_area == 0:
            window_area = zone.area_sqft * 0.15  # 15% window-to-floor
        
        window_u = zone.window_u_value
        heating.windows_conduction = window_u * window_area * delta_t_heating
        cooling.windows_conduction = window_u * window_area * delta_t_cooling
        
        # 3. WINDOWS - Solar Gain (cooling only)
        for window in zone.windows:
            orientation = window.get('orientation', 'S')
            area = window.get('area', 20)
            shgc = window.get('shgc', zone.window_shgc)
            
            # Get solar gain factor
            solar_factor = self._get_solar_factor(orientation, conditions['latitude'])
            
            # Apply shading coefficient and SHGC
            shading_coef = 0.85  # Typical interior shades
            cooling.windows_solar += area * solar_factor * shgc * shading_coef
        
        # 4. DOORS
        door_area = sum(d.get('area', 20) for d in zone.doors)
        door_u = 0.20  # Insulated door
        heating.doors = door_u * door_area * delta_t_heating
        cooling.doors = door_u * door_area * delta_t_cooling
        
        # 5. CEILING/ROOF (top floor only) - Using PARALLEL PATH
        if zone.ceiling:
            roof_area = zone.ceiling['area']
            
            # CRITICAL FIX: Use parallel path for ceiling/attic interface
            roof_u_effective = self.parallel_path.calculate_ceiling_u_value(
                nominal_r_value=model.envelope.roof_r_value - 1.5,  # Subtract films
                joist_spacing='24oc',  # Typical for ceilings
                joist_depth=10  # 2x10 joists typical
            )
            
            heating.roof = roof_u_effective * roof_area * delta_t_heating
            
            # Cooling uses CLTD for solar gain on roof
            roof_cltd = self.ROOF_CLTD['medium'] + delta_t_cooling
            cooling.roof = roof_u_effective * roof_area * roof_cltd
        
        # 6. FLOOR (ground floor handled in foundation)
        if zone.floor and zone.floor_number > 1:
            # Floor over conditioned space - no load
            pass
        
        # 7. INTERNAL GAINS (cooling only)
        cooling.people_sensible = zone.occupancy * self.INTERNAL_GAINS['people_sensible']
        cooling.people_latent = zone.occupancy * self.INTERNAL_GAINS['people_latent']
        cooling.equipment = zone.area_sqft * self.INTERNAL_GAINS['equipment']
        cooling.lighting = zone.lighting_load_w * 3.41  # Convert W to BTU/hr
        
        return heating, cooling
    
    def _calculate_foundation_loads(
        self,
        model: ThermalModel,
        conditions: Dict
    ) -> Tuple[float, float]:
        """Calculate foundation heat loss/gain"""
        if not model.foundation_data:
            # Use simplified calculation
            return self._calculate_simple_foundation(model, conditions)
        
        delta_t_heating = conditions['winter_indoor'] - conditions['winter_outdoor']
        delta_t_cooling = conditions['summer_outdoor'] - conditions['summer_indoor']
        
        # Use foundation extractor's proper calculation
        heating_loss = self.foundation_extractor.calculate_heat_loss(
            model.foundation_data,
            delta_t_heating,
            is_heating=True
        )
        
        # Minimal cooling loss through foundation
        cooling_loss = self.foundation_extractor.calculate_heat_loss(
            model.foundation_data,
            delta_t_cooling * 0.5,  # Ground buffers temperature
            is_heating=False
        )
        
        logger.debug(f"Foundation loads: {heating_loss:.0f} heating, {cooling_loss:.0f} cooling")
        
        return heating_loss, cooling_loss
    
    def _calculate_simple_foundation(
        self,
        model: ThermalModel,
        conditions: Dict
    ) -> Tuple[float, float]:
        """Simplified foundation calculation"""
        delta_t_heating = conditions['winter_indoor'] - conditions['winter_outdoor']
        
        if model.envelope.foundation_type == 'slab':
            # F-factor method
            f_factor = model.envelope.slab_f_factor
            perimeter = model.envelope.slab_perimeter_ft
            heating = f_factor * perimeter * delta_t_heating
            cooling = 0  # Minimal cooling through slab
            
        elif model.envelope.foundation_type == 'basement':
            # Below-grade walls
            u_factor = model.envelope.basement_u_factor
            area = model.envelope.basement_wall_area_sqft
            heating = u_factor * area * delta_t_heating * 0.7  # Ground buffering
            cooling = 0
            
        else:  # Crawlspace
            # Floor over crawl
            u_factor = 1.0 / model.envelope.floor_r_value
            area = model.envelope.floor_area_sqft
            heating = u_factor * area * delta_t_heating
            cooling = u_factor * area * (conditions['summer_outdoor'] - conditions['summer_indoor']) * 0.5
        
        return heating, cooling
    
    def _calculate_infiltration_loads(
        self,
        model: ThermalModel,
        conditions: Dict
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Calculate infiltration using AIM-2 model"""
        
        # Create building leakage profile
        building = BuildingLeakage(
            blower_door_cfm50=(model.envelope.ach50 * model.envelope.total_volume_cuft) / 60,
            ach50=model.envelope.ach50,
            ela=model.envelope.ela_sqin,
            leakage_class='average',  # Could be determined from ACH50
            envelope_area_sqft=model.envelope.gross_wall_area_sqft + model.envelope.roof_area_sqft,
            volume_cuft=model.envelope.total_volume_cuft,
            neutral_level=0.5
        )
        
        # Winter infiltration
        winter_factors = InfiltrationFactors(
            wind_speed_mph=15,  # Typical design wind
            indoor_temp_f=conditions['winter_indoor'],
            outdoor_temp_f=conditions['winter_outdoor'],
            terrain_class='suburban',
            shielding_class='moderate',
            building_height_ft=model.envelope.building_height_ft
        )
        
        winter_results = self.aim2_model.calculate_infiltration(
            building, winter_factors
        )
        
        # Summer infiltration (less due to smaller ΔT)
        summer_factors = InfiltrationFactors(
            wind_speed_mph=10,
            indoor_temp_f=conditions['summer_indoor'],
            outdoor_temp_f=conditions['summer_outdoor'],
            terrain_class='suburban',
            shielding_class='moderate',
            building_height_ft=model.envelope.building_height_ft
        )
        
        summer_results = self.aim2_model.calculate_infiltration(
            building, summer_factors
        )
        
        # Calculate loads
        heating_load = {
            'sensible': winter_results.sensible_load_btu_hr,
            'latent': 0  # No latent in heating
        }
        
        cooling_load = {
            'sensible': summer_results.sensible_load_btu_hr,
            'latent': self._calculate_latent_infiltration(
                summer_results.infiltration_cfm,
                conditions
            )
        }
        
        logger.debug(f"Infiltration: {winter_results.infiltration_cfm:.0f} CFM winter, "
                    f"{summer_results.infiltration_cfm:.0f} CFM summer")
        
        return heating_load, cooling_load
    
    def _calculate_latent_infiltration(
        self,
        cfm: float,
        conditions: Dict
    ) -> float:
        """Calculate latent infiltration load"""
        # Humidity ratios (simplified)
        w_indoor = 0.0095  # 75°F @ 50% RH
        w_outdoor = 0.014   # Summer design
        
        delta_w = max(0, w_outdoor - w_indoor)
        
        # Q_latent = 4840 × CFM × ΔW
        return 4840 * cfm * delta_w
    
    def _calculate_ventilation_loads(
        self,
        model: ThermalModel,
        conditions: Dict
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate mechanical ventilation loads"""
        
        if model.mechanical_data and model.mechanical_data.ventilation_system:
            vent = model.mechanical_data.ventilation_system
            cfm = vent.ventilation_rate_cfm
            recovery_eff = vent.heat_recovery_efficiency
        else:
            # ASHRAE 62.2 minimum
            cfm = model.envelope.total_area_sqft * 0.03 + 22.5  # 3 bedrooms assumed
            recovery_eff = 0  # No heat recovery
        
        # Temperature differences
        delta_t_heating = conditions['winter_indoor'] - conditions['winter_outdoor']
        delta_t_cooling = conditions['summer_outdoor'] - conditions['summer_indoor']
        
        # Apply heat recovery
        effective_delta_t_heating = delta_t_heating * (1 - recovery_eff)
        effective_delta_t_cooling = delta_t_cooling * (1 - recovery_eff)
        
        # Sensible loads
        heating_load = 1.08 * cfm * effective_delta_t_heating
        
        cooling_sensible = 1.08 * cfm * effective_delta_t_cooling
        cooling_latent = self._calculate_latent_infiltration(cfm, conditions) * (1 - recovery_eff)
        
        cooling_load = {
            'sensible': cooling_sensible,
            'latent': cooling_latent
        }
        
        logger.debug(f"Ventilation: {cfm:.0f} CFM, {recovery_eff:.0%} heat recovery")
        
        return heating_load, cooling_load
    
    def _get_duct_factors(self, model: ThermalModel) -> Tuple[float, float]:
        """Get duct loss factors"""
        if model.mechanical_data and model.mechanical_data.duct_system:
            duct = model.mechanical_data.duct_system
            
            # Use mechanical extractor's calculation
            delta_t_heating = 70 - model.climate_data.get('winter_99', 10)
            delta_t_cooling = model.climate_data.get('summer_1', 95) - 75
            
            return self.mechanical_extractor.calculate_duct_losses(
                duct, delta_t_heating, delta_t_cooling
            )
        
        # Default factors by location
        return 1.10, 1.12  # 10% heating, 12% cooling typical
    
    def _get_solar_factor(self, orientation: str, latitude: str) -> float:
        """Get solar gain factor by orientation and latitude"""
        factors = self.SOLAR_GAIN_FACTORS.get(orientation, self.SOLAR_GAIN_FACTORS['S'])
        return factors.get(latitude, factors['mid'])
    
    def _get_latitude_band(self, climate_zone: str) -> str:
        """Determine latitude band from climate zone"""
        zone_num = int(climate_zone[0]) if climate_zone and climate_zone[0].isdigit() else 4
        
        if zone_num <= 2:
            return 'low'  # Southern US
        elif zone_num >= 6:
            return 'high'  # Northern US
        else:
            return 'mid'  # Middle US
    
    def _accumulate_loads(self, total: LoadComponents, zone: LoadComponents):
        """Accumulate zone loads into total"""
        total.walls += zone.walls
        total.windows_conduction += zone.windows_conduction
        total.windows_solar += zone.windows_solar
        total.doors += zone.doors
        total.roof += zone.roof
        total.floor += zone.floor
        total.people_sensible += zone.people_sensible
        total.people_latent += zone.people_latent
        total.equipment += zone.equipment
        total.lighting += zone.lighting
    
    def _validate_results(
        self,
        heating: float,
        cooling: float,
        model: ThermalModel
    ) -> List[str]:
        """Validate calculation results"""
        warnings = []
        
        area = model.envelope.total_area_sqft
        
        # Check heating load
        heating_per_sqft = heating / area
        if heating_per_sqft < 10:
            warnings.append(f"Low heating load: {heating_per_sqft:.1f} BTU/sqft")
        elif heating_per_sqft > 60:
            warnings.append(f"High heating load: {heating_per_sqft:.1f} BTU/sqft")
        
        # Check cooling load
        cooling_per_sqft = cooling / area
        if cooling_per_sqft < 8:
            warnings.append(f"Low cooling load: {cooling_per_sqft:.1f} BTU/sqft")
        elif cooling_per_sqft > 40:
            warnings.append(f"High cooling load: {cooling_per_sqft:.1f} BTU/sqft")
        
        # Check tonnage
        cooling_tons = cooling / 12000
        tons_per_sqft = cooling_tons / area * 1000
        if tons_per_sqft < 300:  # Less than 300 sqft/ton
            warnings.append(f"High cooling tonnage: {tons_per_sqft:.0f} sqft/ton")
        elif tons_per_sqft > 800:  # More than 800 sqft/ton
            warnings.append(f"Low cooling tonnage: {tons_per_sqft:.0f} sqft/ton")
        
        return warnings
    
    def _calculate_confidence(
        self,
        model: ThermalModel,
        warnings: List[str]
    ) -> float:
        """Calculate confidence in results"""
        confidence = model.confidence_score  # Start with model confidence
        
        # Reduce for warnings
        confidence *= (0.95 ** len(warnings))
        
        # Boost for good data sources
        if model.foundation_data:
            confidence *= 1.05
        
        if model.mechanical_data:
            confidence *= 1.05
        
        # Cap at 0.95
        return min(0.95, confidence)


# Module-level calculator instance
_calculator_v2 = None


def get_calculator_v2() -> ManualJCalculatorV2:
    """Get or create the global calculator"""
    global _calculator_v2
    if _calculator_v2 is None:
        _calculator_v2 = ManualJCalculatorV2()
    return _calculator_v2


def get_manual_j_calculator() -> ManualJCalculatorV2:
    """Alias for get_calculator_v2 - used by pipeline_v3"""
    return get_calculator_v2()