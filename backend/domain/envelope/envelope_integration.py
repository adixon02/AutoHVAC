"""
Building Envelope Integration System

Integrates intelligent envelope extraction with Manual J calculations,
providing automatic R-value detection and thermal modeling for accurate
HVAC load calculations.

This system bridges the gap between blueprint text extraction and 
thermal modeling, ensuring extracted envelope characteristics are
properly applied to load calculations.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .envelope_intelligence import (
    EnvelopeIntelligenceExtractor,
    BuildingEnvelopeProfile,
    ConstructionQuality
)
from domain.core.climate_zones import get_zone_config, get_construction_factors

logger = logging.getLogger(__name__)

@dataclass
class EnvelopeOverrides:
    """User or AI-extracted envelope overrides for Manual J calculations"""
    wall_r_value: Optional[float] = None
    roof_r_value: Optional[float] = None 
    floor_r_value: Optional[float] = None
    window_u_factor: Optional[float] = None
    window_shgc: Optional[float] = None
    infiltration_ach: Optional[float] = None
    construction_quality: Optional[str] = None  # "tight", "average", "loose"
    confidence_score: float = 0.0
    extraction_notes: list = None

class EnvelopeIntegrationSystem:
    """
    Integrates building envelope intelligence with Manual J thermal modeling.
    
    Responsibilities:
    1. Extract envelope characteristics from blueprint text
    2. Validate extracted values against climate zone requirements
    3. Apply confidence-weighted overrides to thermal calculations
    4. Fallback to climate zone defaults when extraction confidence is low
    """
    
    def __init__(self):
        self.extractor = EnvelopeIntelligenceExtractor()
    
    def analyze_building_envelope(
        self,
        blueprint_text: str,
        building_data: Dict[str, Any],
        climate_zone: str,
        user_inputs: Dict[str, Any] = None
    ) -> Tuple[EnvelopeOverrides, BuildingEnvelopeProfile]:
        """
        Analyze building envelope and generate thermal modeling overrides.
        
        Args:
            blueprint_text: OCR extracted text from blueprint
            building_data: Building characteristics (sqft, stories, etc.)
            climate_zone: IECC climate zone (e.g., "5B")
            user_inputs: Optional user-provided envelope inputs
            
        Returns:
            Tuple of (EnvelopeOverrides, BuildingEnvelopeProfile)
        """
        logger.info(f"Analyzing building envelope for climate zone {climate_zone}")
        
        # 1. Extract envelope characteristics from blueprint
        envelope_profile = self.extractor.extract_envelope_from_text(
            blueprint_text, building_data, climate_zone
        )
        
        logger.info(f"Envelope extraction confidence: {envelope_profile.overall_confidence:.2f}")
        
        # 2. Get climate zone baseline for validation
        zone_config = get_zone_config(climate_zone)
        
        # 3. Create envelope overrides with confidence weighting
        overrides = self._create_envelope_overrides(
            envelope_profile, zone_config, user_inputs
        )
        
        # 4. Validate overrides against building codes and physics
        self._validate_envelope_overrides(overrides, zone_config, climate_zone)
        
        logger.info(f"Generated envelope overrides with {overrides.confidence_score:.2f} confidence")
        
        return overrides, envelope_profile
    
    def _create_envelope_overrides(
        self,
        envelope_profile: BuildingEnvelopeProfile,
        zone_config: Dict[str, Any],
        user_inputs: Dict[str, Any] = None
    ) -> EnvelopeOverrides:
        """Create envelope overrides with confidence weighting"""
        
        # Start with climate zone defaults
        base_factors = get_construction_factors(
            zone_config, 
            construction_quality="average"  # Default quality
        )
        
        # Apply intelligent overrides based on extraction confidence
        confidence_threshold = 0.6  # Minimum confidence to override defaults
        
        # Wall R-value override
        wall_r = None
        if (envelope_profile.effective_wall_r > 0 and 
            envelope_profile.overall_confidence >= confidence_threshold):
            wall_r = envelope_profile.effective_wall_r
        
        # Roof R-value override  
        roof_r = None
        if (envelope_profile.effective_roof_r > 0 and
            envelope_profile.overall_confidence >= confidence_threshold):
            roof_r = envelope_profile.effective_roof_r
        
        # Floor R-value override
        floor_r = None
        if (envelope_profile.effective_floor_r > 0 and
            envelope_profile.overall_confidence >= confidence_threshold):
            floor_r = envelope_profile.effective_floor_r
        
        # Window U-factor override
        window_u = None
        if (envelope_profile.effective_window_u > 0 and
            envelope_profile.overall_confidence >= confidence_threshold):
            window_u = envelope_profile.effective_window_u
        
        # Construction quality and infiltration
        construction_quality = envelope_profile.construction_quality.value
        infiltration_ach = envelope_profile.infiltration_ach
        
        # User input overrides (highest priority)
        if user_inputs:
            if user_inputs.get('wall_r_value'):
                wall_r = float(user_inputs['wall_r_value'])
            if user_inputs.get('roof_r_value'):
                roof_r = float(user_inputs['roof_r_value'])
            if user_inputs.get('floor_r_value'):
                floor_r = float(user_inputs['floor_r_value'])
            if user_inputs.get('window_u_factor'):
                window_u = float(user_inputs['window_u_factor'])
            if user_inputs.get('construction_quality'):
                construction_quality = user_inputs['construction_quality']
        
        return EnvelopeOverrides(
            wall_r_value=wall_r,
            roof_r_value=roof_r,
            floor_r_value=floor_r,
            window_u_factor=window_u,
            window_shgc=0.30,  # Default SHGC
            infiltration_ach=infiltration_ach,
            construction_quality=construction_quality,
            confidence_score=envelope_profile.overall_confidence,
            extraction_notes=envelope_profile.extraction_notes
        )
    
    def _validate_envelope_overrides(
        self,
        overrides: EnvelopeOverrides,
        zone_config: Dict[str, Any],
        climate_zone: str
    ) -> None:
        """Validate envelope overrides against building codes and physics"""
        
        # Validate wall R-value
        if overrides.wall_r_value:
            min_wall_r = max(zone_config['typical_wall_r'] * 0.5, 8)
            max_wall_r = zone_config['typical_wall_r'] * 2.0
            
            if overrides.wall_r_value < min_wall_r:
                logger.warning(f"Wall R-{overrides.wall_r_value:.1f} below minimum R-{min_wall_r:.1f} for zone {climate_zone}")
                overrides.wall_r_value = min_wall_r
            elif overrides.wall_r_value > max_wall_r:
                logger.warning(f"Wall R-{overrides.wall_r_value:.1f} above typical maximum R-{max_wall_r:.1f}")
        
        # Validate roof R-value
        if overrides.roof_r_value:
            min_roof_r = max(zone_config['typical_roof_r'] * 0.6, 15)
            max_roof_r = zone_config['typical_roof_r'] * 2.5
            
            if overrides.roof_r_value < min_roof_r:
                logger.warning(f"Roof R-{overrides.roof_r_value:.1f} below minimum R-{min_roof_r:.1f}")
                overrides.roof_r_value = min_roof_r
            elif overrides.roof_r_value > max_roof_r:
                logger.warning(f"Roof R-{overrides.roof_r_value:.1f} above typical maximum R-{max_roof_r:.1f}")
        
        # Validate window U-factor
        if overrides.window_u_factor:
            min_u = 0.15  # Triple-pane high-performance
            max_u = 1.2   # Single-pane aluminum
            
            if overrides.window_u_factor < min_u:
                logger.warning(f"Window U-{overrides.window_u_factor:.2f} below typical minimum U-{min_u}")
                overrides.window_u_factor = min_u
            elif overrides.window_u_factor > max_u:
                logger.warning(f"Window U-{overrides.window_u_factor:.2f} above typical maximum U-{max_u}")
                overrides.window_u_factor = max_u
        
        # Validate infiltration rate
        if overrides.infiltration_ach:
            min_ach = 0.05  # Super-tight construction
            max_ach = 0.8   # Very leaky construction
            
            if overrides.infiltration_ach < min_ach:
                logger.warning(f"Infiltration {overrides.infiltration_ach:.3f} ACH below practical minimum")
                overrides.infiltration_ach = min_ach
            elif overrides.infiltration_ach > max_ach:
                logger.warning(f"Infiltration {overrides.infiltration_ach:.3f} ACH above typical maximum")
                overrides.infiltration_ach = max_ach
    
    def apply_envelope_overrides_to_factors(
        self,
        base_factors: Dict[str, Any],
        overrides: EnvelopeOverrides,
        climate_zone: str
    ) -> Dict[str, Any]:
        """
        Apply envelope overrides to thermal calculation factors.
        
        Args:
            base_factors: Base thermal factors from climate zone
            overrides: Extracted envelope overrides
            climate_zone: IECC climate zone
            
        Returns:
            Updated thermal factors with envelope intelligence applied
        """
        updated_factors = base_factors.copy()
        
        # Apply R-value overrides
        if overrides.wall_r_value:
            updated_factors['wall_r'] = overrides.wall_r_value
            logger.info(f"Applied wall R-value override: R-{overrides.wall_r_value:.1f}")
        
        if overrides.roof_r_value:
            updated_factors['roof_r'] = overrides.roof_r_value  
            logger.info(f"Applied roof R-value override: R-{overrides.roof_r_value:.1f}")
        
        if overrides.floor_r_value:
            updated_factors['floor_r'] = overrides.floor_r_value
            logger.info(f"Applied floor R-value override: R-{overrides.floor_r_value:.1f}")
        
        # Apply window performance overrides
        if overrides.window_u_factor:
            updated_factors['window_u'] = overrides.window_u_factor
            logger.info(f"Applied window U-factor override: U-{overrides.window_u_factor:.2f}")
        
        if overrides.window_shgc:
            updated_factors['window_shgc'] = overrides.window_shgc
        
        # Apply infiltration override
        if overrides.infiltration_ach:
            updated_factors['infiltration_ach'] = overrides.infiltration_ach
            logger.info(f"Applied infiltration override: {overrides.infiltration_ach:.3f} ACH")
        
        # Add envelope intelligence metadata
        updated_factors['envelope_confidence'] = overrides.confidence_score
        updated_factors['envelope_source'] = 'intelligent_extraction' if overrides.confidence_score > 0.6 else 'climate_zone_default'
        
        return updated_factors
    
    def generate_envelope_report(
        self,
        envelope_profile: BuildingEnvelopeProfile,
        overrides: EnvelopeOverrides,
        climate_zone: str
    ) -> Dict[str, Any]:
        """Generate detailed envelope analysis report"""
        
        zone_config = get_zone_config(climate_zone)
        
        return {
            'analysis_summary': {
                'overall_confidence': envelope_profile.overall_confidence,
                'construction_quality': envelope_profile.construction_quality.value,
                'extraction_method': 'intelligent_blueprint_analysis'
            },
            'thermal_properties': {
                'wall_r_value': overrides.wall_r_value or zone_config['typical_wall_r'],
                'roof_r_value': overrides.roof_r_value or zone_config['typical_roof_r'],
                'floor_r_value': overrides.floor_r_value or zone_config['typical_floor_r'],
                'window_u_factor': overrides.window_u_factor or zone_config['typical_window_u'],
                'infiltration_ach': overrides.infiltration_ach or zone_config['typical_infiltration_ach']
            },
            'extracted_components': {
                'walls': len(envelope_profile.wall_characteristics),
                'roof': len(envelope_profile.roof_characteristics),
                'floors': len(envelope_profile.floor_characteristics),
                'windows': len(envelope_profile.window_performance)
            },
            'extraction_notes': envelope_profile.extraction_notes,
            'climate_zone_baseline': {
                'zone': climate_zone,
                'typical_wall_r': zone_config['typical_wall_r'],
                'typical_roof_r': zone_config['typical_roof_r'],
                'typical_floor_r': zone_config['typical_floor_r'],
                'typical_window_u': zone_config['typical_window_u']
            }
        }


def analyze_blueprint_envelope(
    blueprint_text: str,
    building_data: Dict[str, Any],
    climate_zone: str,
    user_inputs: Dict[str, Any] = None
) -> Tuple[EnvelopeOverrides, Dict[str, Any]]:
    """
    Convenience function for blueprint envelope analysis.
    
    Args:
        blueprint_text: OCR extracted text from blueprint
        building_data: Building characteristics
        climate_zone: IECC climate zone
        user_inputs: Optional user envelope inputs
        
    Returns:
        Tuple of (EnvelopeOverrides, envelope_report)
    """
    integration_system = EnvelopeIntegrationSystem()
    
    # Analyze envelope
    overrides, envelope_profile = integration_system.analyze_building_envelope(
        blueprint_text, building_data, climate_zone, user_inputs
    )
    
    # Generate report
    report = integration_system.generate_envelope_report(
        envelope_profile, overrides, climate_zone
    )
    
    return overrides, report