"""
Pipeline Contracts - Strict Pydantic models for inter-stage data transfer
Ensures type safety and validation between pipeline stages
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class StageStatus(str, Enum):
    """Status of a pipeline stage"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PageClassificationOutput(BaseModel):
    """Output from Stage 1: Page Classification"""
    selected_page: int = Field(..., ge=0, description="0-indexed page number")
    total_pages: int = Field(..., ge=1)
    page_scores: Dict[int, float] = Field(..., description="Confidence scores for each page")
    selection_reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator('selected_page')
    def validate_page_in_range(cls, v, values):
        if 'total_pages' in values and v >= values['total_pages']:
            raise ValueError(f"Selected page {v} out of range (total: {values['total_pages']})")
        return v


class ScaleDetectionOutput(BaseModel):
    """Output from Stage 2: Scale Detection"""
    pixels_per_foot: float = Field(..., gt=0)
    scale_notation: str = Field(..., description="e.g., '1/4\"=1'-0\"'")
    detection_method: str = Field(..., description="How scale was detected")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_location: Optional[str] = Field(None, description="Where on page scale was found")
    
    @validator('pixels_per_foot')
    def validate_reasonable_scale(cls, v):
        # Reasonable range: 1/8"=1' (96 px/ft) to 1"=1' (12 px/ft)
        if v < 10 or v > 200:
            raise ValueError(f"Scale {v} px/ft outside reasonable range (10-200)")
        return v


class RoomGeometry(BaseModel):
    """Geometry for a single room"""
    id: str
    polygon: List[Tuple[float, float]] = Field(..., min_items=3)
    area_sqft: float = Field(..., gt=0)
    perimeter_ft: float = Field(..., gt=0)
    center: Tuple[float, float]
    bounding_box: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    
    @validator('area_sqft')
    def validate_reasonable_area(cls, v):
        # Rooms should be between 10 and 5000 sqft
        if v < 10 or v > 5000:
            raise ValueError(f"Room area {v} sqft outside reasonable range (10-5000)")
        return v


class GeometryExtractionOutput(BaseModel):
    """Output from Stage 3: Geometry Extraction"""
    rooms: List[RoomGeometry]
    total_area_sqft: float = Field(..., gt=0)
    exterior_perimeter_ft: float = Field(..., gt=0)
    num_floors: int = Field(1, ge=1, le=5)
    building_footprint: List[Tuple[float, float]] = Field(..., min_items=3)
    extraction_method: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator('rooms')
    def validate_rooms_exist(cls, v):
        if len(v) == 0:
            raise ValueError("No rooms detected in geometry extraction")
        return v
    
    @validator('total_area_sqft')
    def validate_total_area(cls, v, values):
        if 'rooms' in values:
            room_total = sum(r.area_sqft for r in values['rooms'])
            # Total should be close to sum of rooms (within 20%)
            if abs(v - room_total) / room_total > 0.2:
                raise ValueError(f"Total area {v} differs significantly from room sum {room_total}")
        return v


class RoomSemantics(BaseModel):
    """Semantic information for a room"""
    room_id: str = Field(..., description="Must match a RoomGeometry.id")
    name: str
    room_type: str = Field(..., description="bedroom, bathroom, kitchen, etc.")
    windows_count: int = Field(0, ge=0)
    doors_count: int = Field(1, ge=0)  # At least one door
    exterior_walls: int = Field(0, ge=0, le=4)
    features: List[str] = Field(default_factory=list)
    occupancy: int = Field(1, ge=0)  # Number of occupants
    
    @validator('room_type')
    def validate_room_type(cls, v):
        valid_types = [
            'bedroom', 'bathroom', 'kitchen', 'living_room', 'dining_room',
            'hallway', 'closet', 'garage', 'basement', 'attic', 'office',
            'laundry', 'utility', 'other'
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid room type: {v}")
        return v.lower()


class BuildingEnvelopeData(BaseModel):
    """Building envelope characteristics"""
    wall_r_value: float = Field(..., gt=0, le=100)
    ceiling_r_value: float = Field(..., gt=0, le=100)
    floor_r_value: float = Field(..., gt=0, le=100)
    window_u_value: float = Field(0.35, gt=0, le=2.0)
    door_u_value: float = Field(0.5, gt=0, le=2.0)
    air_changes_per_hour: float = Field(0.5, gt=0, le=5.0)
    foundation_type: str = Field("slab", regex="^(slab|crawl|basement)$")


class SemanticAnalysisOutput(BaseModel):
    """Output from Stage 4: Semantic Analysis (GPT-5 Vision)"""
    room_semantics: List[RoomSemantics]
    building_envelope: BuildingEnvelopeData
    climate_zone: str = Field(..., regex="^[1-8][A-C]?$")  # ASHRAE climate zones
    orientation_degrees: float = Field(0, ge=0, lt=360)
    special_features: List[str] = Field(default_factory=list)
    analysis_method: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator('room_semantics')
    def validate_semantics_exist(cls, v):
        if len(v) == 0:
            raise ValueError("No room semantics provided")
        return v


class RoomHVACLoad(BaseModel):
    """HVAC load for a single room"""
    room_id: str = Field(..., description="Must match a RoomGeometry.id")
    heating_btu_hr: float = Field(..., ge=0)
    cooling_btu_hr: float = Field(..., ge=0)
    heating_components: Dict[str, float] = Field(default_factory=dict)
    cooling_components: Dict[str, float] = Field(default_factory=dict)
    
    @validator('heating_btu_hr')
    def validate_heating_reasonable(cls, v):
        # Reasonable range: 0 to 50,000 BTU/hr per room
        if v > 50000:
            raise ValueError(f"Heating load {v} BTU/hr exceeds reasonable maximum")
        return v
    
    @validator('cooling_btu_hr')
    def validate_cooling_reasonable(cls, v):
        # Reasonable range: 0 to 50,000 BTU/hr per room
        if v > 50000:
            raise ValueError(f"Cooling load {v} BTU/hr exceeds reasonable maximum")
        return v


class LoadCalculationOutput(BaseModel):
    """Output from Stage 5: Load Calculation"""
    room_loads: List[RoomHVACLoad]
    total_heating_btu_hr: float = Field(..., ge=0)
    total_cooling_btu_hr: float = Field(..., ge=0)
    heating_system_tons: float = Field(..., ge=0)
    cooling_system_tons: float = Field(..., ge=0)
    design_temperatures: Dict[str, float]
    calculation_method: str = Field("ACCA Manual J")
    safety_factor: float = Field(1.1, ge=1.0, le=1.5)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('total_heating_btu_hr')
    def validate_total_heating(cls, v, values):
        if 'room_loads' in values:
            room_total = sum(r.heating_btu_hr for r in values['room_loads'])
            # Should be close to sum of rooms (with safety factor)
            if v < room_total * 0.9 or v > room_total * 1.5:
                raise ValueError(f"Total heating {v} inconsistent with room sum {room_total}")
        return v
    
    @validator('heating_system_tons')
    def validate_heating_tons(cls, v, values):
        if 'total_heating_btu_hr' in values:
            expected_tons = values['total_heating_btu_hr'] / 12000
            if abs(v - expected_tons) / expected_tons > 0.1:
                raise ValueError(f"Heating tons {v} inconsistent with BTU/hr")
        return v


class PipelineResult(BaseModel):
    """Complete pipeline result with all stage outputs"""
    # Stage outputs
    page_classification: PageClassificationOutput
    scale_detection: ScaleDetectionOutput
    geometry_extraction: GeometryExtractionOutput
    semantic_analysis: SemanticAnalysisOutput
    load_calculation: LoadCalculationOutput
    
    # Metadata
    project_id: str
    filename: str
    zip_code: str
    processing_time_seconds: float = Field(..., ge=0)
    pipeline_version: str = "2.0.0"
    success: bool = True
    warnings: List[str] = Field(default_factory=list)
    
    # Overall metrics
    total_area_sqft: float = Field(..., gt=0)
    num_rooms: int = Field(..., ge=1)
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator('num_rooms')
    def validate_room_counts_match(cls, v, values):
        """Ensure room counts are consistent across stages"""
        if 'geometry_extraction' in values:
            geom_rooms = len(values['geometry_extraction'].rooms)
            if v != geom_rooms:
                raise ValueError(f"Room count {v} doesn't match geometry {geom_rooms}")
        if 'semantic_analysis' in values:
            sem_rooms = len(values['semantic_analysis'].room_semantics)
            if v != sem_rooms:
                raise ValueError(f"Room count {v} doesn't match semantics {sem_rooms}")
        return v
    
    @validator('overall_confidence')
    def calculate_overall_confidence(cls, v, values):
        """Calculate weighted average of stage confidences"""
        confidences = []
        weights = []
        
        if 'page_classification' in values:
            confidences.append(values['page_classification'].confidence)
            weights.append(0.15)
        if 'scale_detection' in values:
            confidences.append(values['scale_detection'].confidence)
            weights.append(0.20)
        if 'geometry_extraction' in values:
            confidences.append(values['geometry_extraction'].confidence)
            weights.append(0.25)
        if 'semantic_analysis' in values:
            confidences.append(values['semantic_analysis'].confidence)
            weights.append(0.40)
        
        if confidences:
            return sum(c * w for c, w in zip(confidences, weights)) / sum(weights)
        return v


class StageInput(BaseModel):
    """Generic input for a pipeline stage"""
    pipeline_context: Dict[str, Any]
    previous_stage_output: Optional[Dict[str, Any]] = None
    stage_config: Dict[str, Any] = Field(default_factory=dict)
    
    
class StageOutput(BaseModel):
    """Generic output from a pipeline stage"""
    status: StageStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    duration_ms: float = Field(..., ge=0)
    

def validate_stage_transition(
    from_stage: str,
    to_stage: str,
    output_data: Dict[str, Any]
) -> bool:
    """
    Validate that data from one stage is valid for the next stage
    
    Args:
        from_stage: Name of the source stage
        to_stage: Name of the target stage
        output_data: Data being passed
        
    Returns:
        True if valid, raises ValidationError otherwise
    """
    transitions = {
        ("page_classification", "scale_detection"): PageClassificationOutput,
        ("scale_detection", "geometry_extraction"): ScaleDetectionOutput,
        ("geometry_extraction", "semantic_analysis"): GeometryExtractionOutput,
        ("semantic_analysis", "load_calculation"): SemanticAnalysisOutput,
    }
    
    key = (from_stage, to_stage)
    if key in transitions:
        # Validate against the expected model
        model_class = transitions[key]
        try:
            model_class(**output_data)
            return True
        except Exception as e:
            raise ValueError(f"Invalid data for {from_stage} -> {to_stage}: {e}")
    
    # Unknown transition
    raise ValueError(f"Unknown stage transition: {from_stage} -> {to_stage}")