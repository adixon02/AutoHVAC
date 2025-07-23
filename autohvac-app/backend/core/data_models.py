#!/usr/bin/env python3
"""
Centralized Data Models for AutoHVAC Blueprint Processing
Consolidates all data structures into a single source of truth
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Tuple, Optional, Union
from enum import Enum
from datetime import datetime
import json

class ConfidenceLevel(Enum):
    """Confidence levels for extracted data"""
    LOW = "low"           # < 0.4
    MEDIUM = "medium"     # 0.4 - 0.7
    HIGH = "high"         # 0.7 - 0.9
    VERY_HIGH = "very_high"  # > 0.9

class ProcessingStatus(Enum):
    """Processing status for jobs"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class BuildingType(Enum):
    """Types of buildings we can process"""
    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    COMMERCIAL_OFFICE = "commercial_office"
    COMMERCIAL_RETAIL = "commercial_retail"
    COMMERCIAL_WAREHOUSE = "commercial_warehouse"
    MIXED_USE = "mixed_use"

@dataclass
class ExtractionMetrics:
    """Metrics for extraction performance and quality"""
    extraction_time_seconds: float = 0.0
    pages_processed: int = 0
    text_blocks_analyzed: int = 0
    patterns_matched: int = 0
    confidence_weighted_score: float = 0.0
    processing_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ProjectInfo:
    """Project identification and metadata"""
    project_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    owner: str = ""
    architect: str = ""
    contractor: str = ""
    permit_number: str = ""
    drawing_date: str = ""
    revision_number: str = ""
    building_type: Optional[BuildingType] = None
    confidence_score: float = 0.0
    extraction_source: str = ""  # Which pattern/method found this data

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class BuildingCharacteristics:
    """Physical building characteristics"""
    total_area: float = 0.0
    main_residence_area: float = 0.0
    adu_area: float = 0.0          # Accessory Dwelling Unit
    garage_area: float = 0.0
    basement_area: float = 0.0
    attic_area: float = 0.0
    stories: int = 1
    ceiling_height: float = 9.0     # Default ceiling height
    construction_type: str = "new_construction"  # new_construction, retrofit, addition
    foundation_type: str = ""       # slab, crawlspace, basement, pier
    roof_type: str = ""            # gable, hip, shed, flat
    year_built: Optional[int] = None
    confidence_score: float = 0.0

    @property
    def conditioned_area(self) -> float:
        """Calculate total conditioned area"""
        return self.main_residence_area + self.adu_area + self.basement_area

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Room:
    """Individual room/space definition"""
    id: str
    name: str
    area: float
    floor_type: str = "main"        # main, upper, lower, basement
    ceiling_height: float = 9.0
    window_area: float = 0.0
    door_area: float = 0.0
    exterior_walls: int = 1         # Number of exterior walls
    interior_walls: int = 3         # Number of interior walls
    dimensions: str = ""            # "12x14" or similar
    room_type: str = ""            # bedroom, bathroom, kitchen, etc.
    occupancy: int = 0             # Number of typical occupants
    equipment_load: float = 0.0    # Internal equipment load (W)
    lighting_load: float = 0.0     # Lighting load (W)
    notes: str = ""
    confidence_score: float = 0.0

    @property
    def perimeter(self) -> float:
        """Estimate room perimeter from area (assuming rectangular)"""
        import math
        if self.area > 0:
            # Assume aspect ratio of 1.5:1 for estimation
            width = math.sqrt(self.area / 1.5)
            length = self.area / width
            return 2 * (width + length)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class InsulationSpecs:
    """Building envelope insulation specifications"""
    wall_r_value: float = 20.0        # R-20 modern standard
    ceiling_r_value: float = 49.0     # R-49 energy efficient
    floor_r_value: float = 19.0       # R-19 over unconditioned space
    foundation_r_value: float = 13.0   # R-13 basement walls
    window_u_value: float = 0.30      # U-0.30 double-pane standard
    door_u_value: float = 0.20        # U-0.20 insulated exterior door
    air_changes_per_hour: float = 0.35 # ACH50 blower door test
    wall_assembly_type: str = ""      # 2x4, 2x6, SIP, ICF, etc.
    window_type: str = "double_pane" # single_pane, double_pane, triple_pane
    building_tightness: str = "average" # tight, average, loose
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ExtractionGaps:
    """Identifies what data is missing or low confidence"""
    missing_required_fields: List[str] = field(default_factory=list)
    low_confidence_fields: List[str] = field(default_factory=list)
    assumptions_made: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    critical_gaps: List[str] = field(default_factory=list)

    @property
    def has_critical_gaps(self) -> bool:
        return len(self.critical_gaps) > 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ExtractionResult:
    """Complete extraction result with all data and metadata"""
    job_id: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    project_info: ProjectInfo = field(default_factory=ProjectInfo)
    building_chars: BuildingCharacteristics = field(default_factory=BuildingCharacteristics)
    rooms: List[Room] = field(default_factory=list)
    insulation: InsulationSpecs = field(default_factory=InsulationSpecs)
    gaps_identified: ExtractionGaps = field(default_factory=ExtractionGaps)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    extraction_metrics: ExtractionMetrics = field(default_factory=ExtractionMetrics)
    overall_confidence: float = 0.0
    processing_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level enum from score"""
        if self.overall_confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.overall_confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.overall_confidence >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    @property
    def is_complete(self) -> bool:
        """Check if extraction has minimum required data"""
        return (
            self.status == ProcessingStatus.COMPLETED and
            self.building_chars.total_area > 0 and
            len(self.rooms) > 0 and
            bool(self.project_info.zip_code)
        )

    def calculate_overall_confidence(self) -> float:
        """Calculate weighted overall confidence score"""
        weights = {
            'project_info': 0.15,
            'building_chars': 0.25,
            'rooms': 0.35,
            'insulation': 0.25
        }
        
        scores = [
            self.project_info.confidence_score * weights['project_info'],
            self.building_chars.confidence_score * weights['building_chars'],
            (sum(room.confidence_score for room in self.rooms) / len(self.rooms) if self.rooms else 0) * weights['rooms'],
            self.insulation.confidence_score * weights['insulation']
        ]
        
        self.overall_confidence = sum(scores)
        return self.overall_confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        result['created_at'] = self.created_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        result['status'] = self.status.value
        result['confidence_level'] = self.confidence_level.value
        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionResult':
        """Create from dictionary"""
        # Handle datetime conversion
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'completed_at' in data and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        # Handle enum conversion
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ProcessingStatus(data['status'])
            
        return cls(**data)

# Validation functions
def validate_extraction_result(result: ExtractionResult) -> List[str]:
    """Validate extraction result and return list of issues"""
    issues = []
    
    # Check required project info
    if not result.project_info.zip_code:
        issues.append("Missing ZIP code - required for climate zone determination")
    
    # Check building characteristics
    if result.building_chars.total_area <= 0:
        issues.append("Missing or invalid total building area")
    
    if result.building_chars.stories <= 0:
        issues.append("Missing or invalid number of stories")
    
    # Check rooms
    if not result.rooms:
        issues.append("No rooms found - at least one room is required")
    
    total_room_area = sum(room.area for room in result.rooms)
    if total_room_area > result.building_chars.total_area * 1.5:  # Allow 50% variance
        issues.append(f"Room areas ({total_room_area:.0f} sq ft) significantly exceed building area ({result.building_chars.total_area:.0f} sq ft)")
    
    # Check insulation values are reasonable
    if result.insulation.wall_r_value < 3 or result.insulation.wall_r_value > 60:
        issues.append(f"Wall R-value ({result.insulation.wall_r_value}) seems unreasonable")
    
    return issues

# Data class registry for dynamic instantiation
DATA_CLASS_REGISTRY = {
    'ProjectInfo': ProjectInfo,
    'BuildingCharacteristics': BuildingCharacteristics,
    'Room': Room,
    'InsulationSpecs': InsulationSpecs,
    'ExtractionGaps': ExtractionGaps,
    'ExtractionResult': ExtractionResult,
    'ExtractionMetrics': ExtractionMetrics
}