"""
Thermal Assembly Library
Standard wall, roof, and floor assemblies with R-values and U-factors
Based on ASHRAE and building codes by era and climate zone
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConstructionEra(Enum):
    """Building construction eras with typical insulation levels"""
    PRE_1960 = "pre_1960"          # Minimal insulation
    ERA_1960_1979 = "1960_1979"    # Some insulation
    ERA_1980_1999 = "1980_1999"    # Energy crisis improvements
    ERA_2000_2009 = "2000_2009"    # Modern codes
    ERA_2010_2019 = "2010_2019"    # Energy Star
    ERA_2020_PLUS = "2020_plus"    # Current high-performance


@dataclass
class ThermalAssembly:
    """Thermal properties of a building assembly"""
    name: str
    description: str
    r_value_nominal: float  # Center-of-cavity R-value
    r_value_effective: float  # Whole-assembly R-value (includes framing)
    u_factor: float  # BTU/hr·ft²·°F
    framing_fraction: float  # Percentage of assembly that is framing
    assembly_type: str  # 'wall', 'roof', 'floor'
    materials: List[Dict[str, Any]]  # Layer-by-layer materials


class ThermalAssemblyLibrary:
    """
    Library of standard thermal assemblies by era and climate zone.
    Provides accurate R-values and U-factors for load calculations.
    """
    
    # Standard wall assemblies by era and insulation level
    WALL_ASSEMBLIES = {
        # 2x4 walls (3.5" cavity)
        "2x4_R0": ThermalAssembly(
            name="2x4_R0",
            description="2x4 wall, no insulation (pre-1960)",
            r_value_nominal=3.5,  # Air space only
            r_value_effective=3.0,
            u_factor=0.333,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_air", "r_value": 1.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x4_R11": ThermalAssembly(
            name="2x4_R11",
            description="2x4 wall, R-11 batts (1980s)",
            r_value_nominal=11.0,
            r_value_effective=9.5,  # With framing factor
            u_factor=0.105,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R11", "r_value": 11.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x4_R13": ThermalAssembly(
            name="2x4_R13",
            description="2x4 wall, R-13 batts (1990s-2000s)",
            r_value_nominal=13.0,
            r_value_effective=11.0,
            u_factor=0.091,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R13", "r_value": 13.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x4_R15": ThermalAssembly(
            name="2x4_R15",
            description="2x4 wall, R-15 high-density batts",
            r_value_nominal=15.0,
            r_value_effective=12.5,
            u_factor=0.080,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R15", "r_value": 15.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        
        # 2x6 walls (5.5" cavity)
        "2x6_R19": ThermalAssembly(
            name="2x6_R19",
            description="2x6 wall, R-19 batts (2000s)",
            r_value_nominal=19.0,
            r_value_effective=16.0,
            u_factor=0.062,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R19", "r_value": 19.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x6_R20": ThermalAssembly(
            name="2x6_R20",
            description="2x6 wall, R-20 batts (2010s standard)",
            r_value_nominal=20.0,
            r_value_effective=17.0,
            u_factor=0.059,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R20", "r_value": 20.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x6_R21": ThermalAssembly(
            name="2x6_R21",
            description="2x6 wall, R-21 high-density batts",
            r_value_nominal=21.0,
            r_value_effective=18.0,
            u_factor=0.056,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R21", "r_value": 21.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        ),
        "2x6_R20_foam": ThermalAssembly(
            name="2x6_R20_foam",
            description="2x6 wall, R-20 + R-5 continuous foam",
            r_value_nominal=25.0,
            r_value_effective=23.0,
            u_factor=0.043,
            framing_fraction=0.23,
            assembly_type="wall",
            materials=[
                {"layer": "exterior_siding", "r_value": 0.6},
                {"layer": "foam_R5", "r_value": 5.0},
                {"layer": "sheathing", "r_value": 0.6},
                {"layer": "cavity_R20", "r_value": 20.0},
                {"layer": "gypsum", "r_value": 0.5},
                {"layer": "air_films", "r_value": 0.8}
            ]
        )
    }
    
    # Standard ceiling/roof assemblies
    CEILING_ASSEMBLIES = {
        "ceiling_R0": ThermalAssembly(
            name="ceiling_R0",
            description="Uninsulated ceiling (pre-1960)",
            r_value_nominal=2.0,
            r_value_effective=2.0,
            u_factor=0.500,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        ),
        "ceiling_R19": ThermalAssembly(
            name="ceiling_R19",
            description="Ceiling with R-19 batts (1980s)",
            r_value_nominal=19.0,
            r_value_effective=18.0,
            u_factor=0.056,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        ),
        "ceiling_R30": ThermalAssembly(
            name="ceiling_R30",
            description="Ceiling with R-30 batts (1990s)",
            r_value_nominal=30.0,
            r_value_effective=28.5,
            u_factor=0.035,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        ),
        "ceiling_R38": ThermalAssembly(
            name="ceiling_R38",
            description="Ceiling with R-38 batts (2000s)",
            r_value_nominal=38.0,
            r_value_effective=36.0,
            u_factor=0.028,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        ),
        "ceiling_R49": ThermalAssembly(
            name="ceiling_R49",
            description="Ceiling with R-49 batts (2010s+)",
            r_value_nominal=49.0,
            r_value_effective=46.5,
            u_factor=0.022,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        ),
        "ceiling_R60": ThermalAssembly(
            name="ceiling_R60",
            description="High-performance ceiling R-60",
            r_value_nominal=60.0,
            r_value_effective=57.0,
            u_factor=0.018,
            framing_fraction=0.07,
            assembly_type="ceiling",
            materials=[]
        )
    }
    
    # Standard floor assemblies
    FLOOR_ASSEMBLIES = {
        "floor_R0": ThermalAssembly(
            name="floor_R0",
            description="Uninsulated floor over crawl/garage",
            r_value_nominal=4.0,  # Wood floor only
            r_value_effective=3.5,
            u_factor=0.286,
            framing_fraction=0.12,
            assembly_type="floor",
            materials=[]
        ),
        "floor_R13": ThermalAssembly(
            name="floor_R13",
            description="Floor with R-13 batts",
            r_value_nominal=13.0,
            r_value_effective=12.0,
            u_factor=0.083,
            framing_fraction=0.12,
            assembly_type="floor",
            materials=[]
        ),
        "floor_R19": ThermalAssembly(
            name="floor_R19",
            description="Floor with R-19 batts",
            r_value_nominal=19.0,
            r_value_effective=17.5,
            u_factor=0.057,
            framing_fraction=0.12,
            assembly_type="floor",
            materials=[]
        ),
        "floor_R30": ThermalAssembly(
            name="floor_R30",
            description="Floor with R-30 batts",
            r_value_nominal=30.0,
            r_value_effective=28.0,
            u_factor=0.036,
            framing_fraction=0.12,
            assembly_type="floor",
            materials=[]
        )
    }
    
    # Climate zone requirements (IECC 2021)
    CLIMATE_ZONE_REQUIREMENTS = {
        "1": {"wall_r": 13, "ceiling_r": 30, "floor_r": 13},
        "2": {"wall_r": 13, "ceiling_r": 30, "floor_r": 13},
        "3": {"wall_r": 20, "ceiling_r": 30, "floor_r": 19},
        "4": {"wall_r": 20, "ceiling_r": 38, "floor_r": 19},
        "5": {"wall_r": 20, "ceiling_r": 38, "floor_r": 30},
        "6": {"wall_r": 20, "ceiling_r": 49, "floor_r": 30},
        "7": {"wall_r": 21, "ceiling_r": 49, "floor_r": 30},
        "8": {"wall_r": 21, "ceiling_r": 49, "floor_r": 30}
    }
    
    def get_assembly_by_era(
        self,
        assembly_type: str,
        era: ConstructionEra,
        climate_zone: str = "4"
    ) -> ThermalAssembly:
        """
        Get appropriate assembly based on construction era.
        
        Args:
            assembly_type: 'wall', 'ceiling', or 'floor'
            era: Construction era
            climate_zone: Climate zone (1-8)
            
        Returns:
            ThermalAssembly with appropriate R-value
        """
        
        if assembly_type == "wall":
            if era == ConstructionEra.PRE_1960:
                return self.WALL_ASSEMBLIES["2x4_R0"]
            elif era == ConstructionEra.ERA_1960_1979:
                return self.WALL_ASSEMBLIES["2x4_R11"]
            elif era == ConstructionEra.ERA_1980_1999:
                return self.WALL_ASSEMBLIES["2x4_R13"]
            elif era == ConstructionEra.ERA_2000_2009:
                # 2x6 walls became standard
                return self.WALL_ASSEMBLIES["2x6_R19"]
            elif era == ConstructionEra.ERA_2010_2019:
                return self.WALL_ASSEMBLIES["2x6_R20"]
            else:  # 2020+
                # High performance with foam
                if climate_zone in ["5", "6", "7", "8"]:
                    return self.WALL_ASSEMBLIES["2x6_R20_foam"]
                return self.WALL_ASSEMBLIES["2x6_R21"]
        
        elif assembly_type == "ceiling":
            if era == ConstructionEra.PRE_1960:
                return self.CEILING_ASSEMBLIES["ceiling_R0"]
            elif era == ConstructionEra.ERA_1960_1979:
                return self.CEILING_ASSEMBLIES["ceiling_R19"]
            elif era == ConstructionEra.ERA_1980_1999:
                return self.CEILING_ASSEMBLIES["ceiling_R30"]
            elif era == ConstructionEra.ERA_2000_2009:
                return self.CEILING_ASSEMBLIES["ceiling_R38"]
            elif era == ConstructionEra.ERA_2010_2019:
                return self.CEILING_ASSEMBLIES["ceiling_R49"]
            else:  # 2020+
                if climate_zone in ["6", "7", "8"]:
                    return self.CEILING_ASSEMBLIES["ceiling_R60"]
                return self.CEILING_ASSEMBLIES["ceiling_R49"]
        
        elif assembly_type == "floor":
            if era == ConstructionEra.PRE_1960:
                return self.FLOOR_ASSEMBLIES["floor_R0"]
            elif era in [ConstructionEra.ERA_1960_1979, ConstructionEra.ERA_1980_1999]:
                return self.FLOOR_ASSEMBLIES["floor_R13"]
            elif era == ConstructionEra.ERA_2000_2009:
                return self.FLOOR_ASSEMBLIES["floor_R19"]
            else:  # 2010+
                if climate_zone in ["5", "6", "7", "8"]:
                    return self.FLOOR_ASSEMBLIES["floor_R30"]
                return self.FLOOR_ASSEMBLIES["floor_R19"]
        
        # Default
        return self.WALL_ASSEMBLIES["2x6_R20"]
    
    def get_assembly_by_r_value(
        self,
        assembly_type: str,
        target_r_value: float
    ) -> ThermalAssembly:
        """
        Get assembly closest to target R-value.
        
        Args:
            assembly_type: 'wall', 'ceiling', or 'floor'
            target_r_value: Desired R-value
            
        Returns:
            Closest matching ThermalAssembly
        """
        
        if assembly_type == "wall":
            assemblies = self.WALL_ASSEMBLIES
        elif assembly_type == "ceiling":
            assemblies = self.CEILING_ASSEMBLIES
        elif assembly_type == "floor":
            assemblies = self.FLOOR_ASSEMBLIES
        else:
            return self.WALL_ASSEMBLIES["2x6_R20"]  # Default
        
        # Find closest match
        best_match = None
        best_diff = float('inf')
        
        for assembly in assemblies.values():
            diff = abs(assembly.r_value_nominal - target_r_value)
            if diff < best_diff:
                best_diff = diff
                best_match = assembly
        
        return best_match
    
    def get_code_minimum(
        self,
        assembly_type: str,
        climate_zone: str,
        year: int = 2021
    ) -> ThermalAssembly:
        """
        Get code minimum assembly for climate zone.
        
        Args:
            assembly_type: 'wall', 'ceiling', or 'floor'
            climate_zone: Climate zone (1-8 or full like '4A')
            year: Code year (affects requirements)
            
        Returns:
            Code-compliant ThermalAssembly
        """
        
        # Extract numeric zone
        zone_num = climate_zone[0] if climate_zone else "4"
        
        if zone_num not in self.CLIMATE_ZONE_REQUIREMENTS:
            zone_num = "4"  # Default
        
        requirements = self.CLIMATE_ZONE_REQUIREMENTS[zone_num]
        
        if assembly_type == "wall":
            target_r = requirements["wall_r"]
        elif assembly_type == "ceiling":
            target_r = requirements["ceiling_r"]
        elif assembly_type == "floor":
            target_r = requirements["floor_r"]
        else:
            target_r = 20
        
        return self.get_assembly_by_r_value(assembly_type, target_r)
    
    def determine_era(self, year_built: int) -> ConstructionEra:
        """
        Determine construction era from year built.
        
        Args:
            year_built: Year of construction
            
        Returns:
            ConstructionEra enum value
        """
        
        if year_built < 1960:
            return ConstructionEra.PRE_1960
        elif year_built < 1980:
            return ConstructionEra.ERA_1960_1979
        elif year_built < 2000:
            return ConstructionEra.ERA_1980_1999
        elif year_built < 2010:
            return ConstructionEra.ERA_2000_2009
        elif year_built < 2020:
            return ConstructionEra.ERA_2010_2019
        else:
            return ConstructionEra.ERA_2020_PLUS


# Singleton instance
_assembly_library = None


def get_assembly_library() -> ThermalAssemblyLibrary:
    """Get or create the global assembly library"""
    global _assembly_library
    if _assembly_library is None:
        _assembly_library = ThermalAssemblyLibrary()
    return _assembly_library