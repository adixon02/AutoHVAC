"""
Pydantic schemas for AutoHVAC blueprint data structures
Enhanced with comprehensive parsing metadata and auditability
"""

from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class ParsingStatus(str, Enum):
    """Status of blueprint parsing operations"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    COMPLEXITY_ERROR = "complexity_error"


class ParsedDimension(BaseModel):
    """Structured dimension information from blueprint"""
    text: str = Field(..., description="Original dimension text")
    width_ft: float = Field(..., description="Width in feet")
    length_ft: float = Field(..., description="Length in feet") 
    position: Tuple[float, float] = Field(..., description="Position on page (x, y)")
    confidence: float = Field(..., description="Parsing confidence 0-1")
    dimension_type: str = Field("room", description="Type: room, wall, opening, etc.")


class ParsedLabel(BaseModel):
    """Structured text label from blueprint"""
    text: str = Field(..., description="Label text")
    position: Tuple[float, float] = Field(..., description="Position on page (x, y)")
    label_type: str = Field("room", description="Type: room, note, dimension, etc.")
    confidence: float = Field(..., description="Recognition confidence 0-1")
    font_size: float = Field(12.0, description="Font size in points")


class GeometricElement(BaseModel):
    """Individual geometric element (line, rectangle, etc.)"""
    element_type: str = Field(..., description="Type: line, rectangle, polyline, etc.")
    coordinates: List[float] = Field(..., description="Element coordinates")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    confidence: float = Field(..., description="Element confidence 0-1")
    classification: str = Field("unknown", description="wall, room_boundary, dimension_line, etc.")


class PageAnalysisResult(BaseModel):
    """Analysis results for a specific PDF page"""
    page_number: int = Field(..., description="1-based page number")
    selected: bool = Field(False, description="Whether this page was selected for processing")
    score: float = Field(..., description="Floor plan likelihood score")
    rectangle_count: int = Field(..., description="Number of rectangles found")
    room_label_count: int = Field(..., description="Number of room labels found")
    dimension_count: int = Field(..., description="Number of dimensions found")
    geometric_complexity: int = Field(..., description="Total geometric elements")
    text_element_count: int = Field(..., description="Total text elements")
    processing_time_seconds: float = Field(..., description="Time to analyze page")
    too_complex: bool = Field(False, description="Page exceeded complexity limits")
    errors: List[str] = Field(default_factory=list, description="Processing errors")


class ParsingMetadata(BaseModel):
    """Comprehensive metadata about the parsing process"""
    parsing_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When parsing occurred")
    processing_time_seconds: float = Field(..., description="Total processing time")
    pdf_filename: str = Field(..., description="Original PDF filename")
    pdf_page_count: int = Field(..., description="Total pages in PDF")
    selected_page: int = Field(..., description="Page selected for processing (1-based)")
    
    # Parsing results by stage
    geometry_status: ParsingStatus = Field(..., description="Geometry extraction status")
    text_status: ParsingStatus = Field(..., description="Text extraction status")
    ai_status: ParsingStatus = Field(..., description="AI analysis status")
    
    # Detailed analysis results
    page_analyses: List[PageAnalysisResult] = Field(default_factory=list, description="Per-page analysis results")
    
    # Error tracking
    errors_encountered: List[Dict[str, Any]] = Field(default_factory=list, description="All errors during processing")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    
    # Confidence metrics
    overall_confidence: float = Field(..., description="Overall parsing confidence 0-1")
    geometry_confidence: float = Field(..., description="Geometry parsing confidence 0-1")
    text_confidence: float = Field(..., description="Text parsing confidence 0-1")
    
    # Data quality validation
    validation_warnings: Optional[List[Dict[str, Any]]] = Field(default=None, description="Validation warnings")
    data_quality_score: Optional[float] = Field(default=None, description="Overall data quality score 0-100")


class Room(BaseModel):
    """Individual room in a blueprint with enhanced metadata"""
    name: str = Field(..., description="Room name (e.g., 'Living Room', 'Master Bedroom')")
    dimensions_ft: Tuple[float, float] = Field(..., description="Room dimensions in feet (width, length)")
    floor: int = Field(..., description="Floor number (1-based)")
    windows: int = Field(0, description="Number of windows")
    orientation: str = Field("", description="Primary orientation (N, S, E, W, NE, etc.)")
    area: float = Field(..., description="Room area in square feet")
    
    # Enhanced room metadata
    room_type: str = Field("unknown", description="Classified room type (bedroom, bathroom, etc.)")
    confidence: float = Field(0.5, description="Room identification confidence 0-1")
    source_elements: Dict[str, Any] = Field(default_factory=dict, description="Geometric/text elements used to identify room")
    center_position: Optional[Tuple[float, float]] = Field(None, description="Room center in page coordinates")
    
    # Parsing details
    label_found: bool = Field(False, description="Whether a text label was found for this room")
    dimensions_source: str = Field("inferred", description="How dimensions were determined: measured, inferred, estimated")
    
    @validator('center_position', pre=True, always=True)
    def set_default_center_position(cls, v):
        """Set default center position if not provided"""
        if v is None:
            return (0.0, 0.0)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Living Room",
                "dimensions_ft": [20.0, 15.0],
                "floor": 1,
                "windows": 3,
                "orientation": "S",
                "area": 300.0,
                "room_type": "living",
                "confidence": 0.85,
                "center_position": [200.0, 150.0],
                "label_found": True,
                "dimensions_source": "measured"
            }
        }


class BlueprintSchema(BaseModel):
    """Complete parsed blueprint structure with comprehensive metadata"""
    project_id: Union[UUID, str] = Field(default_factory=uuid4, description="Unique project identifier")
    zip_code: str = Field(..., description="Project location zip code")
    sqft_total: float = Field(..., description="Total square footage")
    stories: int = Field(..., description="Number of stories/floors")
    rooms: List[Room] = Field(..., description="List of all rooms")
    
    # Raw data preservation
    raw_geometry: Optional[Dict[str, Any]] = Field(None, description="Raw geometry data for reference")
    raw_text: Optional[Dict[str, Any]] = Field(None, description="Raw text data for reference")
    
    # Structured parsed elements
    dimensions: List[ParsedDimension] = Field(default_factory=list, description="All dimensions found in blueprint")
    labels: List[ParsedLabel] = Field(default_factory=list, description="All text labels found")
    geometric_elements: List[GeometricElement] = Field(default_factory=list, description="All geometric elements")
    
    # Comprehensive metadata
    parsing_metadata: ParsingMetadata = Field(..., description="Complete parsing metadata and audit trail")
    
    @validator('project_id', pre=True)
    def validate_project_id(cls, v):
        """Convert string UUID to UUID object if needed"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID string: {v}")
        return v

    def dict(self, **kwargs):
        """Override dict method to ensure UUID serialization"""
        data = super().dict(**kwargs)
        # Ensure project_id is always a string
        if 'project_id' in data and not isinstance(data['project_id'], str):
            data['project_id'] = str(data['project_id'])
        return data
    
    class Config:
        json_encoders = {
            UUID: str,  # Automatically convert UUIDs to strings for JSON serialization
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
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
                        "area": 300.0,
                        "room_type": "living",
                        "confidence": 0.85,
                        "center_position": [200.0, 150.0],
                        "label_found": True,
                        "dimensions_source": "measured"
                    }
                ],
                "parsing_metadata": {
                    "processing_time_seconds": 45.2,
                    "pdf_filename": "house_plan.pdf",
                    "selected_page": 1,
                    "geometry_status": "success",
                    "text_status": "partial",
                    "ai_status": "success",
                    "overall_confidence": 0.78
                }
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