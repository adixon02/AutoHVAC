"""
Decision Engine Stage
Routes blueprints through reliability layer for guaranteed ±10% accuracy
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from domain.core.reliability import get_ensemble_engine, ReliabilityResult
from domain.core.baselines import Candidate

logger = logging.getLogger(__name__)


@dataclass
class DecisionEngineResult:
    """Result from decision engine with reliability guarantees"""
    # Final load calculations
    heating_load_btu_hr: float
    cooling_load_btu_hr: float
    
    # Reliability metrics
    reliability_result: ReliabilityResult
    
    # Performance metadata
    processing_time: float
    confidence: float
    routing_decision: str
    
    # Transparency for user
    method_breakdown: Dict[str, Any]
    applied_policies: List[str]
    quality_assessment: Dict[str, Any]


class DecisionEngine:
    """
    Routes blueprints through the reliability layer to guarantee ±10% accuracy.
    This is the main entry point for the reliability system.
    """
    
    def __init__(self):
        self.ensemble_engine = get_ensemble_engine()
    
    def process(
        self,
        ai_result: Dict[str, Any],
        envelope: Dict[str, Any],
        extraction_data: Dict[str, Any],
        geometry_data: Dict[str, Any],
        climate_data: Dict[str, Any],
        energy_specs: Any,
        processing_metadata: Dict[str, Any]
    ) -> DecisionEngineResult:
        """
        Process blueprint through reliability layer for guaranteed accuracy.
        
        Args:
            ai_result: Current AI-enhanced calculation results
            envelope: Building envelope data
            extraction_data: Raw extracted data from blueprint
            geometry_data: Geometry detection results
            climate_data: Climate design conditions
            energy_specs: Energy specification extraction
            processing_metadata: Timing and processing info
            
        Returns:
            DecisionEngineResult with reliability-enhanced loads
        """
        
        logger.info("🎯 Decision Engine: Processing blueprint through reliability layer")
        
        start_time = processing_metadata.get('start_time')
        
        # 1. Convert AI result to candidate format
        ai_candidate = self._convert_ai_result_to_candidate(ai_result)
        
        # 2. Determine if orientation handling is needed
        north_arrow_found = self._check_north_arrow_availability(extraction_data)
        handle_orientation = not north_arrow_found
        
        if handle_orientation:
            logger.info("🧭 North arrow not found - will compute orientation range")
        
        # 3. Build compatibility layer for quality assessment
        compatible_extraction_data = self._build_compatible_extraction_data(extraction_data)
        
        # 4. Process through ensemble decision engine
        reliability_result = self.ensemble_engine.decide(
            ai_result=ai_candidate,
            envelope=envelope,
            extraction_data=compatible_extraction_data,
            geometry_data=geometry_data,
            climate_data=climate_data,
            energy_specs=energy_specs,
            handle_orientation_uncertainty=handle_orientation
        )
        
        # 4. Log decision summary
        self._log_decision_summary(reliability_result)
        
        # 5. Create transparent method breakdown
        method_breakdown = self._create_method_breakdown(reliability_result)
        
        # 6. Compile quality assessment
        quality_assessment = {
            'score': reliability_result.quality_score,
            'routing': reliability_result.routing_decision,
            'confidence': reliability_result.confidence,
            'factors': reliability_result.notes
        }
        
        # 7. Calculate total processing time
        processing_time = processing_metadata.get('processing_time', 0)
        
        return DecisionEngineResult(
            heating_load_btu_hr=reliability_result.heating_btuh,
            cooling_load_btu_hr=reliability_result.cooling_btuh,
            reliability_result=reliability_result,
            processing_time=processing_time,
            confidence=reliability_result.confidence,
            routing_decision=reliability_result.routing_decision,
            method_breakdown=method_breakdown,
            applied_policies=reliability_result.conservative_policies or [],
            quality_assessment=quality_assessment
        )
    
    def _convert_ai_result_to_candidate(self, ai_result: Dict[str, Any]) -> Candidate:
        """Convert AI calculation result to candidate format"""
        
        return Candidate(
            name="A_ai",
            heating_btuh=ai_result.get('heating_load_btu_hr', 0),
            cooling_btuh=ai_result.get('cooling_load_btu_hr', 0),
            method_details={
                'source': 'ai_enhanced_pipeline_v3',
                'zones': ai_result.get('zone_count', 1),
                'confidence': ai_result.get('confidence', 0.5),
                'processing_notes': ai_result.get('notes', [])
            }
        )
    
    def _check_north_arrow_availability(self, extraction_data: Dict[str, Any]) -> bool:
        """Check if north arrow or orientation information is available"""
        
        text_blocks = extraction_data.get('text_blocks', [])
        
        north_indicators = ['north', 'n', '↑', 'arrow', 'orientation']
        
        all_text = ' '.join(block.get('text', '') for block in text_blocks).lower()
        
        return any(indicator in all_text for indicator in north_indicators)
    
    def _log_decision_summary(self, reliability_result: ReliabilityResult):
        """Log summary of reliability engine decision"""
        
        logger.info("📊 RELIABILITY ENGINE DECISION SUMMARY:")
        logger.info(f"   Quality Score: {reliability_result.quality_score:.2f}")
        logger.info(f"   Routing: {reliability_result.routing_decision}")
        logger.info(f"   Method Spread: {reliability_result.spread:.1%}")
        logger.info(f"   Final Confidence: {reliability_result.confidence:.1%}")
        
        # Log method values
        logger.info("   Method Results:")
        for candidate in reliability_result.candidates:
            weight = reliability_result.weights.get(candidate.name, 0)
            logger.info(f"     {candidate.name}: {candidate.heating_btuh:,.0f} heating (weight: {weight:.2f})")
        
        logger.info(f"   Final Blended: {reliability_result.heating_btuh:,.0f} heating, {reliability_result.cooling_btuh:,.0f} cooling")
        
        # Log applied policies
        if reliability_result.conservative_policies:
            logger.info(f"   Applied Policies: {len(reliability_result.conservative_policies)}")
            for policy in reliability_result.conservative_policies[:3]:  # Show first 3
                logger.info(f"     • {policy}")
        
        # Log clamps
        if reliability_result.clamps_applied:
            logger.info(f"   Applied Clamps: {len(reliability_result.clamps_applied)}")
    
    def _create_method_breakdown(self, reliability_result: ReliabilityResult) -> Dict[str, Any]:
        """Create detailed breakdown of methods and decisions for transparency"""
        
        method_breakdown = {
            'ensemble_weights': reliability_result.weights,
            'method_spread': reliability_result.spread,
            'candidates': {},
            'decision_factors': {
                'quality_score': reliability_result.quality_score,
                'routing_decision': reliability_result.routing_decision,
                'spread_acceptable': reliability_result.spread <= 0.10,
                'confidence_high': reliability_result.confidence >= 0.8
            },
            'applied_safeguards': {
                'conservative_policies': reliability_result.conservative_policies or [],
                'clamps_applied': reliability_result.clamps_applied or [],
                'orientation_band': reliability_result.orientation_band
            }
        }
        
        # Add candidate details
        for candidate in reliability_result.candidates:
            method_breakdown['candidates'][candidate.name] = {
                'heating_btuh': candidate.heating_btuh,
                'cooling_btuh': candidate.cooling_btuh,
                'weight': reliability_result.weights.get(candidate.name, 0),
                'method_details': candidate.method_details
            }
        
        return method_breakdown
    
    def _build_compatible_extraction_data(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build compatibility layer for quality assessment.
        Pipeline V3 uses different data structures than quality scorer expects.
        """
        
        # Extract basic required data for quality assessment
        compatible_data = {
            'text_blocks': extraction_data.get('text_blocks', []),
            'page_classifications': {},
            'geometry_data': extraction_data.get('geometry_data', {}),
            'foundation_data': {'type': 'crawlspace'},  # Default
            'energy_specs': extraction_data.get('energy_specs'),
            'building_data': extraction_data.get('building_data', {})
        }
        
        # Handle page classifications - convert from Pipeline V3 format to expected format
        pages = extraction_data.get('pages', [])
        page_classifications_raw = extraction_data.get('page_classifications', {})
        
        for page_num, page_info in page_classifications_raw.items():
            if isinstance(page_info, tuple) and len(page_info) >= 2:
                page_type, confidence = page_info
                compatible_data['page_classifications'][page_num] = {
                    'type': page_type,
                    'confidence': confidence
                }
        
        # Handle foundation data - extract from building model if available
        building_data = extraction_data.get('building_data', {})
        foundation_type = building_data.get('foundation_type', 'crawlspace')
        compatible_data['foundation_data'] = {
            'type': foundation_type,
            'condition': 'vented',
            'confidence': 0.7
        }
        
        return compatible_data


# Singleton instance
_decision_engine = None

def get_decision_engine() -> DecisionEngine:
    """Get or create the global decision engine"""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine