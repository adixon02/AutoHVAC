"""
Pydantic schemas for AutoHVAC blueprint data structures
"""

from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
from uuid import UUID, uuid4


class Room(BaseModel):
    """Individual room in a blueprint"""
    name: str = Field(..., description="Room name (e.g., 'Living Room', 'Master Bedroom')")
    dimensions_ft: Tuple[float, float] = Field(..., description="Room dimensions in feet (width, length)")
    floor: int = Field(..., description="Floor number (1-based)")
    windows: int = Field(0, description="Number of windows")
    orientation: str = Field("", description="Primary orientation (N, S, E, W, NE, etc.)")
    area: float = Field(..., description="Room area in square feet")

    class Config:
        schema_extra = {
            "example": {
                "name": "Living Room",
                "dimensions_ft": [20.0, 15.0],
                "floor": 1,
                "windows": 3,
                "orientation": "S",
                "area": 300.0
            }
        }


class BlueprintSchema(BaseModel):
    """Complete parsed blueprint structure"""
    project_id: UUID = Field(default_factory=uuid4, description="Unique project identifier")
    zip_code: str = Field(..., description="Project location zip code")
    sqft_total: float = Field(..., description="Total square footage")
    stories: int = Field(..., description="Number of stories/floors")
    rooms: List[Room] = Field(..., description="List of all rooms")

    class Config:
        schema_extra = {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "zip_code": "90210",
                "sqft_total": 2500.0,
                "stories": 2,
                "rooms": [
                    {
                        "name": "Living Room",
                        "dimensions_ft": [20.0, 15.0],
                        "floor": 1,
                        "windows": 3,
                        "orientation": "S",
                        "area": 300.0
                    }
                ]
            }
        }


class RawGeometry(BaseModel):
    """Raw geometry extracted from PDF"""
    page_width: float
    page_height: float
    scale_factor: Optional[float] = None
    lines: List[dict]
    rectangles: List[dict]
    polylines: List[dict]


class RawText(BaseModel):
    """Raw text extracted from PDF"""
    words: List[dict]
    room_labels: List[dict]
    dimensions: List[dict]
    notes: List[dict]