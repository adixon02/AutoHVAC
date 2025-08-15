"""
Clean data models for AutoHVAC v2
No bloat, just what we need for HVAC calculations
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RoomType(Enum):
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    KITCHEN = "kitchen"
    LIVING = "living"
    DINING = "dining"
    HALLWAY = "hallway"
    CLOSET = "closet"
    GARAGE = "garage"
    UTILITY = "utility"
    STORAGE = "storage"
    OFFICE = "office"
    BONUS = "bonus"
    OTHER = "other"


@dataclass
class Room:
    """Single room with HVAC-relevant properties"""
    name: str
    room_type: RoomType
    width_ft: float
    length_ft: float
    area_sqft: float
    floor_number: int
    exterior_walls: int = 1
    windows: int = 1
    ceiling_height_ft: float = 9.0
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.room_type.value,
            "dimensions": [self.width_ft, self.length_ft],
            "area": self.area_sqft,
            "floor": self.floor_number,
            "exterior_walls": self.exterior_walls,
            "windows": self.windows,
            "ceiling_height": self.ceiling_height_ft
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any], floor_number: int = 1):
        """Create Room from extractor output"""
        return cls(
            name=data.get("name", "Unknown"),
            room_type=RoomType(data.get("type", "other")),
            width_ft=data.get("dimensions", [10, 10])[0],
            length_ft=data.get("dimensions", [10, 10])[1],
            area_sqft=data.get("area", 100),
            floor_number=floor_number,
            exterior_walls=data.get("exterior_walls", 1),
            windows=data.get("windows", 1),
            ceiling_height_ft=data.get("ceiling_height", 9.0)
        )


@dataclass
class Floor:
    """Single floor/level of a building"""
    number: int  # 0=basement, 1=first, 2=second
    name: str  # "First Floor", "Second Floor"
    rooms: List[Room] = field(default_factory=list)
    
    @property
    def total_sqft(self) -> float:
        return sum(room.area_sqft for room in self.rooms)
    
    @property
    def room_count(self) -> int:
        return len(self.rooms)
    
    def add_room(self, room: Room):
        room.floor_number = self.number
        self.rooms.append(room)
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "total_sqft": self.total_sqft,
            "room_count": self.room_count,
            "rooms": [room.to_json() for room in self.rooms]
        }


@dataclass
class Building:
    """Complete building with all floors"""
    floors: List[Floor] = field(default_factory=list)
    zip_code: str = ""
    climate_zone: Optional[str] = None
    
    @property
    def total_sqft(self) -> float:
        return sum(floor.total_sqft for floor in self.floors)
    
    @property
    def room_count(self) -> int:
        return sum(floor.room_count for floor in self.floors)
    
    @property
    def floor_count(self) -> int:
        return len(self.floors)
    
    def add_floor(self, floor: Floor):
        self.floors.append(floor)
        # Keep floors sorted by number
        self.floors.sort(key=lambda f: f.number)
    
    def get_floor(self, number: int) -> Optional[Floor]:
        for floor in self.floors:
            if floor.number == number:
                return floor
        return None
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "zip_code": self.zip_code,
            "climate_zone": self.climate_zone,
            "total_sqft": self.total_sqft,
            "room_count": self.room_count,
            "floor_count": self.floor_count,
            "floors": [floor.to_json() for floor in self.floors]
        }


@dataclass
class HVACLoads:
    """HVAC load calculation results"""
    heating_btu_hr: float
    cooling_btu_hr: float
    heating_tons: float
    cooling_tons: float
    cfm_required: float
    
    # Per-floor breakdown
    floor_loads: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "heating_btu_hr": round(self.heating_btu_hr),
            "cooling_btu_hr": round(self.cooling_btu_hr),
            "heating_tons": round(self.heating_tons, 1),
            "cooling_tons": round(self.cooling_tons, 1),
            "cfm_required": round(self.cfm_required),
            "floor_breakdown": self.floor_loads
        }


@dataclass
class ExtractionResult:
    """Result from an extractor (vision, vector, ocr, etc.)"""
    source: str  # "vision", "vector", "ocr"
    rooms: List[Dict[str, Any]]
    scale_factor: Optional[float] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def room_count(self) -> int:
        return len(self.rooms)
    
    @property
    def total_area(self) -> float:
        return sum(r.get("area", 0) for r in self.rooms)
