"""
Project-related data models
Exact match to TypeScript definitions in shared/types.ts
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal

class BuildingType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"

class ConstructionType(str, Enum):
    NEW = "new"
    RETROFIT = "retrofit"

class InputMethod(str, Enum):
    MANUAL = "manual"
    BLUEPRINT = "blueprint"

class ProjectInfo(BaseModel):
    id: str
    project_name: str = Field(..., min_length=3, max_length=50)
    zip_code: str = Field(..., pattern=r'^\d{5}$')
    building_type: BuildingType
    construction_type: ConstructionType
    input_method: InputMethod
    created_at: datetime
    updated_at: datetime

class FoundationType(str, Enum):
    SLAB = "slab"
    CRAWLSPACE = "crawlspace" 
    BASEMENT = "basement"
    PIER = "pier"

class InsulationQuality(str, Enum):
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    EXCELLENT = "excellent"

class WindowType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    LOW_E = "low-E"

class BuildingOrientation(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"

class BuildingAge(str, Enum):
    NEW = "new"       # <5 years
    RECENT = "recent" # 5-20 years
    OLDER = "older"   # 20-40 years
    HISTORIC = "historic"  # >40 years

class BuildingCharacteristics(BaseModel):
    total_square_footage: int = Field(..., ge=500, le=50000)
    foundation_type: FoundationType
    wall_insulation: InsulationQuality
    ceiling_insulation: InsulationQuality
    window_type: WindowType
    building_orientation: BuildingOrientation
    stories: int = Field(..., ge=1, le=4)
    building_age: BuildingAge

class RoomType(str, Enum):
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    KITCHEN = "kitchen"
    LIVING = "living"
    DINING = "dining"
    OFFICE = "office"
    OTHER = "other"

class Room(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=30)
    area: int = Field(..., ge=50, le=5000)  # sq ft
    ceiling_height: int = Field(..., ge=7, le=15)  # feet
    exterior_walls: int = Field(..., ge=0, le=4)
    window_area: int = Field(..., ge=0, le=500)  # sq ft
    occupants: int = Field(..., ge=0, le=20)
    equipment_load: int = Field(..., ge=0, le=5000)  # watts
    room_type: RoomType