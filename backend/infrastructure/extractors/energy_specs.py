"""
Energy Specification Extractor
Extracts building performance specifications from blueprint text
Prioritizes actual blueprint specs over hardcoded defaults
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EnergySpecs:
    """Extracted energy performance specifications"""
    # Insulation R-values
    wall_r_value: Optional[float] = None
    roof_r_value: Optional[float] = None  
    floor_r_value: Optional[float] = None
    foundation_r_value: Optional[float] = None
    
    # Window performance
    window_u_value: Optional[float] = None
    window_shgc: Optional[float] = None
    
    # Air leakage
    ach50: Optional[float] = None
    
    # Equipment specs
    heat_pump_hspf: Optional[float] = None
    ac_seer: Optional[float] = None
    heat_recovery_efficiency: Optional[float] = None
    
    # Confidence in extraction
    confidence: float = 0.0
    extraction_source: str = "none"


class EnergySpecExtractor:
    """
    Extracts building energy specifications from blueprint text
    Uses regex patterns to find R-values, U-values, efficiency ratings
    """
    
    def __init__(self):
        # Regex patterns for common energy specifications
        self.patterns = {
            # R-values: "R-38", "R-19", "R 21"
            'r_value': re.compile(r'R[-\s]?(\d+(?:\.\d+)?)', re.IGNORECASE),
            
            # U-values: "U-0.25", "U=0.30", "U 0.35", "fenestration U = 0.25"
            'u_value': re.compile(r'(?:fenestration\s+)?U[-=\s]*(\d\.\d+)', re.IGNORECASE),
            
            # ACH50: "2.0 ACH50", "2.0 air changes per hour", "air leakage to 2.0 air changes", "ACH50=5.0"
            'ach50': re.compile(r'(?:(?:leakage\s+to\s+)?(\d+(?:\.\d+)?)\s*(?:ACH50|air\s+changes.*?(?:hour|50)|cfm.*50))|(?:ACH50[=\s]*(\d+(?:\.\d+)?))', re.IGNORECASE),
            
            # HSPF: "HSPF 8.1", "HSPF of 9.5", "HSPF2 of 8.1"
            'hspf': re.compile(r'HSPF\s*2?\s*(?:of\s*)?(\d+(?:\.\d+)?)', re.IGNORECASE),
            
            # SEER: "SEER 16", "SEER of 14.5"
            'seer': re.compile(r'SEER\s*(?:of\s*)?(\d+(?:\.\d+)?)', re.IGNORECASE),
            
            # SHGC: "SHGC 0.30", "SHGC=0.25"
            'shgc': re.compile(r'SHGC[=\s]*(\d\.\d+)', re.IGNORECASE),
            
            # Heat recovery efficiency: "efficiency of 0.65", "65% efficiency"
            'heat_recovery': re.compile(r'(?:efficiency\s*(?:of\s*)?(\d\.\d+))|(?:(\d+)%\s*efficiency)', re.IGNORECASE)
        }
        
        # Context keywords to associate R-values with components
        self.context_keywords = {
            'wall': ['wall', 'exterior wall', 'stud', 'framing', 'sheathing'],
            'roof': ['roof', 'ceiling', 'attic', 'rafter', 'truss'],
            'floor': ['floor', 'subfloor', 'joist', 'crawl', 'basement'],
            'foundation': ['foundation', 'slab', 'perimeter', 'footing', 'stem wall'],
            'window': ['window', 'fenestration', 'glazing', 'glass']
        }
    
    def extract_energy_specs(self, text_blocks: List[Dict[str, Any]]) -> EnergySpecs:
        """
        Extract energy specifications from all blueprint text
        
        Args:
            text_blocks: List of text blocks from PDF extraction
            
        Returns:
            EnergySpecs with extracted values and confidence
        """
        logger.info("Extracting energy specifications from blueprint text...")
        
        specs = EnergySpecs()
        extraction_count = 0
        
        # Combine all text for pattern matching
        all_text = ""
        text_segments = []
        
        for block in text_blocks:
            text = block.get('text', '').strip()
            if text:
                all_text += f" {text}"
                text_segments.append(text)
        
        logger.info(f"Analyzing {len(text_segments)} text segments for energy specs")
        
        # Extract R-values with context (using conservative selection)
        r_values = self._extract_r_values_with_context(text_segments)
        if r_values:
            specs.wall_r_value = r_values.get('wall')
            specs.roof_r_value = r_values.get('roof') 
            specs.floor_r_value = r_values.get('floor')
            specs.foundation_r_value = r_values.get('foundation')
            extraction_count += len([v for v in r_values.values() if v])
            logger.info(f"Extracted R-values (conservative selection): {r_values}")
        
        # Extract U-values (typically windows)
        u_values = self._extract_values(all_text, 'u_value')
        if u_values:
            # For U-values, HIGHER values = worse performance = more conservative for load calcs
            specs.window_u_value = max(u_values)  # Use most conservative (worst performing)
            extraction_count += 1
            logger.info(f"Extracted window U-value: {specs.window_u_value} (conservative selection from {u_values})")
        
        # Extract SHGC
        shgc_values = self._extract_values(all_text, 'shgc')
        if shgc_values:
            # For SHGC, HIGHER values = more solar gain = more conservative for cooling loads
            specs.window_shgc = max(shgc_values)  # Use most conservative (higher solar gain)
            extraction_count += 1
            logger.info(f"Extracted window SHGC: {specs.window_shgc} (conservative selection from {shgc_values})")
        
        # Extract ACH50
        ach50_values = self._extract_ach50(all_text)
        if ach50_values:
            # For ACH50, HIGHER values = leakier building = more conservative for load calcs
            specs.ach50 = max(ach50_values)  # Use leakiest/most conservative value
            extraction_count += 1
            logger.info(f"Extracted ACH50: {specs.ach50} (conservative selection from {ach50_values})")
        
        # Extract equipment specifications
        hspf_values = self._extract_values(all_text, 'hspf')
        if hspf_values:
            specs.heat_pump_hspf = max(hspf_values)  # Use highest efficiency
            extraction_count += 1
            logger.info(f"Extracted HSPF: {specs.heat_pump_hspf}")
        
        seer_values = self._extract_values(all_text, 'seer')
        if seer_values:
            specs.ac_seer = max(seer_values)  # Use highest efficiency
            extraction_count += 1
            logger.info(f"Extracted SEER: {specs.ac_seer}")
        
        # Extract heat recovery efficiency
        hr_values = self._extract_heat_recovery_efficiency(all_text)
        if hr_values:
            specs.heat_recovery_efficiency = max(hr_values)
            extraction_count += 1
            logger.info(f"Extracted heat recovery efficiency: {specs.heat_recovery_efficiency}")
        
        # Calculate confidence based on extraction success
        max_possible_extractions = 10  # Total spec types we try to extract
        specs.confidence = min(1.0, extraction_count / max_possible_extractions)
        
        if extraction_count > 0:
            specs.extraction_source = "blueprint_text"
            logger.info(f"Energy spec extraction complete: {extraction_count} values found, confidence {specs.confidence:.1%}")
        else:
            specs.extraction_source = "none"
            logger.warning("No energy specifications found in blueprint text")
        
        return specs
    
    def _extract_r_values_with_context(self, text_segments: List[str]) -> Dict[str, Optional[float]]:
        """Extract R-values and associate with building components based on context"""
        results = {'wall': None, 'roof': None, 'floor': None, 'foundation': None}
        
        for text in text_segments:
            r_matches = self.patterns['r_value'].findall(text)
            if not r_matches:
                continue
            
            text_lower = text.lower()
            
            # Convert all R-values in this text segment
            segment_r_values = []
            for r_value_str in r_matches:
                r_value = float(r_value_str)
                # Skip unreasonably low or high R-values
                if r_value >= 5 and r_value <= 100:
                    segment_r_values.append(r_value)
            
            if not segment_r_values:
                continue
                
            # Apply conservative selection WITHIN this text segment
            if len(segment_r_values) > 1:
                # Multiple R-values in same text - apply conservative logic
                chosen_r_value = self._choose_conservative_r_value_in_segment(text_lower, segment_r_values)
                logger.info(f"Found multiple R-values {segment_r_values} in '{text[:50]}...', chose R-{chosen_r_value}")
            else:
                chosen_r_value = segment_r_values[0]
            
            # Determine context and assign to component
            component = self._determine_r_value_context(text_lower, chosen_r_value)
            
            if component:
                if not results[component] or chosen_r_value > results[component]:
                    if results[component]:
                        logger.info(f"Updated {component} R-value from R-{results[component]} to R-{chosen_r_value}")
                    results[component] = chosen_r_value
                    logger.debug(f"Found {component} R-{chosen_r_value} in: {text[:100]}...")
        
        return results
    
    def _determine_r_value_context(self, text_lower: str, r_value: float) -> Optional[str]:
        """Determine which building component an R-value refers to"""
        
        # Check for explicit context keywords
        for component, keywords in self.context_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return component
        
        # Use R-value range heuristics if no explicit context
        if 30 <= r_value <= 60:
            return 'roof'  # Typical attic insulation
        elif 15 <= r_value <= 40:
            return 'floor'  # Floor insulation range
        elif 10 <= r_value <= 25:
            return 'wall'  # Wall insulation range
        elif 5 <= r_value <= 15:
            return 'foundation'  # Foundation insulation range
        
        return None
    
    def _choose_conservative_r_value_in_segment(self, text_lower: str, r_values: List[float]) -> float:
        """Choose the most conservative/practical R-value from multiple options"""
        if len(r_values) <= 1:
            return r_values[0] if r_values else 0
        
        # Look for construction method indicators for ceiling/roof
        if 'ceiling' in text_lower or 'roof' in text_lower or 'attic' in text_lower:
            # Look for construction method indicators
            if 'energy heel' in text_lower or 'w/ energy heel' in text_lower:
                # When energy heel is mentioned, it usually indicates the lower R-value is standard
                conservative_r = min(r_values)
                logger.info(f"Found 'energy heel' construction - choosing conservative R-{conservative_r} over max R-{max(r_values)}")
                return conservative_r
            elif 'or' in text_lower:
                # "R-60 or R-49" - choose the more practical/conservative option
                conservative_r = min(r_values)
                logger.info(f"Found multiple ceiling options - choosing conservative R-{conservative_r} over max R-{max(r_values)}")
                return conservative_r
        
        # For walls - be conservative but rational
        if 'wall' in text_lower:
            if 'continuous' in text_lower and len(r_values) >= 2:
                # R-20+R5 continuous: use the base wall R-value (R-20)
                # The +R5 is continuous insulation that's often not perfectly installed
                reasonable_values = [r for r in r_values if r >= 15]
                return max(reasonable_values) if reasonable_values else max(r_values)
        
        # Default: take minimum for conservative approach (but not unreasonably low)
        reasonable_values = [r for r in r_values if r >= 15]
        if reasonable_values:
            return min(reasonable_values)
        
        return min(r_values)
    
    def _extract_values(self, text: str, pattern_name: str) -> List[float]:
        """Extract numeric values using specified pattern"""
        matches = self.patterns[pattern_name].findall(text)
        values = []
        
        for match in matches:
            try:
                # Handle tuple matches (multiple groups)
                if isinstance(match, tuple):
                    for group in match:
                        if group:
                            values.append(float(group))
                else:
                    values.append(float(match))
            except ValueError:
                continue
        
        return values
    
    def _extract_ach50(self, text: str) -> List[float]:
        """Extract ACH50 values with special handling for different formats"""
        matches = self.patterns['ach50'].findall(text)
        values = []
        
        for match in matches:
            try:
                # Handle tuple matches
                if isinstance(match, tuple):
                    for group in match:
                        if group:
                            value = float(group)
                            # Only accept reasonable ACH50 values
                            if 0.5 <= value <= 15:
                                values.append(value)
                else:
                    value = float(match)
                    if 0.5 <= value <= 15:
                        values.append(value)
            except ValueError:
                continue
        
        return values
    
    def _extract_heat_recovery_efficiency(self, text: str) -> List[float]:
        """Extract heat recovery efficiency values"""
        matches = self.patterns['heat_recovery'].findall(text)
        values = []
        
        for match in matches:
            try:
                if isinstance(match, tuple):
                    for group in match:
                        if group:
                            value = float(group)
                            # Convert percentage to decimal if needed
                            if value > 1:
                                value = value / 100
                            if 0.3 <= value <= 1.0:  # Reasonable efficiency range
                                values.append(value)
                else:
                    value = float(match)
                    if value > 1:
                        value = value / 100
                    if 0.3 <= value <= 1.0:
                        values.append(value)
            except ValueError:
                continue
        
        return values
    
    def get_defaults_for_era(self, building_era: Optional[str] = None) -> EnergySpecs:
        """Get appropriate default values based on building era"""
        
        # Modern high-efficiency defaults (2020+)
        if building_era and (building_era == 'new' or 
                           (isinstance(building_era, str) and building_era.isdigit() and int(building_era) >= 2020)):
            return EnergySpecs(
                wall_r_value=21.0,
                roof_r_value=49.0,
                floor_r_value=30.0,
                foundation_r_value=10.0,
                window_u_value=0.27,
                window_shgc=0.25,
                ach50=3.0,
                heat_pump_hspf=8.5,
                ac_seer=16.0,
                confidence=0.0,
                extraction_source="era_defaults"
            )
        
        # Standard modern defaults (2000-2019)
        elif building_era and isinstance(building_era, str) and building_era.isdigit() and int(building_era) >= 2000:
            return EnergySpecs(
                wall_r_value=19.0,
                roof_r_value=38.0,
                floor_r_value=19.0,
                foundation_r_value=5.0,
                window_u_value=0.35,
                window_shgc=0.30,
                ach50=5.0,
                heat_pump_hspf=7.5,
                ac_seer=14.0,
                confidence=0.0,
                extraction_source="era_defaults"
            )
        
        # Legacy defaults (pre-2000)
        else:
            return EnergySpecs(
                wall_r_value=13.0,
                roof_r_value=30.0,
                floor_r_value=11.0,
                foundation_r_value=0.0,
                window_u_value=0.50,
                window_shgc=0.40,
                ach50=8.0,
                heat_pump_hspf=6.8,
                ac_seer=10.0,
                confidence=0.0,
                extraction_source="era_defaults"
            )


# Singleton instance
_energy_spec_extractor = None


def get_energy_spec_extractor() -> EnergySpecExtractor:
    """Get or create the global energy spec extractor"""
    global _energy_spec_extractor
    if _energy_spec_extractor is None:
        _energy_spec_extractor = EnergySpecExtractor()
    return _energy_spec_extractor