"""
Enhanced Audit Tracking System for ACCA Manual J Compliance

Provides comprehensive audit trails for all calculation inputs, outputs, and
professional review processes to ensure ACCA Manual J 8th Edition compliance.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from utils.json_utils import safe_dict, ensure_json_serializable

from app.parser.schema import BlueprintSchema
from .envelope_extractor import EnvelopeExtraction
from models.audit import (
    CalculationAudit, RoomCalculationDetail, 
    DataSourceMetadata, ComplianceCheck
)
from database import SyncSessionLocal
import logging

# Version tracking for calculation changes
CALCULATION_VERSION = "2.0.0"  # Updated for Phase 2 enhancements

# Import database health check
try:
    from services.db_health import check_table_exists, AUDIT_TABLES_EXIST
except ImportError:
    # Fallback if db_health module not available yet
    AUDIT_TABLES_EXIST = None
    def check_table_exists(table_name: str) -> bool:
        return True  # Assume tables exist if we can't check


@dataclass
class AuditSnapshot:
    """Complete audit snapshot of a Manual J calculation"""
    
    # Required fields (no defaults)
    calculation_id: str
    timestamp: str
    calculation_version: str
    blueprint_schema: Dict[str, Any]
    
    # Optional fields (with defaults)
    user_id: Optional[str] = None
    construction_vintage: Optional[str] = None
    duct_config: str = "ducted_attic"
    heating_fuel: str = "gas"
    include_ventilation: bool = True
    
    # Climate data used
    climate_data: Dict[str, Any] = None
    zip_code: str = None
    climate_zone: str = None
    design_temps: Dict[str, float] = None
    
    # Page selection audit data (new for multi-page support)
    page_selection_data: Optional[Dict[str, Any]] = None
    selected_page_number: Optional[int] = None
    total_pages_analyzed: Optional[int] = None
    page_selection_score: Optional[float] = None
    
    # Envelope data (if extracted)
    envelope_extraction: Optional[Dict[str, Any]] = None
    envelope_confidence_flags: List[str] = None
    
    # Construction assumptions used
    construction_values: Dict[str, float] = None
    calculation_method: str = "Simplified"
    
    # Load calculation details
    room_calculations: List[Dict[str, Any]] = None
    diversity_factor: float = 1.0
    duct_loss_factor: float = 1.15
    safety_factor: float = 1.1
    
    # Final results
    heating_total: float = 0.0
    cooling_total: float = 0.0
    equipment_recommendations: Dict[str, Any] = None
    
    # Validation flags
    validation_warnings: List[str] = None
    confidence_issues: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return ensure_json_serializable(asdict(self))
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditSnapshot':
        """Create from dictionary"""
        return cls(**data)


class AuditTracker:
    """Manages audit snapshots for Manual J calculations"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize audit tracker
        
        Args:
            storage_path: Path to store audit files (default: ./audit_logs)
        """
        self.storage_path = Path(storage_path or "./audit_logs")
        self.storage_path.mkdir(exist_ok=True)
    
    def create_snapshot(self, 
                       blueprint_schema: BlueprintSchema,
                       calculation_result: Dict[str, Any],
                       climate_data: Dict[str, Any],
                       construction_vintage: Optional[str] = None,
                       envelope_data: Optional[EnvelopeExtraction] = None,
                       user_id: Optional[str] = None,
                       **kwargs) -> AuditSnapshot:
        """
        Create comprehensive audit snapshot
        
        Args:
            blueprint_schema: Input blueprint data
            calculation_result: Complete calculation results
            climate_data: Climate data used
            construction_vintage: Construction vintage specified
            envelope_data: AI-extracted envelope data (if any)
            user_id: User performing calculation
            **kwargs: Additional parameters
            
        Returns:
            AuditSnapshot with complete calculation audit trail
        """
        calculation_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract design parameters from result
        design_params = calculation_result.get("design_parameters", {})
        
        # Prepare envelope extraction data
        envelope_dict = None
        confidence_flags = []
        
        if envelope_data:
            envelope_dict = envelope_data.to_dict() if hasattr(envelope_data, 'to_dict') else {
                'wall_construction': envelope_data.wall_construction,
                'wall_r_value': envelope_data.wall_r_value,
                'wall_confidence': envelope_data.wall_confidence,
                'roof_construction': envelope_data.roof_construction, 
                'roof_r_value': envelope_data.roof_r_value,
                'roof_confidence': envelope_data.roof_confidence,
                'window_type': envelope_data.window_type,
                'window_u_factor': envelope_data.window_u_factor,
                'window_confidence': envelope_data.window_confidence,
                'ceiling_height': envelope_data.ceiling_height,
                'ceiling_height_confidence': envelope_data.ceiling_height_confidence,
                'infiltration_class': envelope_data.infiltration_class,
                'infiltration_confidence': envelope_data.infiltration_confidence,
                'estimated_vintage': envelope_data.estimated_vintage,
                'overall_confidence': envelope_data.overall_confidence
            }
            confidence_flags = getattr(envelope_data, 'needs_confirmation', [])
        
        # Create validation warnings
        validation_warnings = self._generate_validation_warnings(
            calculation_result, envelope_data, blueprint_schema
        )
        
        # Create confidence issues list
        confidence_issues = self._identify_confidence_issues(
            envelope_data, calculation_result
        )
        
        snapshot = AuditSnapshot(
            calculation_id=calculation_id,
            timestamp=timestamp,
            calculation_version=CALCULATION_VERSION,
            user_id=user_id,
            
            # Input data
            blueprint_schema=safe_dict(blueprint_schema),
            construction_vintage=construction_vintage,
            duct_config=kwargs.get('duct_config', 'ducted_attic'),
            heating_fuel=kwargs.get('heating_fuel', 'gas'),
            include_ventilation=kwargs.get('include_ventilation', True),
            
            # Climate data
            climate_data=climate_data,
            zip_code=getattr(blueprint_schema, 'zip_code', None) if blueprint_schema else None,
            climate_zone=climate_data.get('climate_zone') if climate_data else None,
            design_temps={
                'heating_db_99': climate_data.get('heating_db_99') if climate_data else None,
                'cooling_db_1': climate_data.get('cooling_db_1') if climate_data else None,
                'outdoor_heating_temp': design_params.get('outdoor_heating_temp'),
                'outdoor_cooling_temp': design_params.get('outdoor_cooling_temp')
            },
            
            # Envelope data
            envelope_extraction=envelope_dict,
            envelope_confidence_flags=confidence_flags,
            
            # Construction assumptions
            construction_values=design_params.get('construction_values'),
            calculation_method=design_params.get('calculation_method', 'Simplified'),
            
            # Load calculation details
            room_calculations=calculation_result.get('zones', []),
            diversity_factor=design_params.get('diversity_factor', 1.0),
            duct_loss_factor=design_params.get('duct_loss_factor', 1.15),
            safety_factor=design_params.get('safety_factor', 1.1),
            
            # Results
            heating_total=calculation_result.get('heating_total', 0),
            cooling_total=calculation_result.get('cooling_total', 0),
            equipment_recommendations=calculation_result.get('equipment_recommendations'),
            
            # Validation
            validation_warnings=validation_warnings,
            confidence_issues=confidence_issues
        )
        
        return snapshot
    
    def save_snapshot(self, snapshot: AuditSnapshot) -> str:
        """
        Save audit snapshot to storage
        
        Args:
            snapshot: AuditSnapshot to save
            
        Returns:
            Path to saved snapshot file
        """
        # Create filename with timestamp and calculation ID
        timestamp_str = datetime.fromisoformat(snapshot.timestamp.replace('Z', '+00:00')).strftime('%Y%m%d_%H%M%S')
        filename = f"audit_{timestamp_str}_{snapshot.calculation_id[:8]}.json"
        filepath = self.storage_path / filename
        
        # Save to file
        with open(filepath, 'w') as f:
            f.write(snapshot.to_json())
        
        return str(filepath)
    
    def load_snapshot(self, calculation_id: str) -> Optional[AuditSnapshot]:
        """
        Load audit snapshot by calculation ID
        
        Args:
            calculation_id: ID of calculation to load
            
        Returns:
            AuditSnapshot if found, None otherwise
        """
        # Search for file with matching calculation ID
        for filepath in self.storage_path.glob(f"audit_*_{calculation_id[:8]}.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    return AuditSnapshot.from_dict(data)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        
        return None
    
    def list_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent audit snapshots
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of snapshot metadata
        """
        snapshots = []
        
        # Get all audit files, sorted by modification time (newest first)
        audit_files = sorted(
            self.storage_path.glob("audit_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for filepath in audit_files[:limit]:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    snapshots.append({
                        'calculation_id': data.get('calculation_id'),
                        'timestamp': data.get('timestamp'),
                        'zip_code': data.get('zip_code'),
                        'calculation_method': data.get('calculation_method'),
                        'heating_total': data.get('heating_total'),
                        'cooling_total': data.get('cooling_total'),
                        'has_envelope_data': data.get('envelope_extraction') is not None,
                        'confidence_issues_count': len(data.get('confidence_issues', [])),
                        'filepath': str(filepath)
                    })
            except (json.JSONDecodeError, TypeError):
                continue
        
        return snapshots
    
    def _generate_validation_warnings(self, 
                                    calculation_result: Dict[str, Any],
                                    envelope_data: Optional[EnvelopeExtraction],
                                    blueprint_schema: BlueprintSchema) -> List[str]:
        """Generate validation warnings for calculation"""
        warnings = []
        
        # Safety check for missing blueprint schema
        if not blueprint_schema:
            warnings.append("Blueprint schema missing - cannot validate calculations")
            return warnings
        
        # Check for unrealistic loads
        heating_total = calculation_result.get('heating_total', 0) if calculation_result else 0
        cooling_total = calculation_result.get('cooling_total', 0) if calculation_result else 0
        total_sqft = getattr(blueprint_schema, 'sqft_total', 0) if blueprint_schema else 0
        
        if total_sqft > 0:
            heating_per_sqft = heating_total / total_sqft
            cooling_per_sqft = cooling_total / total_sqft
            
            if heating_per_sqft > 80:
                warnings.append(f"High heating load: {heating_per_sqft:.1f} BTU/hr/sqft (typical: 20-60)")
            
            if cooling_per_sqft > 40:
                warnings.append(f"High cooling load: {cooling_per_sqft:.1f} BTU/hr/sqft (typical: 15-30)")
            
            if heating_per_sqft < 10:
                warnings.append(f"Low heating load: {heating_per_sqft:.1f} BTU/hr/sqft (may indicate missing data)")
        
        # Check room count vs total area
        room_count = len(blueprint_schema.rooms) if blueprint_schema and hasattr(blueprint_schema, 'rooms') else 0
        if room_count > 0:
            avg_room_size = total_sqft / room_count
            if avg_room_size < 50:
                warnings.append(f"Very small average room size: {avg_room_size:.0f} sqft")
            elif avg_room_size > 500:
                warnings.append(f"Very large average room size: {avg_room_size:.0f} sqft")
        
        # Check envelope data consistency
        if envelope_data:
            if envelope_data.overall_confidence < 0.5:
                warnings.append("Low overall confidence in envelope data extraction")
            
            # Check for realistic R-values
            if envelope_data.wall_r_value < 5 or envelope_data.wall_r_value > 50:
                warnings.append(f"Unusual wall R-value: R-{envelope_data.wall_r_value}")
            
            if envelope_data.roof_r_value < 10 or envelope_data.roof_r_value > 70:
                warnings.append(f"Unusual roof R-value: R-{envelope_data.roof_r_value}")
        
        return warnings
    
    def _identify_confidence_issues(self, 
                                  envelope_data: Optional[EnvelopeExtraction],
                                  calculation_result: Dict[str, Any]) -> List[str]:
        """Identify confidence issues in calculation"""
        issues = []
        
        if envelope_data:
            # Add needs_confirmation items
            if envelope_data.needs_confirmation:
                issues.extend([f"Low confidence: {item}" for item in envelope_data.needs_confirmation])
            
            # Check for missing critical data
            if envelope_data.wall_confidence < 0.6:
                issues.append("Wall construction data uncertain - using defaults")
            
            if envelope_data.ceiling_height_confidence < 0.6:
                issues.append("Ceiling height uncertain - using 9ft default")
        else:
            issues.append("No envelope data extracted - using construction vintage defaults")
        
        # Check calculation method
        design_params = calculation_result.get("design_parameters", {})
        calc_method = design_params.get("calculation_method", "Simplified")
        
        if calc_method == "Simplified":
            issues.append("Using simplified calculation method - consider providing construction details")
        
        return issues


# Global audit tracker instance
_audit_tracker = None


def get_audit_tracker() -> AuditTracker:
    """Get global audit tracker instance"""
    global _audit_tracker
    if _audit_tracker is None:
        _audit_tracker = AuditTracker()
    return _audit_tracker


def create_calculation_audit(
    blueprint_schema: Optional[BlueprintSchema],
    calculation_result: Optional[Dict[str, Any]],
    climate_data: Optional[Dict[str, Any]],
    construction_vintage: Optional[str] = None,
    envelope_data: Optional[EnvelopeExtraction] = None,
    user_id: Optional[str] = None,
    duct_config: str = "ducted_attic",
    heating_fuel: str = "gas",
    include_ventilation: bool = True,
    processing_metadata: Optional[Dict[str, Any]] = None,
    error_details: Optional[Dict[str, Any]] = None,
    page_selection_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create comprehensive audit record in database for ACCA Manual J compliance
    
    Args:
        blueprint_schema: Parsed blueprint (None if processing failed)
        calculation_result: Manual J calculation results (None if failed)
        climate_data: Climate data used in calculations
        construction_vintage: Building construction era
        envelope_data: AI-extracted envelope characteristics
        user_id: User who initiated calculation
        duct_config: Duct system configuration
        heating_fuel: Heating system fuel type
        include_ventilation: Whether ventilation loads were included
        processing_metadata: Detailed processing information
        error_details: Error information if calculation failed
        page_selection_data: Multi-page PDF analysis and selection data
        
    Returns:
        Audit ID for future reference
    """
    logger = logging.getLogger(__name__)
    audit_id = str(uuid.uuid4())
    
    # Check if audit tables exist before attempting database operations
    if AUDIT_TABLES_EXIST is False:
        logger.warning("Audit tables do not exist in database, falling back to file-based audit")
        # Jump directly to file-based fallback
        try:
            tracker = get_audit_tracker()
            snapshot = tracker.create_snapshot(
                blueprint_schema=blueprint_schema,
                calculation_result=calculation_result or {},
                climate_data=climate_data or {},
                construction_vintage=construction_vintage,
                envelope_data=envelope_data,
                user_id=user_id,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                include_ventilation=include_ventilation
            )
            filepath = tracker.save_snapshot(snapshot)
            logger.info(f"File-based audit snapshot saved: {filepath}")
            return snapshot.calculation_id
        except Exception as fallback_error:
            logger.error(f"Even file-based audit failed: {fallback_error}")
            return audit_id
    
    try:
        with SyncSessionLocal() as session:
            # Create main audit record
            calculation_audit = CalculationAudit(
                audit_id=audit_id,
                project_id=str(blueprint_schema.project_id) if blueprint_schema and hasattr(blueprint_schema, 'project_id') else "unknown",
                user_id=user_id or "system",
                calculation_timestamp=datetime.utcnow(),
                calculation_method="ACCA Manual J 8th Edition",
                software_version=f"AutoHVAC v{CALCULATION_VERSION}",
                
                # Input data
                blueprint_schema=safe_dict(blueprint_schema) if blueprint_schema else None,
                climate_data=ensure_json_serializable(climate_data),
                system_parameters={
                    'duct_config': duct_config,
                    'heating_fuel': heating_fuel,
                    'construction_vintage': construction_vintage,
                    'include_ventilation': include_ventilation,
                    'page_selection': page_selection_data
                },
                envelope_data=safe_dict(envelope_data) if envelope_data else None,
                
                # Results
                calculation_results=calculation_result,
                heating_total_btu=calculation_result.get('heating_total') if calculation_result else None,
                cooling_total_btu=calculation_result.get('cooling_total') if calculation_result else None,
                
                # Quality metrics
                data_quality_score=_calculate_data_quality_score(
                    blueprint_schema, envelope_data, climate_data
                ),
                validation_flags=_extract_validation_flags(calculation_result, processing_metadata),
                acca_compliance_verified=error_details is None and calculation_result is not None,
                
                # Processing metadata
                processing_time_seconds=processing_metadata.get('processing_time_seconds') if processing_metadata else None,
                processing_stages=processing_metadata.get('stages_completed') if processing_metadata else None,
                error_details=error_details
            )
            
            session.add(calculation_audit)
            session.flush()  # Get the ID
            
            # Create room-level detail records
            if blueprint_schema and calculation_result and calculation_result.get('zones'):
                for zone in calculation_result['zones']:
                    room_detail = RoomCalculationDetail(
                        audit_id=audit_id,
                        room_name=zone['name'],
                        room_area_sqft=zone['area'],
                        room_type=zone.get('room_type', 'unknown'),
                        floor_number=zone.get('floor', 1),
                        window_count=_find_room_windows(blueprint_schema, zone['name']),
                        orientation=_find_room_orientation(blueprint_schema, zone['name']),
                        heating_load_btu=zone['heating_btu'],
                        cooling_load_btu=zone['cooling_btu'],
                        load_components=zone.get('load_breakdown'),
                        required_airflow_cfm=zone.get('cfm_required'),
                        recommended_duct_size=zone.get('duct_size'),
                        calculation_method=zone.get('calculation_method', 'Manual J'),
                        data_confidence=_calculate_room_confidence(blueprint_schema, zone['name'])
                    )
                    session.add(room_detail)
            
            # Create data source metadata records
            if climate_data:
                climate_metadata = DataSourceMetadata(
                    audit_id=audit_id,
                    source_type="climate_data",
                    source_name="ASHRAE/IECC Climate Database",
                    source_version="2021",
                    data_completeness=1.0 if climate_data.get('found') else 0.5,
                    data_confidence=0.95 if climate_data.get('found') else 0.7,
                    extraction_method="database_lookup",
                    source_metadata=ensure_json_serializable(climate_data)
                )
                session.add(climate_metadata)
            
            if blueprint_schema:
                blueprint_metadata = DataSourceMetadata(
                    audit_id=audit_id,
                    source_type="blueprint_data",
                    source_name="AI Blueprint Parser",
                    source_version=CALCULATION_VERSION,
                    data_completeness=_calculate_blueprint_completeness(blueprint_schema),
                    data_confidence=_calculate_blueprint_confidence(blueprint_schema),
                    extraction_method="ai_analysis",
                    source_metadata={'rooms_count': len(blueprint_schema.rooms), 'total_area': blueprint_schema.sqft_total}
                )
                session.add(blueprint_metadata)
            
            if envelope_data:
                envelope_metadata = DataSourceMetadata(
                    audit_id=audit_id,
                    source_type="envelope_data",
                    source_name="AI Envelope Extractor", 
                    source_version=CALCULATION_VERSION,
                    data_completeness=envelope_data.overall_confidence if hasattr(envelope_data, 'overall_confidence') else 0.8,
                    data_confidence=envelope_data.overall_confidence if hasattr(envelope_data, 'overall_confidence') else 0.8,
                    extraction_method="ai_analysis",
                    source_metadata=safe_dict(envelope_data)
                )
                session.add(envelope_metadata)
            
            # Create compliance check records
            if calculation_result:
                compliance_checks = _create_compliance_checks(audit_id, blueprint_schema, calculation_result)
                for check in compliance_checks:
                    session.add(check)
            
            session.commit()
            logger.info(f"Created comprehensive audit record: {audit_id}")
            
            return audit_id
            
    except Exception as e:
        logger.exception(f"Failed to create audit record: {e}")
        # Fallback to file-based audit for debugging
        try:
            tracker = get_audit_tracker()
            snapshot = tracker.create_snapshot(
                blueprint_schema=blueprint_schema,
                calculation_result=calculation_result or {},
                climate_data=climate_data or {},
                construction_vintage=construction_vintage,
                envelope_data=envelope_data,
                user_id=user_id,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                include_ventilation=include_ventilation
            )
            filepath = tracker.save_snapshot(snapshot)
            logger.info(f"Fallback audit snapshot saved: {filepath}")
            return snapshot.calculation_id
        except Exception as fallback_error:
            logger.exception(f"Fallback audit also failed: {fallback_error}")
            return audit_id


def _calculate_data_quality_score(
    blueprint_schema: Optional[BlueprintSchema],
    envelope_data: Optional[EnvelopeExtraction],
    climate_data: Optional[Dict]
) -> float:
    """Calculate overall data quality score (0.0-1.0)"""
    score = 0.0
    factors = 0
    
    # Blueprint data quality (40% weight)
    if blueprint_schema:
        blueprint_score = 0.6  # Base score for having blueprint
        if len(blueprint_schema.rooms) > 0:
            blueprint_score += 0.2
        if blueprint_schema.sqft_total > 0:
            blueprint_score += 0.1
        if any(room.orientation for room in blueprint_schema.rooms):
            blueprint_score += 0.1
        score += blueprint_score * 0.4
        factors += 0.4
    
    # Climate data quality (30% weight)
    if climate_data:
        climate_score = 0.9 if climate_data.get('found') else 0.5
        score += climate_score * 0.3
        factors += 0.3
    
    # Envelope data quality (30% weight)
    if envelope_data:
        envelope_score = getattr(envelope_data, 'overall_confidence', 0.7)
        score += envelope_score * 0.3
        factors += 0.3
    
    return score / factors if factors > 0 else 0.5


def _extract_validation_flags(
    calculation_result: Optional[Dict],
    processing_metadata: Optional[Dict]
) -> Dict[str, Any]:
    """Extract validation flags and warnings"""
    flags = {
        'processing_errors': [],
        'calculation_warnings': [],
        'data_quality_issues': []
    }
    
    if processing_metadata:
        if processing_metadata.get('errors_encountered'):
            flags['processing_errors'] = processing_metadata['errors_encountered']
    
    if calculation_result:
        if calculation_result.get('audit_information', {}).get('calculation_warnings'):
            flags['calculation_warnings'] = calculation_result['audit_information']['calculation_warnings']
    
    return flags


def _find_room_windows(blueprint_schema: BlueprintSchema, room_name: str) -> int:
    """Find window count for a specific room"""
    if not blueprint_schema:
        return 0
    for room in blueprint_schema.rooms:
        if room.name == room_name:
            return room.windows
    return 0


def _find_room_orientation(blueprint_schema: BlueprintSchema, room_name: str) -> Optional[str]:
    """Find orientation for a specific room"""
    if not blueprint_schema:
        return None
    for room in blueprint_schema.rooms:
        if room.name == room_name:
            return room.orientation
    return None


def _calculate_room_confidence(blueprint_schema: BlueprintSchema, room_name: str) -> float:
    """Calculate confidence score for room data"""
    if not blueprint_schema:
        return 0.0
    
    for room in blueprint_schema.rooms:
        if room.name == room_name:
            confidence = 0.6  # Base confidence
            if room.area > 0:
                confidence += 0.2
            if room.orientation:
                confidence += 0.1
            if room.windows >= 0:
                confidence += 0.1
            return confidence
    return 0.0


def _calculate_blueprint_completeness(blueprint_schema: BlueprintSchema) -> float:
    """Calculate blueprint data completeness"""
    if not blueprint_schema or not blueprint_schema.rooms:
        return 0.0
    
    total_fields = len(blueprint_schema.rooms) * 5  # name, area, floor, windows, orientation
    filled_fields = 0
    
    for room in blueprint_schema.rooms:
        if room.name:
            filled_fields += 1
        if room.area > 0:
            filled_fields += 1
        if room.floor > 0:
            filled_fields += 1
        if room.windows >= 0:
            filled_fields += 1
        if room.orientation:
            filled_fields += 1
    
    return filled_fields / total_fields if total_fields > 0 else 0.0


def _calculate_blueprint_confidence(blueprint_schema: BlueprintSchema) -> float:
    """Calculate confidence in blueprint data accuracy"""
    if not blueprint_schema:
        return 0.0
    
    # Simple heuristic based on data consistency
    confidence = 0.7  # Base confidence
    
    if blueprint_schema.sqft_total > 0:
        room_total = sum(room.area for room in blueprint_schema.rooms)
        if abs(room_total - blueprint_schema.sqft_total) / blueprint_schema.sqft_total < 0.1:
            confidence += 0.2  # Areas match well
    
    if len(blueprint_schema.rooms) >= 3:
        confidence += 0.1  # Reasonable number of rooms
    
    return min(confidence, 1.0)


def _create_compliance_checks(
    audit_id: str,
    blueprint_schema: Optional[BlueprintSchema],
    calculation_result: Dict[str, Any]
) -> List[ComplianceCheck]:
    """Create ACCA Manual J compliance check records"""
    checks = []
    
    if not calculation_result:
        return checks
    
    # Load range check
    heating_total = calculation_result.get('heating_total', 0)
    cooling_total = calculation_result.get('cooling_total', 0)
    total_sqft = blueprint_schema.sqft_total if blueprint_schema else 1000
    
    # Heating load per sqft check
    heating_per_sqft = heating_total / total_sqft if total_sqft > 0 else 0
    checks.append(ComplianceCheck(
        audit_id=audit_id,
        check_category="load_range",
        check_name="heating_load_per_sqft",
        check_description="Heating load should be within typical residential range",
        passed=15 <= heating_per_sqft <= 80,
        check_value=heating_per_sqft,
        expected_range_min=15.0,
        expected_range_max=80.0,
        severity="warning" if not (15 <= heating_per_sqft <= 80) else "info",
        recommendation="Review building envelope and climate data if outside typical range"
    ))
    
    # Cooling load per sqft check
    cooling_per_sqft = cooling_total / total_sqft if total_sqft > 0 else 0
    checks.append(ComplianceCheck(
        audit_id=audit_id,
        check_category="load_range",
        check_name="cooling_load_per_sqft",
        check_description="Cooling load should be within typical residential range",
        passed=10 <= cooling_per_sqft <= 50,
        check_value=cooling_per_sqft,
        expected_range_min=10.0,
        expected_range_max=50.0,
        severity="warning" if not (10 <= cooling_per_sqft <= 50) else "info",
        recommendation="Review building envelope and climate data if outside typical range"
    ))
    
    # Equipment sizing check
    cooling_tons = cooling_total / 12000
    checks.append(ComplianceCheck(
        audit_id=audit_id,
        check_category="equipment_sizing",
        check_name="system_size_reasonable",
        check_description="System size should be reasonable for building",
        passed=1.0 <= cooling_tons <= 10.0,
        check_value=cooling_tons,
        expected_range_min=1.0,
        expected_range_max=10.0,
        severity="error" if not (1.0 <= cooling_tons <= 10.0) else "info",
        recommendation="Verify building area and load calculations if system size is unusual"
    ))
    
    return checks