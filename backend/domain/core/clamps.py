"""
Conservative Unknowns Policy and Sanity Clamps
Ensures sparse blueprints never default to optimistic assumptions
"""

import logging
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClampResult:
    """Result of applying clamps and conservative policies"""
    value: float
    original_value: float
    clamp_applied: bool
    clamp_type: str
    reason: str


class ConservativeUnknownsPolicy:
    """
    When blueprint information is missing, choose the more heating-penalizing option.
    This prevents undersized HVAC systems due to optimistic defaults.
    """
    
    def __init__(self):
        # Conservative defaults table from the spec
        self.conservative_defaults = {
            'foundation_type': 'crawl_vented',
            'crawl_insulation': {'wall_r': 0, 'floor_r': 19},
            'basement_condition': 'unheated',
            'basement_insulation': {'interior_r': 0},
            'ach50_new': 5.0,
            'ach50_existing': 7.0,
            'shielding_single_story': 'exposed',
            'shielding_multi_story': 'normal',
            'window_u_max_by_zone': {
                '5B': 0.30,  # Code max for climate zone 5B
                '4C': 0.35,
                '6A': 0.27
            },
            'window_shgc_mid': 0.30,
            'wwr_default_per_facade': 0.20,  # 20% if unknown
            'rim_joist_always_include': True
        }
    
    def apply_to_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply conservative unknowns policy to thermal envelope.
        
        Args:
            envelope: Thermal envelope dictionary
            
        Returns:
            Modified envelope with conservative defaults applied
        """
        
        conservative_envelope = envelope.copy()
        applied_policies = []
        
        # 1. Foundation type and insulation
        if not envelope.get('foundation_type') or envelope.get('foundation_confidence', 0) < 0.7:
            conservative_envelope['foundation_type'] = 'crawlspace'
            conservative_envelope['foundation_condition'] = 'vented'
            applied_policies.append("Foundation: Unknown → vented crawlspace")
            
            # Conservative crawl insulation
            if not envelope.get('foundation_wall_r'):
                conservative_envelope['foundation_wall_r'] = 0
                applied_policies.append("Crawl walls: Unknown → R-0")
            
            if not envelope.get('floor_r_value'):
                conservative_envelope['floor_r_value'] = 19
                applied_policies.append("Floor insulation: Unknown → R-19")
        
        # 2. Duct location (critical for single-story heating)
        stories = envelope.get('floor_count', 1)
        if not envelope.get('duct_location'):
            if stories == 1:
                conservative_envelope['duct_location'] = 'vented_attic'
                applied_policies.append("Ducts: Single-story unknown → vented attic")
            else:
                conservative_envelope['duct_location'] = 'basement_crawl'
                applied_policies.append("Ducts: Multi-story unknown → basement/crawl")
        
        # 3. Air leakage
        building_era = envelope.get('building_era', 'existing')
        if not envelope.get('ach50'):
            if building_era == 'new' or (isinstance(building_era, str) and building_era.isdigit() and int(building_era) >= 2000):
                conservative_envelope['ach50'] = self.conservative_defaults['ach50_new']
                applied_policies.append("ACH50: New construction unknown → 5.0")
            else:
                conservative_envelope['ach50'] = self.conservative_defaults['ach50_existing']
                applied_policies.append("ACH50: Existing construction unknown → 7.0")
        
        # 4. Wind shielding
        if not envelope.get('wind_shielding'):
            if stories == 1:
                conservative_envelope['wind_shielding'] = 'exposed'
                applied_policies.append("Shielding: Single-story unknown → exposed")
            else:
                conservative_envelope['wind_shielding'] = 'normal'
                applied_policies.append("Shielding: Multi-story unknown → normal")
        
        # 5. Window properties
        climate_zone = envelope.get('climate_zone', '5B')
        if not envelope.get('window_u_value'):
            max_u = self.conservative_defaults['window_u_max_by_zone'].get(climate_zone, 0.30)
            conservative_envelope['window_u_value'] = max_u
            applied_policies.append(f"Window U: Unknown → {max_u} (code max for {climate_zone})")
        
        if not envelope.get('window_shgc'):
            conservative_envelope['window_shgc'] = self.conservative_defaults['window_shgc_mid']
            applied_policies.append("Window SHGC: Unknown → 0.30 (mid-range)")
        
        # 6. Window-to-wall ratio
        if not envelope.get('window_areas_by_facade'):
            wwr = self.conservative_defaults['wwr_default_per_facade']
            conservative_envelope['wwr_per_facade'] = wwr
            applied_policies.append(f"WWR: Unknown → {wwr*100}% per facade")
        
        # 7. Rim joists (always include as separate high-framing assembly)
        conservative_envelope['include_rim_joists'] = True
        applied_policies.append("Rim joists: Always included as separate assembly")
        
        # Log applied policies
        if applied_policies:
            logger.info(f"Applied {len(applied_policies)} conservative unknown policies:")
            for policy in applied_policies:
                logger.info(f"  • {policy}")
        
        conservative_envelope['conservative_policies_applied'] = applied_policies
        
        return conservative_envelope


class SanityClamps:
    """
    Engineering sanity checks that prevent unrealistic calculation results.
    If any clamp triggers, confidence is reduced and blend weights shift conservative.
    """
    
    def __init__(self):
        self.clamps = {
            'achnat_floor_new': 0.25,  # ACHnat for new construction at 5B design
            'achnat_floor_existing': 0.35,
            'wwr_facade_max': 0.35,  # 35% WWR per facade max without evidence
            'wall_effective_r_max': 18,  # R-20+R5 should not imply effective R > 18
            'single_story_attic_duct_min_intensity': 18,  # BTU/hr·sqft minimum
            'effective_ceiling_height_max': 12,  # Reasonable ceiling height limit
            'infiltration_cfm_max_per_sqft': 0.5  # Maximum reasonable infiltration
        }
    
    def apply_achnat_floor(self, achnat: float, building_era: str) -> ClampResult:
        """Clamp ACH natural to reasonable minimum"""
        if building_era == 'new' or (isinstance(building_era, str) and building_era.isdigit() and int(building_era) >= 2000):
            min_achnat = self.clamps['achnat_floor_new']
        else:
            min_achnat = self.clamps['achnat_floor_existing']
        
        if achnat < min_achnat:
            return ClampResult(
                value=min_achnat,
                original_value=achnat,
                clamp_applied=True,
                clamp_type='achnat_floor',
                reason=f"ACH natural {achnat:.3f} below realistic minimum {min_achnat:.3f}"
            )
        
        return ClampResult(
            value=achnat,
            original_value=achnat,
            clamp_applied=False,
            clamp_type='achnat_floor',
            reason="Within acceptable range"
        )
    
    def apply_wwr_facade_limit(self, wwr: float, has_elevation_evidence: bool = False) -> ClampResult:
        """Clamp window-to-wall ratio to reasonable maximum"""
        max_wwr = self.clamps['wwr_facade_max']
        
        if wwr > max_wwr and not has_elevation_evidence:
            return ClampResult(
                value=max_wwr,
                original_value=wwr,
                clamp_applied=True,
                clamp_type='wwr_facade_max',
                reason=f"WWR {wwr:.1%} exceeds {max_wwr:.1%} without elevation evidence"
            )
        
        return ClampResult(
            value=wwr,
            original_value=wwr,
            clamp_applied=False,
            clamp_type='wwr_facade_max',
            reason="Within acceptable range or has evidence"
        )
    
    def apply_wall_effective_r_limit(self, stated_r: float, continuous_r: float) -> ClampResult:
        """Prevent unrealistic effective R-values from continuous insulation"""
        # R-20 + R-5 continuous should not imply effective R > ~18 due to thermal bridging
        max_effective_r = self.clamps['wall_effective_r_max']
        
        if continuous_r > 0:
            # Simplified effective R calculation accounting for thermal bridging
            effective_r = min(stated_r + continuous_r * 0.8, max_effective_r)
            
            if effective_r < stated_r + continuous_r:
                return ClampResult(
                    value=effective_r,
                    original_value=stated_r + continuous_r,
                    clamp_applied=True,
                    clamp_type='wall_effective_r_max',
                    reason=f"Effective R-value limited to {max_effective_r} due to thermal bridging"
                )
        
        return ClampResult(
            value=stated_r + continuous_r,
            original_value=stated_r + continuous_r,
            clamp_applied=False,
            clamp_type='wall_effective_r_max',
            reason="Within realistic range"
        )
    
    def apply_heating_intensity_floor(
        self, 
        heating_btuh: float, 
        area_sqft: float, 
        stories: int,
        duct_location: str
    ) -> ClampResult:
        """Prevent unrealistically low heating intensities"""
        
        intensity = heating_btuh / area_sqft if area_sqft > 0 else 0
        min_intensity = self.clamps['single_story_attic_duct_min_intensity']
        
        # Apply floor for single-story with attic ducts
        if stories == 1 and 'attic' in duct_location.lower():
            if intensity < min_intensity:
                adjusted_heating = min_intensity * area_sqft
                return ClampResult(
                    value=adjusted_heating,
                    original_value=heating_btuh,
                    clamp_applied=True,
                    clamp_type='heating_intensity_floor',
                    reason=f"Single-story attic ducts: {intensity:.1f} BTU/hr·sqft below minimum {min_intensity}"
                )
        
        return ClampResult(
            value=heating_btuh,
            original_value=heating_btuh,
            clamp_applied=False,
            clamp_type='heating_intensity_floor',
            reason="Within acceptable range"
        )
    
    def apply_infiltration_limit(self, cfm: float, area_sqft: float) -> ClampResult:
        """Prevent unrealistically high infiltration rates"""
        
        cfm_per_sqft = cfm / area_sqft if area_sqft > 0 else 0
        max_cfm_per_sqft = self.clamps['infiltration_cfm_max_per_sqft']
        
        if cfm_per_sqft > max_cfm_per_sqft:
            adjusted_cfm = max_cfm_per_sqft * area_sqft
            return ClampResult(
                value=adjusted_cfm,
                original_value=cfm,
                clamp_applied=True,
                clamp_type='infiltration_cfm_max',
                reason=f"Infiltration {cfm_per_sqft:.3f} CFM/sqft exceeds maximum {max_cfm_per_sqft:.3f}"
            )
        
        return ClampResult(
            value=cfm,
            original_value=cfm,
            clamp_applied=False,
            clamp_type='infiltration_cfm_max',
            reason="Within acceptable range"
        )


def apply_conservative_unknowns(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Apply conservative unknowns policy to thermal envelope"""
    policy = ConservativeUnknownsPolicy()
    return policy.apply_to_envelope(envelope)


def apply_sanity_clamps(
    calculation_results: Dict[str, Any], 
    envelope: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply engineering sanity clamps to calculation results"""
    
    clamps = SanityClamps()
    clamped_results = calculation_results.copy()
    clamps_applied = []
    
    # Apply relevant clamps based on available data
    if 'achnat' in calculation_results:
        clamp_result = clamps.apply_achnat_floor(
            calculation_results['achnat'], 
            envelope.get('building_era', 'existing')
        )
        if clamp_result.clamp_applied:
            clamped_results['achnat'] = clamp_result.value
            clamps_applied.append(clamp_result)
    
    if 'heating_btuh' in calculation_results and 'area_sqft' in envelope:
        clamp_result = clamps.apply_heating_intensity_floor(
            calculation_results['heating_btuh'],
            envelope['area_sqft'],
            envelope.get('floor_count', 1),
            envelope.get('duct_location', '')
        )
        if clamp_result.clamp_applied:
            clamped_results['heating_btuh'] = clamp_result.value
            clamps_applied.append(clamp_result)
    
    # Log applied clamps
    if clamps_applied:
        logger.warning(f"Applied {len(clamps_applied)} sanity clamps:")
        for clamp in clamps_applied:
            logger.warning(f"  • {clamp.clamp_type}: {clamp.reason}")
    
    clamped_results['clamps_applied'] = [
        {
            'type': clamp.clamp_type,
            'reason': clamp.reason,
            'original_value': clamp.original_value,
            'clamped_value': clamp.value
        }
        for clamp in clamps_applied
    ]
    
    return clamped_results


# Singleton instances
_conservative_policy = None
_sanity_clamps = None

def get_conservative_policy() -> ConservativeUnknownsPolicy:
    """Get or create the global conservative unknowns policy"""
    global _conservative_policy
    if _conservative_policy is None:
        _conservative_policy = ConservativeUnknownsPolicy()
    return _conservative_policy

def get_sanity_clamps() -> SanityClamps:
    """Get or create the global sanity clamps"""
    global _sanity_clamps
    if _sanity_clamps is None:
        _sanity_clamps = SanityClamps()
    return _sanity_clamps