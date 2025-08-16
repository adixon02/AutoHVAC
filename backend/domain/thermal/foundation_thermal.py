"""
Foundation Thermal Modeling Module

Implements ACCA Manual J foundation heat loss calculations per industry standards.
Provides accurate thermal modeling for different foundation types based on:
- ACCA Manual J 8th Edition
- ASHRAE Fundamentals Handbook  
- Building science best practices

Foundation Types Supported:
- Slab-on-grade (slab_only)
- Crawl space (crawlspace) 
- Basement with slab (basement_with_slab)
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass
import math


@dataclass
class FoundationThermalResult:
    """Result of foundation thermal calculations"""
    foundation_type: str
    effective_r_value: float
    thermal_conductance: float  # BTU/hr/°F/sqft
    perimeter_factor: float
    below_grade_factor: float
    notes: str


class FoundationThermalCalculator:
    """
    World-class foundation thermal modeling following ACCA Manual J standards.
    
    Calculates foundation heat loss based on:
    1. Foundation type and construction
    2. Climate zone conditions
    3. Soil thermal properties
    4. Building geometry
    """
    
    def __init__(self):
        # ACCA Manual J foundation thermal factors
        self.soil_thermal_conductivity = 1.0  # BTU/hr/ft/°F (typical soil)
        self.ground_temperature_offset = 10  # °F warmer than outdoor design temp
        
        # Foundation construction thermal properties (ACCA Manual J defaults)
        self.foundation_thermal_properties = {
            'slab_only': {
                'slab_thickness': 4,  # inches
                'slab_r_value': 0.8,  # R-value of 4" concrete
                'edge_insulation_r': 0,  # Default: no edge insulation
                'perimeter_insulation_depth': 0,  # inches
                'carpet_r_value': 2.0,  # Typical floor covering
                'thermal_bridging_factor': 1.15,  # 15% degradation from slab edge thermal bridging
            },
            'crawlspace': {
                'floor_r_value': 19,  # IECC minimum for Zone 5B (gets overridden by extraction)
                'wall_r_value': 3,  # REALISTIC: Most crawlspaces have minimal/no wall insulation
                'ventilation_rate': 2.5,  # REALISTIC: Higher due to code requirements and leakage
                'height': 4,  # feet (typical crawl space height)
                'thermal_bridging_factor': 1.25,  # 25% degradation from thermal bridging
            },
            'basement_with_slab': {
                'wall_r_value': 8,  # REALISTIC: Most basements have minimal wall insulation
                'slab_r_value': 0.8,  # Basement floor
                'depth': 8,  # feet below grade
                'above_grade_height': 2,  # feet above grade
                'thermal_bridging_factor': 1.20,  # 20% degradation from rim joist and wall thermal bridging
            }
        }
    
    def calculate_foundation_thermal_factors(
        self,
        foundation_type: str,
        climate_zone: str,
        winter_design_temp: float,
        building_area_sqft: float,
        building_perimeter_ft: float = None
    ) -> FoundationThermalResult:
        """
        Calculate foundation thermal factors per ACCA Manual J standards.
        
        Args:
            foundation_type: 'slab_only', 'crawlspace', 'basement_with_slab'
            climate_zone: IECC climate zone (e.g., '5B')
            winter_design_temp: 99% heating design temperature (°F)
            building_area_sqft: Conditioned floor area
            building_perimeter_ft: Building perimeter (estimated if not provided)
            
        Returns:
            FoundationThermalResult with thermal factors
        """
        # Estimate perimeter if not provided (assume rectangular building)
        if building_perimeter_ft is None:
            # Assume aspect ratio of 1.5:1 for typical residential
            width = math.sqrt(building_area_sqft / 1.5)
            length = width * 1.5
            building_perimeter_ft = 2 * (width + length)
        
        # Ground temperature (warmer than air due to thermal mass)
        ground_temp = winter_design_temp + self.ground_temperature_offset
        
        if foundation_type == 'slab_only':
            return self._calculate_slab_thermal_factors(
                climate_zone, winter_design_temp, ground_temp,
                building_area_sqft, building_perimeter_ft
            )
        elif foundation_type == 'crawlspace':
            return self._calculate_crawlspace_thermal_factors(
                climate_zone, winter_design_temp, ground_temp,
                building_area_sqft, building_perimeter_ft
            )
        elif foundation_type == 'basement_with_slab':
            return self._calculate_basement_thermal_factors(
                climate_zone, winter_design_temp, ground_temp,
                building_area_sqft, building_perimeter_ft
            )
        else:
            # Fallback to generic calculation
            return FoundationThermalResult(
                foundation_type=foundation_type,
                effective_r_value=10.0,
                thermal_conductance=0.1,
                perimeter_factor=1.0,
                below_grade_factor=1.0,
                notes="Generic foundation thermal factors applied"
            )
    
    def _calculate_slab_thermal_factors(
        self,
        climate_zone: str,
        winter_design_temp: float,
        ground_temp: float,
        area_sqft: float,
        perimeter_ft: float
    ) -> FoundationThermalResult:
        """
        ACCA Manual J slab-on-grade thermal calculation.
        
        Heat loss occurs primarily at slab edge where thermal bridging is highest.
        Interior slab is well-coupled to ground thermal mass.
        """
        props = self.foundation_thermal_properties['slab_only']
        
        # Slab edge thermal conductance (BTU/hr/°F per linear foot)
        # Based on ACCA Manual J Table 4A
        if props['edge_insulation_r'] > 5:
            edge_conductance = 0.54  # Well insulated
        elif props['edge_insulation_r'] > 0:
            edge_conductance = 0.68  # Some insulation  
        else:
            edge_conductance = 0.84  # No edge insulation (typical)
        
        # Perimeter heat loss factor
        perimeter_factor = edge_conductance * perimeter_ft
        
        # Interior slab thermal conductance (much lower due to ground coupling)
        interior_conductance = 0.025  # BTU/hr/°F/sqft for interior slab
        
        # Effective thermal conductance for entire slab
        base_conductance = (perimeter_factor + interior_conductance * area_sqft) / area_sqft
        
        # Apply thermal bridging degradation (universal for all slabs)
        thermal_bridging_factor = props.get('thermal_bridging_factor', 1.15)
        total_conductance = base_conductance * thermal_bridging_factor
        effective_r_value = 1.0 / total_conductance
        
        return FoundationThermalResult(
            foundation_type='slab_only',
            effective_r_value=effective_r_value,
            thermal_conductance=total_conductance,
            perimeter_factor=perimeter_factor / perimeter_ft,  # Per linear foot
            below_grade_factor=1.0,  # No below-grade component
            notes=f"Slab edge conductance: {edge_conductance:.2f} BTU/hr/°F/ft, Interior: {interior_conductance:.3f} BTU/hr/°F/sqft"
        )
    
    def _calculate_crawlspace_thermal_factors(
        self,
        climate_zone: str,
        winter_design_temp: float,
        ground_temp: float,
        area_sqft: float,
        perimeter_ft: float
    ) -> FoundationThermalResult:
        """
        ACCA Manual J crawl space thermal calculation.
        
        Heat loss occurs through:
        1. Floor assembly (conditioned space to crawl space)
        2. Crawl space walls (crawl space to outdoors)
        3. Air infiltration through vents (significant impact)
        
        Key: Ventilated crawl spaces have higher heat loss than basements
        due to air infiltration and limited earth coupling benefits.
        """
        props = self.foundation_thermal_properties['crawlspace']
        
        # Floor thermal resistance (conditioned space to crawl space)
        floor_r_total = props['floor_r_value'] + 0.92 + 0.68  # Insulation + air films
        floor_conductance = 1.0 / floor_r_total
        
        # Crawl space temperature - physics-based calculation for all climates
        # Ventilated crawlspaces are influenced by both outdoor air and ground coupling
        # Ground temperature is more stable, but ventilation reduces this benefit
        ground_coupling_benefit = (ground_temp - winter_design_temp) * 0.3  # 30% of ground benefit due to ventilation
        crawlspace_temp = winter_design_temp + ground_coupling_benefit + 3  # Base 3°F from structural mass
        
        # Temperature difference factor
        temp_diff_factor = (70 - crawlspace_temp) / (70 - winter_design_temp)
        
        # Base floor conductance
        base_conductance = floor_conductance * temp_diff_factor
        
        # Add ventilation penalty - ventilated crawlspaces lose more heat
        # due to air infiltration through vents connecting to outdoor air
        ventilation_penalty = props['ventilation_rate'] * 0.018 * temp_diff_factor  # CFM * specific heat
        
        # Crawl space wall losses (typically uninsulated perimeter walls)
        wall_conductance = 1.0 / (props['wall_r_value'] + 1.6)  # Wall R + air films
        wall_loss_per_sqft = (perimeter_ft * props['height'] * wall_conductance) / area_sqft
        
        # Apply thermal bridging degradation (universal physics principle)
        thermal_bridging_factor = props.get('thermal_bridging_factor', 1.25)
        
        # Total effective conductance includes floor, ventilation, and wall losses
        base_effective_conductance = base_conductance + ventilation_penalty + (wall_loss_per_sqft * 0.5)  # Increased wall impact
        
        # Apply thermal bridging degradation - affects all foundation types
        effective_conductance = base_effective_conductance * thermal_bridging_factor
        effective_r_value = 1.0 / effective_conductance
        
        # Perimeter factor (crawl space walls to outdoor)
        perimeter_factor = wall_conductance * props['height']  # BTU/hr/°F per linear foot
        
        return FoundationThermalResult(
            foundation_type='crawlspace',
            effective_r_value=effective_r_value,
            thermal_conductance=effective_conductance,
            perimeter_factor=perimeter_factor / props['height'],  # Per sqft of wall
            below_grade_factor=0.3,  # Limited below-grade benefit due to ventilation
            notes=f"Floor R-{floor_r_total:.1f}, Crawlspace temp: {crawlspace_temp:.0f}°F, Ventilation: {props['ventilation_rate']} CFM/sqft"
        )
    
    def _calculate_basement_thermal_factors(
        self,
        climate_zone: str,
        winter_design_temp: float,
        ground_temp: float,
        area_sqft: float,
        perimeter_ft: float
    ) -> FoundationThermalResult:
        """
        ACCA Manual J basement thermal calculation.
        
        Heat loss occurs through:
        1. Above-grade walls (to outdoor air)
        2. Below-grade walls (to ground - much lower loss due to soil thermal mass)
        3. Basement floor (to deep ground - minimal loss, ~55°F year-round)
        
        Key principle: Below-grade foundations have significant thermal benefits
        due to earth coupling and reduced temperature differentials.
        """
        props = self.foundation_thermal_properties['basement_with_slab']
        
        # Above-grade wall thermal conductance (exposed to outdoor air)
        above_grade_r = props['wall_r_value'] + 1.6  # Wall R + air films
        above_grade_conductance = 1.0 / above_grade_r
        
        # Below-grade wall thermal conductance (earth-coupled)
        # Per ACCA Manual J and building science: ground temperature is much more
        # stable and warmer than outdoor air in winter
        # Use ground temperature differential instead of outdoor air differential
        temp_reduction_factor = (70 - ground_temp) / (70 - winter_design_temp)
        below_grade_conductance = above_grade_conductance * temp_reduction_factor * 0.6  # Additional reduction for soil contact
        
        # Floor thermal conductance (deep ground coupling - very low)
        # Deep ground is approximately 55°F year-round at 8+ feet depth
        deep_ground_temp = 55  # °F typical deep ground temperature
        floor_temp_factor = (70 - deep_ground_temp) / (70 - winter_design_temp)
        floor_conductance = 0.02 * floor_temp_factor  # Very low due to stable ground temp
        
        # Calculate heat loss components
        above_grade_area = perimeter_ft * props['above_grade_height']
        below_grade_area = perimeter_ft * (props['depth'] - props['above_grade_height'])
        
        # Above-grade loss (full outdoor temperature differential)
        above_grade_loss = above_grade_area * above_grade_conductance
        
        # Below-grade loss (reduced temperature differential + soil benefits)
        below_grade_loss = below_grade_area * below_grade_conductance
        
        # Floor loss (minimal due to deep ground coupling)
        floor_loss = area_sqft * floor_conductance
        
        total_loss = above_grade_loss + below_grade_loss + floor_loss
        
        # Effective thermal conductance per sqft of conditioned space
        effective_conductance = total_loss / area_sqft
        effective_r_value = 1.0 / effective_conductance
        
        return FoundationThermalResult(
            foundation_type='basement_with_slab',
            effective_r_value=effective_r_value,
            thermal_conductance=effective_conductance,
            perimeter_factor=below_grade_loss / (perimeter_ft * area_sqft),  # Below-grade wall loss per sqft
            below_grade_factor=temp_reduction_factor,  # Actual temperature benefit
            notes=f"Wall R-{props['wall_r_value']}, {props['depth']}ft deep, Ground temp: {ground_temp:.0f}°F, Deep ground: {deep_ground_temp}°F"
        )


def get_foundation_thermal_factors(
    foundation_type: str,
    climate_zone: str,
    winter_design_temp: float,
    building_area_sqft: float,
    building_perimeter_ft: float = None
) -> Dict[str, Any]:
    """
    Convenience function to get foundation thermal factors.
    
    Returns:
        Dictionary with thermal factors for Manual J calculations
    """
    calculator = FoundationThermalCalculator()
    result = calculator.calculate_foundation_thermal_factors(
        foundation_type, climate_zone, winter_design_temp,
        building_area_sqft, building_perimeter_ft
    )
    
    return {
        'foundation_type': result.foundation_type,
        'foundation_r_value': result.effective_r_value,
        'foundation_conductance': result.thermal_conductance,
        'foundation_perimeter_factor': result.perimeter_factor,
        'foundation_below_grade_factor': result.below_grade_factor,
        'foundation_notes': result.notes
    }