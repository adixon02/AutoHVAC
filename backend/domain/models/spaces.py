"""
Space and Surface Models for Zone-Based Thermal Modeling
Represents individual rooms and their surfaces (walls, floors, ceilings)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class SpaceType(Enum):
    """Types of spaces with different thermal characteristics"""
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    KITCHEN = "kitchen"
    LIVING = "living"
    DINING = "dining"
    HALLWAY = "hallway"
    STORAGE = "storage"
    GARAGE = "garage"
    MECHANICAL = "mechanical"
    UNCONDITIONED = "unconditioned"
    UNKNOWN = "unknown"


class CeilingType(Enum):
    """Ceiling configurations that affect load calculations"""
    FLAT = "flat"
    VAULTED = "vaulted"
    CATHEDRAL = "cathedral"
    OPEN_TO_BELOW = "open_to_below"
    EXPOSED_BEAM = "exposed_beam"


class BoundaryCondition(Enum):
    """Thermal boundary conditions for surfaces"""
    EXTERIOR = "exterior"  # Outside
    GROUND = "ground"  # Soil contact
    GARAGE = "garage"  # Adjacent to garage
    CRAWLSPACE = "crawlspace"  # Adjacent to crawl
    ATTIC = "attic"  # Adjacent to attic
    CONDITIONED = "conditioned"  # Adjacent to conditioned space
    UNCONDITIONED = "unconditioned"  # Adjacent to unconditioned space
    ADIABATIC = "adiabatic"  # No heat transfer (internal wall)


@dataclass
class Surface:
    """A single surface (wall, floor, ceiling) of a space"""
    surface_id: str
    surface_type: str  # "wall", "floor", "ceiling", "roof"
    area_sqft: float
    orientation: Optional[str] = None  # "N", "S", "E", "W" for walls
    tilt_degrees: float = 90  # 90 for walls, 0 for flat roof/floor
    
    # Thermal properties
    assembly_name: str = ""  # e.g., "2x6_R19_wall"
    u_value: float = 0.05  # BTU/hr·ft²·°F
    
    # Boundary condition
    boundary_condition: BoundaryCondition = BoundaryCondition.EXTERIOR
    adjacent_space: Optional[str] = None  # ID of adjacent space if applicable
    adjacent_temp: Optional[float] = None  # Temperature of adjacent space/condition
    
    # Fenestration (windows/doors on this surface)
    windows: List[Dict[str, Any]] = field(default_factory=list)
    doors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def net_wall_area(self) -> float:
        """Wall area minus windows and doors"""
        if self.surface_type != "wall":
            return self.area_sqft
        
        window_area = sum(w.get('area_sqft', 0) for w in self.windows)
        door_area = sum(d.get('area_sqft', 0) for d in self.doors)
        return max(0, self.area_sqft - window_area - door_area)
    
    @property
    def window_area(self) -> float:
        """Total window area on this surface"""
        return sum(w.get('area_sqft', 0) for w in self.windows)


@dataclass
class Space:
    """
    Represents a single room or space in the building.
    This is the fundamental unit for zone-based calculations.
    """
    space_id: str
    name: str  # e.g., "Master Bedroom", "Garage"
    space_type: SpaceType
    
    # Geometry
    floor_level: int  # 1 for main floor, 2 for second floor, etc.
    area_sqft: float
    ceiling_height_ft: float = 9.0
    ceiling_type: CeilingType = CeilingType.FLAT
    
    # Location context
    floor_over: BoundaryCondition = BoundaryCondition.GROUND  # What's below
    ceiling_under: BoundaryCondition = BoundaryCondition.ATTIC  # What's above
    is_conditioned: bool = True
    
    # Special flags for bonus rooms
    is_over_garage: bool = False
    is_over_unconditioned: bool = False
    has_cathedral_ceiling: bool = False
    open_to_below: bool = False
    
    # Surfaces
    surfaces: List[Surface] = field(default_factory=list)
    
    # Occupancy and gains
    design_occupants: int = 0
    equipment_w_per_sqft: float = 1.0
    lighting_w_per_sqft: float = 1.0
    
    # Confidence tracking
    detection_confidence: float = 0.5
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def volume_cuft(self) -> float:
        """Calculate space volume accounting for ceiling type"""
        if self.ceiling_type == CeilingType.VAULTED:
            # Vaulted ceiling adds ~50% to volume
            return self.area_sqft * self.ceiling_height_ft * 1.5
        elif self.ceiling_type == CeilingType.CATHEDRAL:
            # Cathedral ceiling can double the volume
            return self.area_sqft * self.ceiling_height_ft * 2.0
        else:
            return self.area_sqft * self.ceiling_height_ft
    
    @property
    def exterior_wall_area(self) -> float:
        """Total exterior wall area"""
        return sum(
            s.area_sqft for s in self.surfaces 
            if s.surface_type == "wall" and 
            s.boundary_condition == BoundaryCondition.EXTERIOR
        )
    
    @property
    def is_bonus_room(self) -> bool:
        """Check if this is a bonus room configuration"""
        return (self.floor_level > 1 and 
                (self.is_over_garage or self.is_over_unconditioned))
    
    def get_heating_load_multiplier(self) -> float:
        """
        Get load multiplier for special conditions.
        Bonus rooms over garages need extra heating capacity.
        """
        if self.is_bonus_room and self.is_over_garage:
            return 1.3  # 30% extra for bonus over garage
        elif self.has_cathedral_ceiling:
            return 1.2  # 20% extra for cathedral ceiling
        elif self.is_over_unconditioned:
            return 1.15  # 15% extra for over unconditioned
        return 1.0
    
    def get_cooling_load_multiplier(self) -> float:
        """
        Get cooling load multiplier.
        Bonus rooms may need less cooling if not primary occupied.
        """
        if self.is_bonus_room and self.space_type in [SpaceType.BEDROOM, SpaceType.STORAGE]:
            return 0.7  # Only 70% cooling for bonus bedrooms
        elif self.space_type == SpaceType.STORAGE:
            return 0.3  # Minimal cooling for storage
        return 1.0