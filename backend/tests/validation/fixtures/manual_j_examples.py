"""
Manual J Reference Examples
Known calculation examples from ACCA Manual J 8th Edition for validation
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum


class ClimateZone(Enum):
    ZONE_3A = "3A"  # Warm-Humid
    ZONE_4A = "4A"  # Mixed-Humid  
    ZONE_5A = "5A"  # Cool-Humid
    ZONE_5B = "5B"  # Cool-Dry (Spokane, WA)
    ZONE_6A = "6A"  # Cold-Humid
    ZONE_7 = "7"    # Very Cold


@dataclass
class DesignConditions:
    """ASHRAE 99% design conditions"""
    heating_db_f: float  # Winter 99% dry-bulb
    cooling_db_f: float  # Summer 1% dry-bulb
    cooling_wb_f: float  # Summer 1% wet-bulb
    daily_range: float   # Daily temperature range
    latitude: float
    elevation_ft: float
    

@dataclass
class EnvelopeComponent:
    """Building envelope component specification"""
    area_sqft: float
    u_value: float  # Overall U-value (BTU/hr·sqft·°F)
    orientation: str  # N, S, E, W, NE, etc.
    

@dataclass
class WindowComponent(EnvelopeComponent):
    """Window component with solar properties"""
    shgc: float  # Solar Heat Gain Coefficient
    window_to_wall_ratio: float  # Percentage of wall area


@dataclass
class BuildingSpec:
    """Complete building specification for Manual J calculations"""
    name: str
    total_sqft: float
    volume_cuft: float
    floors: int
    foundation_type: str  # 'slab', 'basement', 'crawlspace'
    
    # Envelope components
    walls: List[EnvelopeComponent]
    windows: List[WindowComponent] 
    doors: List[EnvelopeComponent]
    roof: EnvelopeComponent
    foundation: EnvelopeComponent
    
    # Air infiltration
    ach50: float  # Blower door test result
    natural_ach: float  # Estimated natural air changes
    
    # Internal loads
    occupants: int
    lighting_watts_sqft: float
    equipment_watts_sqft: float
    

@dataclass
class ExpectedLoads:
    """Expected Manual J calculation results"""
    heating_btuh: float
    cooling_sensible_btuh: float
    cooling_latent_btuh: float
    cooling_total_btuh: float
    
    # Component breakdowns
    envelope_heating: float
    infiltration_heating: float
    solar_gains: float
    internal_gains_sensible: float
    internal_gains_latent: float


# ACCA Manual J Example 1: Simple Ranch Home
SIMPLE_RANCH = BuildingSpec(
    name="Manual J Example 1 - Simple Ranch",
    total_sqft=1600,
    volume_cuft=12800,  # 8ft ceilings
    floors=1,
    foundation_type='slab',
    
    walls=[
        EnvelopeComponent(area_sqft=1120, u_value=0.064, orientation="mixed")
    ],
    windows=[
        WindowComponent(area_sqft=180, u_value=0.35, shgc=0.30, 
                       window_to_wall_ratio=0.16, orientation="mixed")
    ],
    doors=[
        EnvelopeComponent(area_sqft=40, u_value=0.20, orientation="N")
    ],
    roof=EnvelopeComponent(area_sqft=1600, u_value=0.030, orientation="horizontal"),
    foundation=EnvelopeComponent(area_sqft=1600, u_value=0.35, orientation="horizontal"),
    
    ach50=5.0,
    natural_ach=0.35,
    
    occupants=4,
    lighting_watts_sqft=1.0,
    equipment_watts_sqft=1.0,
)

SIMPLE_RANCH_EXPECTED = ExpectedLoads(
    heating_btuh=45000,
    cooling_sensible_btuh=18000,
    cooling_latent_btuh=6000,
    cooling_total_btuh=24000,
    
    envelope_heating=32000,
    infiltration_heating=13000,
    solar_gains=8500,
    internal_gains_sensible=5500,
    internal_gains_latent=6000,
)


# ACCA Manual J Example 2: Two-Story Colonial  
TWO_STORY_COLONIAL = BuildingSpec(
    name="Manual J Example 2 - Two-Story Colonial",
    total_sqft=2400,
    volume_cuft=19200,  # Mixed ceiling heights
    floors=2,
    foundation_type='basement',
    
    walls=[
        EnvelopeComponent(area_sqft=1680, u_value=0.058, orientation="mixed")
    ],
    windows=[
        WindowComponent(area_sqft=300, u_value=0.32, shgc=0.28,
                       window_to_wall_ratio=0.18, orientation="mixed")
    ],
    doors=[
        EnvelopeComponent(area_sqft=40, u_value=0.18, orientation="N")
    ],
    roof=EnvelopeComponent(area_sqft=1200, u_value=0.027, orientation="horizontal"),
    foundation=EnvelopeComponent(area_sqft=1200, u_value=0.12, orientation="horizontal"),
    
    ach50=4.0,
    natural_ach=0.30,
    
    occupants=5,
    lighting_watts_sqft=1.2,
    equipment_watts_sqft=1.2,
)

TWO_STORY_COLONIAL_EXPECTED = ExpectedLoads(
    heating_btuh=68000,
    cooling_sensible_btuh=28000,
    cooling_latent_btuh=9500,
    cooling_total_btuh=37500,
    
    envelope_heating=48000,
    infiltration_heating=20000,
    solar_gains=12500,
    internal_gains_sensible=8500,
    internal_gains_latent=9500,
)


# Our Test Cases (mapped to Manual J methodology)
EXAMPLE_1_SPOKANE = BuildingSpec(
    name="AutoHVAC Example 1 - Spokane Ranch",
    total_sqft=1853,
    volume_cuft=14824,  # 8ft ceilings
    floors=1,
    foundation_type='crawlspace',
    
    walls=[
        EnvelopeComponent(area_sqft=1200, u_value=0.075, orientation="mixed")  # R-13.3 effective
    ],
    windows=[
        WindowComponent(area_sqft=264, u_value=0.30, shgc=0.30,
                       window_to_wall_ratio=0.22, orientation="mixed")
    ],
    doors=[
        EnvelopeComponent(area_sqft=40, u_value=0.20, orientation="N")
    ],
    roof=EnvelopeComponent(area_sqft=1853, u_value=0.023, orientation="horizontal"),  # R-43
    foundation=EnvelopeComponent(area_sqft=1853, u_value=0.026, orientation="horizontal"),  # R-38 floor
    
    ach50=3.0,
    natural_ach=0.46,  # ACH50/6.5 per our fix
    
    occupants=4,
    lighting_watts_sqft=1.0,
    equipment_watts_sqft=1.0,
)

EXAMPLE_1_EXPECTED = ExpectedLoads(
    heating_btuh=61393,
    cooling_sensible_btuh=18314,
    cooling_latent_btuh=5000,
    cooling_total_btuh=23314,
    
    envelope_heating=35000,  # Estimated breakdown
    infiltration_heating=26393,
    solar_gains=8000,
    internal_gains_sensible=6000,
    internal_gains_latent=5000,
)


EXAMPLE_2_SPOKANE = BuildingSpec(
    name="AutoHVAC Example 2 - Spokane Two-Story + Bonus",
    total_sqft=2599,
    volume_cuft=23391,  # 9ft ceilings
    floors=2,
    foundation_type='crawlspace',
    
    walls=[
        EnvelopeComponent(area_sqft=2012, u_value=0.075, orientation="mixed")  # R-13.3 effective
    ],
    windows=[
        WindowComponent(area_sqft=443, u_value=0.30, shgc=0.30,
                       window_to_wall_ratio=0.22, orientation="mixed")
    ],
    doors=[
        EnvelopeComponent(area_sqft=40, u_value=0.20, orientation="N")
    ],
    roof=EnvelopeComponent(area_sqft=676, u_value=0.023, orientation="horizontal"),  # Bonus only
    foundation=EnvelopeComponent(area_sqft=1923, u_value=0.026, orientation="horizontal"),  # Main floor
    
    ach50=3.0,
    natural_ach=0.46,
    
    occupants=5,
    lighting_watts_sqft=1.0,
    equipment_watts_sqft=1.0,
)

EXAMPLE_2_EXPECTED = ExpectedLoads(
    heating_btuh=74980,
    cooling_sensible_btuh=20020,
    cooling_latent_btuh=5500,
    cooling_total_btuh=25520,
    
    envelope_heating=42000,  # Estimated breakdown
    infiltration_heating=32980,
    solar_gains=9000,
    internal_gains_sensible=7000,
    internal_gains_latent=5500,
)


# Climate data for Zone 5B (Spokane, WA)
SPOKANE_CLIMATE = DesignConditions(
    heating_db_f=6.0,   # 99% winter design
    cooling_db_f=89.0,  # 1% summer design  
    cooling_wb_f=63.0,  # 1% summer wet-bulb
    daily_range=28.0,   # Diurnal temperature range
    latitude=47.6,
    elevation_ft=2350,
)


# Test cases organized by complexity
VALIDATION_CASES = {
    'simple_ranch_manual_j': (SIMPLE_RANCH, SIMPLE_RANCH_EXPECTED),
    'two_story_colonial_manual_j': (TWO_STORY_COLONIAL, TWO_STORY_COLONIAL_EXPECTED),
    'autohvac_example1': (EXAMPLE_1_SPOKANE, EXAMPLE_1_EXPECTED),
    'autohvac_example2': (EXAMPLE_2_SPOKANE, EXAMPLE_2_EXPECTED),
}


def get_climate_data(zone: ClimateZone) -> DesignConditions:
    """Get climate data for specific IECC zone"""
    if zone == ClimateZone.ZONE_5B:
        return SPOKANE_CLIMATE
    else:
        raise NotImplementedError(f"Climate data for {zone} not implemented")


def get_validation_case(case_name: str) -> tuple[BuildingSpec, ExpectedLoads]:
    """Get specific validation test case"""
    if case_name not in VALIDATION_CASES:
        raise ValueError(f"Unknown validation case: {case_name}")
    return VALIDATION_CASES[case_name]


def list_validation_cases() -> List[str]:
    """List all available validation cases"""
    return list(VALIDATION_CASES.keys())