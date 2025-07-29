"""
Audit Models for ACCA Manual J Compliance Tracking

These models provide comprehensive audit trails for all HVAC load calculations,
ensuring professional-grade accountability and compliance with ACCA Manual J standards.
"""

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text, DateTime, Index
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class CalculationAudit(SQLModel, table=True):
    """
    Comprehensive audit record for each Manual J calculation
    
    This table stores detailed information about every load calculation
    to ensure ACCA compliance and enable professional review.
    """
    __tablename__ = "calculation_audits"
    
    # Primary identification
    audit_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True,
        description="Unique audit record identifier"
    )
    project_id: str = Field(
        index=True,
        description="Associated project identifier"
    )
    user_id: str = Field(
        index=True, 
        description="User who initiated the calculation"
    )
    
    # Calculation metadata
    calculation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the calculation was performed"
    )
    calculation_method: str = Field(
        default="ACCA Manual J 8th Edition",
        description="Calculation methodology used"
    )
    software_version: str = Field(
        default="AutoHVAC v1.0",
        description="Software version that performed calculation"
    )
    
    # Input data (for reproducibility)
    blueprint_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Complete blueprint schema used as input"
    )
    climate_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Climate data and design temperatures used"
    )
    system_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Duct configuration, heating fuel, and system parameters"
    )
    envelope_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Building envelope characteristics (if available)"
    )
    
    # Calculation results (for validation)
    calculation_results: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Complete calculation results"
    )
    heating_total_btu: Optional[int] = Field(
        default=None,
        description="Total heating load in BTU/hr"
    )
    cooling_total_btu: Optional[int] = Field(
        default=None,
        description="Total cooling load in BTU/hr"
    )
    
    # Quality and validation metrics
    data_quality_score: Optional[float] = Field(
        default=None,
        description="Data quality score (0.0-1.0)"
    )
    validation_flags: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Quality checks and validation warnings"
    )
    acca_compliance_verified: bool = Field(
        default=True,
        description="Whether calculation meets ACCA Manual J standards"
    )
    
    # Processing metadata
    processing_time_seconds: Optional[float] = Field(
        default=None,
        description="Time taken to complete calculation"
    )
    processing_stages: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detailed processing stage information"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Error information if calculation failed"
    )
    
    # Professional review fields
    reviewed_by: Optional[str] = Field(
        default=None,
        description="Professional reviewer identifier"
    )
    review_timestamp: Optional[datetime] = Field(
        default=None,
        description="When the calculation was professionally reviewed"
    )
    review_notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Professional review comments"
    )
    review_approved: Optional[bool] = Field(
        default=None,
        description="Whether calculation was approved by reviewer"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calc_audit_project_user', 'project_id', 'user_id'),
        Index('idx_calc_audit_timestamp', 'calculation_timestamp'),
        Index('idx_calc_audit_loads', 'heating_total_btu', 'cooling_total_btu'),
    )


class RoomCalculationDetail(SQLModel, table=True):
    """
    Detailed calculation breakdown for each room/zone
    
    This table stores room-by-room calculations for audit purposes,
    enabling detailed review of load calculation components.
    """
    __tablename__ = "room_calculation_details"
    
    # Primary identification
    detail_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique detail record identifier"
    )
    audit_id: str = Field(
        foreign_key="calculation_audits.audit_id",
        index=True,
        description="Associated audit record"
    )
    
    # Room identification
    room_name: str = Field(
        description="Room name from blueprint"
    )
    room_area_sqft: float = Field(
        description="Room area in square feet"
    )
    room_type: str = Field(
        description="Classified room type (living, bedroom, etc.)"
    ) 
    floor_number: int = Field(
        description="Floor number (1-based)"
    )
    
    # Room characteristics
    dimensions_ft: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Room dimensions (width, length, height)"
    )
    window_count: int = Field(
        default=0,
        description="Number of windows"
    )
    orientation: Optional[str] = Field(
        default=None,
        description="Primary room orientation (N, S, E, W, etc.)"
    )
    
    # Load calculation components
    heating_load_btu: float = Field(
        description="Room heating load in BTU/hr"
    )
    cooling_load_btu: float = Field(
        description="Room cooling load in BTU/hr"
    )
    
    # Detailed load breakdown
    load_components: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detailed breakdown of load components (walls, windows, etc.)"
    )
    
    # Airflow and ductwork
    required_airflow_cfm: Optional[int] = Field(
        default=None,
        description="Required airflow in CFM"
    )
    recommended_duct_size: Optional[str] = Field(
        default=None,
        description="Recommended duct size"
    )
    
    # Calculation metadata
    calculation_method: str = Field(
        description="Method used for this room (CLF/CLTD, simplified, etc.)"
    )
    data_confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for room data (0.0-1.0)"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_room_detail_audit', 'audit_id'),
        Index('idx_room_detail_loads', 'heating_load_btu', 'cooling_load_btu'),
    )


class DataSourceMetadata(SQLModel, table=True):
    """
    Metadata about data sources used in calculations
    
    This table tracks the source and quality of data used in each
    calculation to ensure transparency and reproducibility.
    """
    __tablename__ = "data_source_metadata"
    
    # Primary identification
    metadata_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique metadata record identifier"
    )
    audit_id: str = Field(
        foreign_key="calculation_audits.audit_id",
        index=True,
        description="Associated audit record"
    )
    
    # Data source information
    source_type: str = Field(
        description="Type of data source (climate, blueprint, envelope, etc.)"
    )
    source_name: str = Field(
        description="Specific source name or identifier"
    )
    source_version: Optional[str] = Field(
        default=None,
        description="Version of data source"
    )
    
    # Data quality metrics
    data_completeness: float = Field(
        description="Data completeness score (0.0-1.0)"
    )
    data_confidence: float = Field(
        description="Confidence in data accuracy (0.0-1.0)"
    )
    extraction_method: str = Field(
        description="How data was extracted (AI, manual, database, etc.)"
    )
    
    # Source metadata
    source_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata about the data source"
    )
    
    # Timestamps
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When data was extracted"
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        description="When source data was last updated"
    )


class ComplianceCheck(SQLModel, table=True):
    """
    ACCA Manual J compliance verification records
    
    This table stores detailed compliance checks to ensure
    calculations meet professional standards.
    """
    __tablename__ = "compliance_checks"
    
    # Primary identification  
    check_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique compliance check identifier"
    )
    audit_id: str = Field(
        foreign_key="calculation_audits.audit_id",
        index=True,
        description="Associated audit record"
    )
    
    # Compliance check details
    check_category: str = Field(
        description="Category of check (load_range, zone_balance, etc.)"
    )
    check_name: str = Field(
        description="Specific check name"
    )
    check_description: str = Field(
        description="Description of what was checked"
    )
    
    # Check results
    passed: bool = Field(
        description="Whether the check passed"
    )
    check_value: Optional[float] = Field(
        default=None,
        description="Measured value (if applicable)"
    )
    expected_range_min: Optional[float] = Field(
        default=None,
        description="Minimum expected value"
    )
    expected_range_max: Optional[float] = Field(
        default=None,
        description="Maximum expected value"
    )
    
    # Check metadata
    severity: str = Field(
        default="warning",
        description="Severity level (info, warning, error, critical)"
    )
    recommendation: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Recommendation if check failed"
    )
    
    # Timestamp
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When check was performed"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_compliance_audit', 'audit_id'),
        Index('idx_compliance_category', 'check_category', 'passed'),
    )