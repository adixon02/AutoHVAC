"""
Audit Tracking System for Manual J Calculations
Provides comprehensive audit trails for all calculation inputs and assumptions
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

from app.parser.schema import BlueprintSchema
from .envelope_extractor import EnvelopeExtraction

# Version tracking for calculation changes
CALCULATION_VERSION = "2.0.0"  # Updated for Phase 2 enhancements


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
        return asdict(self)
    
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
            confidence_flags = envelope_data.needs_confirmation
        
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
            blueprint_schema=blueprint_schema.dict(),
            construction_vintage=construction_vintage,
            duct_config=kwargs.get('duct_config', 'ducted_attic'),
            heating_fuel=kwargs.get('heating_fuel', 'gas'),
            include_ventilation=kwargs.get('include_ventilation', True),
            
            # Climate data
            climate_data=climate_data,
            zip_code=blueprint_schema.zip_code,
            climate_zone=climate_data.get('climate_zone'),
            design_temps={
                'heating_db_99': climate_data.get('heating_db_99'),
                'cooling_db_1': climate_data.get('cooling_db_1'),
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
        
        # Check for unrealistic loads
        heating_total = calculation_result.get('heating_total', 0)
        cooling_total = calculation_result.get('cooling_total', 0)
        total_sqft = blueprint_schema.sqft_total
        
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
        room_count = len(blueprint_schema.rooms)
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


def create_calculation_audit(blueprint_schema: BlueprintSchema,
                           calculation_result: Dict[str, Any],
                           climate_data: Dict[str, Any],
                           **kwargs) -> str:
    """
    Convenience function to create and save calculation audit
    
    Returns:
        Calculation ID for future reference
    """
    tracker = get_audit_tracker()
    snapshot = tracker.create_snapshot(
        blueprint_schema=blueprint_schema,
        calculation_result=calculation_result,
        climate_data=climate_data,
        **kwargs
    )
    
    filepath = tracker.save_snapshot(snapshot)
    print(f"Audit snapshot saved: {filepath}")
    
    return snapshot.calculation_id