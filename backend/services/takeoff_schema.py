"""
Takeoff Schema - Pydantic models for strict GPT-5 response validation
Ensures consistent data structure from blueprint parsing through HVAC calculations
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Data source confidence tracking"""
    LABELED = "labeled"  # Directly from blueprint labels
    SCALED = "scaled"    # Calculated from scale measurements
    ASSUMED = "assumed"  # Estimated based on context


class RoomType(str, Enum):
    """Standard room types for HVAC calculations"""
    BEDROOM = "bedroom"
    MASTER_BEDROOM = "master_bedroom"
    BATHROOM = "bathroom"
    MASTER_BATHROOM = "master_bathroom"
    KITCHEN = "kitchen"
    LIVING_ROOM = "living_room"
    FAMILY_ROOM = "family_room"
    DINING_ROOM = "dining_room"
    OFFICE = "office"
    DEN = "den"
    GARAGE = "garage"
    BASEMENT = "basement"
    ATTIC = "attic"
    HALLWAY = "hallway"
    CLOSET = "closet"
    WALK_IN_CLOSET = "walk_in_closet"
    LAUNDRY = "laundry"
    UTILITY = "utility"
    FOYER = "foyer"
    ENTRY = "entry"
    PANTRY = "pantry"
    GREAT_ROOM = "great_room"
    REC_ROOM = "rec_room"
    OTHER = "other"


class WallType(str, Enum):
    """Wall types for heat transfer calculations"""
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    SHARED = "shared"  # Shared with unconditioned space


class WindowFeature(BaseModel):
    """Window specifications for heat gain/loss"""
    width_ft: float = Field(..., gt=0, description="Window width in feet")
    height_ft: float = Field(..., gt=0, description="Window height in feet")
    orientation: Optional[str] = Field(None, description="Cardinal direction (N/S/E/W)")
    glazing_type: str = Field("double_pane", description="Window glazing type")
    source: SourceType = Field(SourceType.ASSUMED, description="Data source")
    
    @property
    def area_sqft(self) -> float:
        return self.width_ft * self.height_ft


class DoorFeature(BaseModel):
    """Door specifications"""
    width_ft: float = Field(3.0, gt=0, description="Door width in feet")
    height_ft: float = Field(7.0, gt=0, description="Door height in feet")
    type: Literal["exterior", "interior"] = Field("interior", description="Door type")
    material: str = Field("wood", description="Door material")
    source: SourceType = Field(SourceType.ASSUMED, description="Data source")


class Room(BaseModel):
    """Room data with HVAC-specific information"""
    id: str = Field(..., description="Unique room identifier")
    name: str = Field(..., description="Room name from blueprint")
    room_type: RoomType = Field(..., description="Standardized room type")
    
    # Dimensions
    width_ft: float = Field(..., gt=0, description="Room width in feet")
    length_ft: float = Field(..., gt=0, description="Room length in feet")
    ceiling_height_ft: float = Field(8.0, gt=0, description="Ceiling height in feet")
    
    # Features
    windows: List[WindowFeature] = Field(default_factory=list, description="Windows in room")
    doors: List[DoorFeature] = Field(default_factory=list, description="Doors in room")
    exterior_walls: int = Field(0, ge=0, le=4, description="Number of exterior walls")
    
    # Location
    floor_number: int = Field(1, ge=0, description="Floor number (0=basement)")
    location_description: str = Field("", description="Location within building")
    
    # HVAC loads
    heating_btu_hr: Optional[float] = Field(None, ge=0, description="Heating load BTU/hr")
    cooling_btu_hr: Optional[float] = Field(None, ge=0, description="Cooling load BTU/hr")
    
    # Metadata
    source: SourceType = Field(..., description="Primary data source")
    confidence: float = Field(0.8, ge=0, le=1, description="Detection confidence")
    
    # Actual area field to store GPT-4V detected area
    actual_area_sqft: Optional[float] = Field(None, gt=0, description="Actual room area from GPT-4V or measurement")
    
    @property
    def area_sqft(self) -> float:
        """
        Return actual area if available (from GPT-4V), otherwise calculate from dimensions
        This preserves GPT-4V detected areas for irregular rooms
        """
        if self.actual_area_sqft is not None and self.actual_area_sqft > 0:
            return self.actual_area_sqft
        return self.width_ft * self.length_ft
    
    @property
    def volume_cuft(self) -> float:
        return self.area_sqft * self.ceiling_height_ft
    
    @property
    def window_area_sqft(self) -> float:
        return sum(w.area_sqft for w in self.windows)
    
    @property
    def is_corner_room(self) -> bool:
        """Check if room is a corner room (2+ exterior walls)"""
        return self.exterior_walls >= 2
    
    def estimate_wall_areas(self) -> None:
        """Estimate wall areas if not provided"""
        if self.exterior_wall_area_sqft is None and self.exterior_walls > 0:
            # Estimate based on room dimensions and ceiling height
            perimeter = 2 * (self.width_ft + self.length_ft)
            wall_height = self.ceiling_height_ft
            
            # Distribute perimeter based on number of exterior walls
            if self.exterior_walls == 1:
                self.exterior_wall_area_sqft = max(self.width_ft, self.length_ft) * wall_height
            elif self.exterior_walls == 2:
                self.exterior_wall_area_sqft = (self.width_ft + self.length_ft) * wall_height
            elif self.exterior_walls >= 3:
                self.exterior_wall_area_sqft = perimeter * wall_height * 0.75
            else:
                self.exterior_wall_area_sqft = 0
            
            # Interior walls are the remainder
            total_wall_area = perimeter * wall_height
            self.interior_wall_area_sqft = total_wall_area - (self.exterior_wall_area_sqft or 0)
    
    @validator('room_type', pre=True)
    def normalize_room_type(cls, v):
        """Convert string to RoomType enum"""
        if isinstance(v, str):
            # Map common variations
            type_mapping = {
                'master': RoomType.MASTER_BEDROOM,
                'mbr': RoomType.MASTER_BEDROOM,
                'br': RoomType.BEDROOM,
                'bath': RoomType.BATHROOM,
                'mbath': RoomType.MASTER_BATHROOM,
                'kit': RoomType.KITCHEN,
                'liv': RoomType.LIVING_ROOM,
                'fam': RoomType.FAMILY_ROOM,
                'din': RoomType.DINING_ROOM,
                'gar': RoomType.GARAGE,
            }
            v_lower = v.lower()
            for key, room_type in type_mapping.items():
                if key in v_lower:
                    return room_type
            # Try direct enum lookup
            try:
                return RoomType(v_lower.replace(' ', '_'))
            except ValueError:
                return RoomType.OTHER
        return v


class BuildingEnvelope(BaseModel):
    """Building envelope characteristics"""
    total_area_sqft: float = Field(..., gt=0, description="Total conditioned area")
    num_floors: int = Field(1, ge=1, description="Number of floors")
    foundation_type: Literal["slab", "crawl", "basement"] = Field("slab", description="Foundation type")
    
    # Insulation values (R-values)
    wall_r_value: float = Field(13.0, gt=0, description="Wall insulation R-value")
    ceiling_r_value: float = Field(30.0, gt=0, description="Ceiling insulation R-value")
    floor_r_value: float = Field(19.0, gt=0, description="Floor insulation R-value")
    
    # Building orientation
    orientation_degrees: Optional[float] = Field(None, ge=0, lt=360, description="Building orientation from North")
    
    # Air infiltration
    air_changes_per_hour: float = Field(0.5, gt=0, description="Air changes per hour (ACH)")
    
    source: SourceType = Field(SourceType.ASSUMED, description="Primary data source")


class ClimateData(BaseModel):
    """Climate zone and design temperatures"""
    zip_code: str = Field(..., description="Project location ZIP code")
    climate_zone: str = Field(..., description="ASHRAE climate zone")
    
    # Design temperatures
    winter_design_temp_f: float = Field(..., description="Winter design temperature (°F)")
    summer_design_temp_f: float = Field(..., description="Summer design temperature (°F)")
    summer_design_humidity: float = Field(50.0, ge=0, le=100, description="Summer design humidity (%)")
    
    # Location data
    latitude: Optional[float] = Field(None, description="Latitude for solar calculations")
    longitude: Optional[float] = Field(None, description="Longitude for solar calculations")
    elevation_ft: Optional[float] = Field(None, description="Elevation in feet")
    
    source: SourceType = Field(SourceType.LABELED, description="Data source (zip from user)")


class HVACLoad(BaseModel):
    """HVAC load calculation results"""
    # Room-by-room loads
    room_loads: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Room ID to heating/cooling BTU/hr mapping"
    )
    
    # Total loads
    total_heating_btu_hr: float = Field(..., ge=0, description="Total heating load BTU/hr")
    total_cooling_btu_hr: float = Field(..., ge=0, description="Total cooling load BTU/hr")
    
    # Equipment sizing
    heating_system_tons: float = Field(..., ge=0, description="Recommended heating capacity (tons)")
    cooling_system_tons: float = Field(..., ge=0, description="Recommended cooling capacity (tons)")
    
    # Load breakdown
    heating_components: Dict[str, float] = Field(
        default_factory=dict,
        description="Heating load components (walls, windows, infiltration, etc.)"
    )
    cooling_components: Dict[str, float] = Field(
        default_factory=dict,
        description="Cooling load components (walls, windows, solar, internal, etc.)"
    )
    
    # Calculation metadata
    calculation_method: str = Field("ACCA Manual J", description="Calculation methodology")
    safety_factor: float = Field(1.1, ge=1.0, le=1.3, description="Applied safety factor")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Calculation timestamp")


class BlueprintTakeoff(BaseModel):
    """Complete blueprint takeoff with all parsed data"""
    # Project identification
    project_id: str = Field(..., description="Unique project identifier")
    filename: str = Field(..., description="Original blueprint filename")
    
    # Parsed data
    rooms: List[Room] = Field(..., min_items=1, description="All detected rooms")
    building_envelope: BuildingEnvelope = Field(..., description="Building characteristics")
    climate_data: ClimateData = Field(..., description="Climate and location data")
    
    # HVAC calculations
    hvac_loads: Optional[HVACLoad] = Field(None, description="HVAC load calculations")
    
    # Metadata
    scale_notation: str = Field("1/4\"=1'-0\"", description="Blueprint scale")
    pages_analyzed: List[int] = Field(..., min_items=1, description="PDF pages analyzed")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence")
    processing_time_seconds: float = Field(..., ge=0, description="Processing time")
    model_used: str = Field(..., description="AI model used for parsing")
    
    @property
    def total_area_sqft(self) -> float:
        return sum(room.area_sqft for room in self.rooms)
    
    @property
    def num_rooms(self) -> int:
        return len(self.rooms)
    
    @property
    def has_hvac_loads(self) -> bool:
        return self.hvac_loads is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return self.dict(exclude_none=True)
    
    def get_room_summary(self) -> Dict[str, int]:
        """Get count of each room type"""
        summary = {}
        for room in self.rooms:
            room_type = room.room_type.value
            summary[room_type] = summary.get(room_type, 0) + 1
        return summary


class GPTResponse(BaseModel):
    """Expected GPT-5 Vision response format"""
    blueprint_takeoff: BlueprintTakeoff = Field(..., description="Parsed blueprint data")
    reasoning: Optional[str] = Field(None, description="GPT-5 reasoning process")
    warnings: List[str] = Field(default_factory=list, description="Any parsing warnings")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }