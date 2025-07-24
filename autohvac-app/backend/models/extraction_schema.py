"""
JSON Schema Models for Blueprint Extraction Intermediate Layer
Comprehensive data structures for PDF extraction, analysis, and storage
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class ExtractionVersion(str, Enum):
    """Version tracking for extraction algorithms"""
    V1_0 = "1.0.0"  # Initial regex-only extraction
    V1_1 = "1.1.0"  # Added AI visual analysis
    V1_2 = "1.2.0"  # Enhanced pattern matching
    CURRENT = "1.2.0"

class ExtractionMethod(str, Enum):
    """Method used for data extraction"""
    REGEX_ONLY = "regex_only"
    AI_ONLY = "ai_only" 
    REGEX_AND_AI = "regex_and_ai_combined"
    FALLBACK = "fallback_mock_data"

class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted data"""
    HIGH = "high"      # 0.8-1.0
    MEDIUM = "medium"  # 0.5-0.79
    LOW = "low"        # 0.2-0.49
    NONE = "none"      # 0.0-0.19

# === PDF Metadata ===
class PDFMetadata(BaseModel):
    """Metadata about the uploaded PDF file"""
    filename: str
    original_filename: str
    file_size_bytes: int
    file_size_mb: float
    page_count: int
    uploaded_at: datetime
    pdf_version: Optional[str] = None
    has_text_layer: bool = True
    is_scanned: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === Extraction Results ===
class RegexExtractionResult(BaseModel):
    """Results from regex-based pattern matching extraction"""
    
    # Building characteristics
    floor_area_ft2: Optional[float] = None
    wall_insulation: Optional[Dict[str, float]] = None  # {"cavity": 21, "continuous": 5}
    ceiling_insulation: Optional[float] = None  # R-value
    window_schedule: Optional[Dict[str, Any]] = None  # {"total_area": 150, "u_value": 0.30, "shgc": 0.65}
    air_tightness: Optional[float] = None  # ACH50
    foundation_type: Optional[str] = None
    orientation: Optional[str] = None
    
    # Room data
    room_dimensions: Optional[List[Dict[str, Any]]] = None
    
    # Extraction metadata
    patterns_matched: Dict[str, List[str]] = Field(default_factory=dict)  # pattern_name -> [matched_strings]
    confidence_scores: Dict[str, float] = Field(default_factory=dict)  # field_name -> confidence
    extraction_notes: List[str] = Field(default_factory=list)  # Warnings, assumptions made
    
    def get_overall_confidence(self) -> float:
        """Calculate overall confidence across all fields"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)

class AIExtractionResult(BaseModel):
    """Results from AI-powered visual analysis"""
    
    # Room analysis
    room_layouts: Optional[List[Dict[str, Any]]] = None  # Room positions, orientations, adjacencies
    window_orientations: Optional[Dict[str, List[str]]] = None  # {"north": ["bedroom1"], "south": ["living"]}
    
    # Building envelope
    building_envelope: Optional[Dict[str, Any]] = None  # Wall types, roof details, foundation
    architectural_details: Optional[Dict[str, Any]] = None  # Ceiling heights, structural elements
    
    # HVAC existing
    hvac_existing: Optional[Dict[str, Any]] = None  # Existing equipment and ductwork
    
    # AI metadata
    model_used: str = "gpt-4-vision-preview"
    ai_confidence: float = 0.0
    processing_tokens: Optional[int] = None
    api_cost_usd: Optional[float] = None
    visual_analysis_notes: List[str] = Field(default_factory=list)
    
    # Enhanced room data
    room_count_detected: Optional[int] = None
    floor_plan_type: Optional[str] = None  # "ranch", "two_story", "split_level"
    architectural_style: Optional[str] = None

class ProcessingMetadata(BaseModel):
    """Metadata about the extraction processing"""
    extraction_id: str
    job_id: str
    extraction_timestamp: datetime
    processing_duration_ms: int
    extraction_version: ExtractionVersion
    extraction_method: ExtractionMethod
    
    # Error handling
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Performance metrics
    text_extraction_ms: Optional[int] = None
    regex_processing_ms: Optional[int] = None
    ai_processing_ms: Optional[int] = None
    
    # System info
    server_version: Optional[str] = None
    python_version: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === Complete Extraction Result ===
class CompleteExtractionResult(BaseModel):
    """Complete extraction result with all data and metadata"""
    
    # Core identification
    extraction_id: str = Field(..., description="Unique identifier for this extraction")
    job_id: str = Field(..., description="Blueprint job ID")
    
    # PDF information
    pdf_metadata: PDFMetadata
    
    # Raw extracted data
    raw_text: str = Field(..., description="Complete text extracted from PDF")
    raw_text_by_page: List[str] = Field(default_factory=list, description="Text by page")
    
    # Extraction results
    regex_extraction: Optional[RegexExtractionResult] = None
    ai_extraction: Optional[AIExtractionResult] = None
    
    # Processing info
    processing_metadata: ProcessingMetadata
    
    # Combined/final data (for backward compatibility)
    final_building_data: Optional[Dict[str, Any]] = None
    final_room_data: Optional[List[Dict[str, Any]]] = None
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get a summary of what was successfully extracted"""
        summary = {
            "extraction_id": self.extraction_id,
            "method": self.processing_metadata.extraction_method,
            "timestamp": self.processing_metadata.extraction_timestamp,
            "duration_ms": self.processing_metadata.processing_duration_ms,
            "has_errors": len(self.processing_metadata.errors) > 0,
            "has_warnings": len(self.processing_metadata.warnings) > 0
        }
        
        if self.regex_extraction:
            summary["regex_confidence"] = self.regex_extraction.get_overall_confidence()
            summary["regex_fields_found"] = len([k for k, v in self.regex_extraction.dict().items() 
                                               if v is not None and k not in ['patterns_matched', 'confidence_scores', 'extraction_notes']])
        
        if self.ai_extraction:
            summary["ai_confidence"] = self.ai_extraction.ai_confidence
            summary["ai_model"] = self.ai_extraction.model_used
            summary["rooms_detected"] = self.ai_extraction.room_count_detected
        
        return summary
    
    def get_field_confidence(self, field_name: str) -> Optional[float]:
        """Get confidence score for a specific field"""
        if self.regex_extraction and field_name in self.regex_extraction.confidence_scores:
            return self.regex_extraction.confidence_scores[field_name]
        return None
    
    def has_field(self, field_name: str) -> bool:
        """Check if a field was successfully extracted"""
        if self.regex_extraction:
            return getattr(self.regex_extraction, field_name, None) is not None
        return False

# === Storage and Versioning ===
class ExtractionStorageInfo(BaseModel):
    """Information about stored extraction data"""
    extraction_id: str
    job_id: str
    storage_path: str
    file_size_bytes: int
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    retention_expires_at: Optional[datetime] = None
    is_compressed: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === Test Data Models ===
class ExtractionTestCase(BaseModel):
    """Test case for extraction algorithm validation"""
    test_id: str
    test_name: str
    description: str
    pdf_filename: str
    expected_results: Dict[str, Any]
    tolerance_levels: Dict[str, float] = Field(default_factory=dict)  # field -> acceptable error %
    test_category: str = "general"  # "residential", "commercial", "complex", etc.
    created_by: str = "system"
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === API Response Models ===
class ExtractionDebugResponse(BaseModel):
    """Response for extraction debug endpoints"""
    extraction_id: str
    job_id: str
    extraction_summary: Dict[str, Any]
    raw_extraction_data: Optional[CompleteExtractionResult] = None
    available_reprocessing_options: List[str] = Field(default_factory=list)

class ReprocessingRequest(BaseModel):
    """Request for reprocessing extraction data"""
    job_id: str
    reprocessing_method: ExtractionMethod = ExtractionMethod.REGEX_AND_AI
    force_ai_reanalysis: bool = False
    override_confidence_threshold: Optional[float] = None
    custom_analysis_prompt: Optional[str] = None