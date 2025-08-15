"""
Mechanical Systems Extractor
Identifies HVAC equipment type, duct locations, and system characteristics
Critical for accurate duct loss calculations and equipment sizing
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HVACEquipment:
    """HVAC equipment characteristics"""
    equipment_type: str  # 'furnace', 'heat_pump', 'ac', 'boiler', 'mini_split'
    fuel_type: str  # 'gas', 'electric', 'oil', 'propane'
    efficiency_heating: float  # AFUE for furnace, COP for heat pump
    efficiency_cooling: float  # SEER for AC/heat pump
    capacity_heating_btu: Optional[float]
    capacity_cooling_tons: Optional[float]
    location: str  # 'attic', 'basement', 'garage', 'closet', 'exterior'
    age_years: Optional[int]
    model_number: Optional[str]


@dataclass
class DuctSystem:
    """Duct system characteristics"""
    duct_location: str  # 'attic', 'crawlspace', 'basement', 'conditioned'
    duct_insulation_r: float
    duct_sealing: str  # 'sealed', 'average', 'leaky'
    supply_area_sqft: float
    return_area_sqft: float
    has_zoning: bool
    number_of_zones: int
    duct_material: str  # 'sheet_metal', 'flex', 'ductboard'
    
    
@dataclass
class VentilationSystem:
    """Ventilation system characteristics"""
    ventilation_type: str  # 'natural', 'exhaust', 'supply', 'balanced', 'hrv', 'erv'
    ventilation_rate_cfm: float
    heat_recovery_efficiency: float  # 0 for no recovery, 0.7-0.9 for HRV/ERV
    controls: str  # 'continuous', 'intermittent', 'demand'


@dataclass
class MechanicalData:
    """Complete mechanical system data"""
    heating_equipment: Optional[HVACEquipment]
    cooling_equipment: Optional[HVACEquipment]
    duct_system: Optional[DuctSystem]
    ventilation_system: Optional[VentilationSystem]
    has_ductless: bool
    has_radiant: bool
    has_baseboard: bool
    equipment_age_estimate: str  # 'new', 'recent', 'moderate', 'old'
    confidence: float


class MechanicalExtractor:
    """
    Extracts mechanical system information from blueprints
    Identifies equipment types, locations, and characteristics
    """
    
    # Equipment type patterns
    EQUIPMENT_PATTERNS = {
        'furnace': ['FURNACE', 'FAU', 'FORCED AIR', 'GAS HEAT'],
        'heat_pump': ['HEAT PUMP', 'HP', 'SPLIT SYSTEM', 'PACKAGE UNIT'],
        'ac': ['AIR CONDITIONER', 'A/C', 'AC', 'CONDENSING UNIT', 'CONDENSER'],
        'boiler': ['BOILER', 'HOT WATER', 'HYDRONIC', 'RADIANT'],
        'mini_split': ['MINI SPLIT', 'DUCTLESS', 'VRF', 'VRV', 'MULTI-SPLIT'],
        'electric': ['ELECTRIC HEAT', 'BASEBOARD', 'RESISTANCE']
    }
    
    # Efficiency patterns
    EFFICIENCY_PATTERNS = {
        'afue': r'(\d{2,3})\s*(?:%\s*)?AFUE',  # 95% AFUE
        'seer': r'(\d{1,2}(?:\.\d)?)\s*SEER',  # 16 SEER
        'seer2': r'(\d{1,2}(?:\.\d)?)\s*SEER2',  # 15.2 SEER2
        'hspf': r'(\d{1,2}(?:\.\d)?)\s*HSPF',  # 9.5 HSPF
        'cop': r'COP\s*(?:=|:)?\s*(\d(?:\.\d+)?)',  # COP 3.5
    }
    
    # Duct location indicators
    DUCT_LOCATIONS = {
        'attic': ['ATTIC', 'ABOVE CEILING', 'ROOF SPACE'],
        'crawlspace': ['CRAWL', 'UNDER FLOOR', 'BELOW FLOOR'],
        'basement': ['BASEMENT', 'LOWER LEVEL', 'MECHANICAL ROOM'],
        'conditioned': ['CONDITIONED SPACE', 'DROPPED CEILING', 'SOFFIT'],
        'garage': ['GARAGE', 'UNCONDITIONED']
    }
    
    # ACCA Manual J Table 7 - Duct Loss Factors
    DUCT_LOSS_FACTORS = {
        # (location, insulation_r, sealing): (heating_factor, cooling_factor)
        ('attic', 8, 'sealed'): (1.08, 1.12),
        ('attic', 8, 'average'): (1.12, 1.18),
        ('attic', 8, 'leaky'): (1.20, 1.30),
        ('attic', 4, 'average'): (1.18, 1.25),
        ('crawlspace', 8, 'sealed'): (1.06, 1.08),
        ('crawlspace', 8, 'average'): (1.10, 1.12),
        ('basement', 8, 'average'): (1.05, 1.05),
        ('conditioned', 8, 'sealed'): (1.00, 1.00),  # No loss
        ('garage', 8, 'average'): (1.15, 1.20),
    }
    
    def __init__(self):
        self.default_duct_r = 8  # R-8 is code minimum in many areas
        self.default_sealing = 'average'
        
    def extract(
        self,
        text_blocks: List[Dict[str, Any]],
        vision_data: Optional[Dict] = None
    ) -> MechanicalData:
        """Extract mechanical data - simplified wrapper"""
        return self.extract_mechanical(text_blocks, {}, None, vision_data)
    
    def extract_mechanical(
        self,
        text_blocks: List[Dict[str, Any]],
        vector_data: Dict[str, Any],
        room_data: Optional[Dict] = None,
        vision_results: Optional[Dict] = None
    ) -> MechanicalData:
        """
        Extract mechanical system information
        
        Args:
            text_blocks: Text from all pages
            vector_data: Vector symbols and paths
            room_data: Room information if available
            vision_results: Optional GPT-4V analysis
            
        Returns:
            MechanicalData with system characteristics
        """
        logger.info("Extracting mechanical system information")
        
        # Initialize with defaults
        mechanical_data = MechanicalData(
            heating_equipment=None,
            cooling_equipment=None,
            duct_system=None,
            ventilation_system=None,
            has_ductless=False,
            has_radiant=False,
            has_baseboard=False,
            equipment_age_estimate='unknown',
            confidence=0.5
        )
        
        # 1. Identify equipment types from text
        equipment = self._identify_equipment(text_blocks)
        if equipment:
            mechanical_data.heating_equipment = equipment.get('heating')
            mechanical_data.cooling_equipment = equipment.get('cooling')
            mechanical_data.confidence = 0.7
        
        # 2. Extract duct system information
        duct_system = self._extract_duct_system(text_blocks, vector_data)
        if duct_system:
            mechanical_data.duct_system = duct_system
        
        # 3. Extract ventilation system
        ventilation = self._extract_ventilation(text_blocks)
        if ventilation:
            mechanical_data.ventilation_system = ventilation
        
        # 4. Check for alternative systems
        mechanical_data.has_ductless = self._check_for_ductless(text_blocks)
        mechanical_data.has_radiant = self._check_for_radiant(text_blocks)
        mechanical_data.has_baseboard = self._check_for_baseboard(text_blocks)
        
        # 5. Estimate equipment age
        mechanical_data.equipment_age_estimate = self._estimate_equipment_age(text_blocks)
        
        # 6. Apply vision results if available
        if vision_results and 'mechanical' in vision_results:
            self._apply_vision_results(mechanical_data, vision_results['mechanical'])
            mechanical_data.confidence = 0.95
        
        # Log summary
        logger.info(f"Mechanical extraction complete: "
                   f"Heating={mechanical_data.heating_equipment.equipment_type if mechanical_data.heating_equipment else 'unknown'}, "
                   f"Cooling={mechanical_data.cooling_equipment.equipment_type if mechanical_data.cooling_equipment else 'unknown'}, "
                   f"Ducts={mechanical_data.duct_system.duct_location if mechanical_data.duct_system else 'unknown'}")
        
        return mechanical_data
    
    def _identify_equipment(self, text_blocks: List[Dict]) -> Dict[str, HVACEquipment]:
        """Identify HVAC equipment types from text"""
        equipment = {}
        
        for block in text_blocks:
            text = block['text'].upper()
            
            # Check for equipment types
            for eq_type, patterns in self.EQUIPMENT_PATTERNS.items():
                for pattern in patterns:
                    if pattern in text:
                        # Extract details from surrounding text
                        details = self._extract_equipment_details(text, eq_type)
                        
                        if eq_type in ['furnace', 'heat_pump', 'boiler', 'electric']:
                            equipment['heating'] = HVACEquipment(
                                equipment_type=eq_type,
                                fuel_type=details.get('fuel', 'gas' if eq_type == 'furnace' else 'electric'),
                                efficiency_heating=details.get('efficiency', 0.95 if eq_type == 'furnace' else 3.0),
                                efficiency_cooling=0,
                                capacity_heating_btu=details.get('capacity'),
                                capacity_cooling_tons=None,
                                location=details.get('location', 'garage'),
                                age_years=None,
                                model_number=details.get('model')
                            )
                        
                        if eq_type in ['heat_pump', 'ac', 'mini_split']:
                            equipment['cooling'] = HVACEquipment(
                                equipment_type=eq_type,
                                fuel_type='electric',
                                efficiency_heating=3.0 if eq_type == 'heat_pump' else 0,
                                efficiency_cooling=details.get('seer', 16),
                                capacity_heating_btu=None,
                                capacity_cooling_tons=details.get('tons'),
                                location=details.get('location', 'exterior'),
                                age_years=None,
                                model_number=details.get('model')
                            )
                        
                        logger.debug(f"Found {eq_type} on page {block['page']}")
        
        return equipment
    
    def _extract_equipment_details(self, text: str, equipment_type: str) -> Dict[str, Any]:
        """Extract equipment specifications from text"""
        details = {}
        
        # Extract efficiency ratings
        for eff_type, pattern in self.EFFICIENCY_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                if eff_type == 'afue':
                    details['efficiency'] = value / 100  # Convert to decimal
                elif eff_type in ['seer', 'seer2']:
                    details['seer'] = value
                elif eff_type == 'hspf':
                    details['hspf'] = value
                elif eff_type == 'cop':
                    details['efficiency'] = value
        
        # Extract capacity
        capacity_match = re.search(r'(\d+(?:,\d+)?)\s*(?:BTU|BTUH)', text)
        if capacity_match:
            details['capacity'] = int(capacity_match.group(1).replace(',', ''))
        
        tons_match = re.search(r'(\d(?:\.\d)?)\s*TON', text)
        if tons_match:
            details['tons'] = float(tons_match.group(1))
        
        # Extract fuel type
        if 'GAS' in text or 'NATURAL GAS' in text:
            details['fuel'] = 'gas'
        elif 'PROPANE' in text or 'LP' in text:
            details['fuel'] = 'propane'
        elif 'OIL' in text:
            details['fuel'] = 'oil'
        elif 'ELECTRIC' in text:
            details['fuel'] = 'electric'
        
        # Extract location
        for location, keywords in self.DUCT_LOCATIONS.items():
            for keyword in keywords:
                if keyword in text:
                    details['location'] = location
                    break
        
        return details
    
    def _extract_duct_system(
        self,
        text_blocks: List[Dict],
        vector_data: Dict
    ) -> Optional[DuctSystem]:
        """Extract duct system information"""
        duct_location = 'attic'  # Most common default
        duct_r = self.default_duct_r
        sealing = self.default_sealing
        has_zoning = False
        
        # Look for duct information in text
        for block in text_blocks:
            text = block['text'].upper()
            
            # Duct location
            for location, keywords in self.DUCT_LOCATIONS.items():
                for keyword in keywords:
                    if keyword in text and 'DUCT' in text:
                        duct_location = location
                        logger.debug(f"Found duct location: {location}")
                        break
            
            # Duct insulation
            r_match = re.search(r'R-?(\d+)\s*DUCT', text)
            if r_match:
                duct_r = float(r_match.group(1))
                logger.debug(f"Found duct insulation: R-{duct_r}")
            
            # Duct sealing
            if 'SEALED' in text and 'DUCT' in text:
                sealing = 'sealed'
            elif 'MASTIC' in text or 'TAPE' in text:
                sealing = 'sealed'
            
            # Zoning
            if 'ZONE' in text or 'ZONING' in text:
                has_zoning = True
                # Try to extract number of zones
                zone_match = re.search(r'(\d+)\s*ZONE', text)
                if zone_match:
                    zones = int(zone_match.group(1))
                else:
                    zones = 2  # Default for zoned system
        
        # Estimate duct surface area based on building size
        # Rule of thumb: 0.2-0.3 sqft of duct per sqft of floor area
        floor_area = 2000  # Default, would get from building data
        supply_area = floor_area * 0.15
        return_area = floor_area * 0.10
        
        return DuctSystem(
            duct_location=duct_location,
            duct_insulation_r=duct_r,
            duct_sealing=sealing,
            supply_area_sqft=supply_area,
            return_area_sqft=return_area,
            has_zoning=has_zoning,
            number_of_zones=zones if has_zoning else 1,
            duct_material='flex'  # Most common in residential
        )
    
    def _extract_ventilation(self, text_blocks: List[Dict]) -> Optional[VentilationSystem]:
        """Extract ventilation system information"""
        vent_type = 'natural'  # Default
        cfm = 0
        efficiency = 0
        
        ventilation_keywords = {
            'hrv': ['HRV', 'HEAT RECOVERY VENTILATOR'],
            'erv': ['ERV', 'ENERGY RECOVERY VENTILATOR'],
            'exhaust': ['EXHAUST FAN', 'BATH FAN', 'KITCHEN EXHAUST'],
            'supply': ['SUPPLY VENTILATION', 'FRESH AIR'],
            'balanced': ['BALANCED VENTILATION']
        }
        
        for block in text_blocks:
            text = block['text'].upper()
            
            # Check for ventilation types
            for vent_key, patterns in ventilation_keywords.items():
                for pattern in patterns:
                    if pattern in text:
                        vent_type = vent_key
                        logger.debug(f"Found ventilation type: {vent_key}")
                        
                        # Extract CFM if mentioned
                        cfm_match = re.search(r'(\d+)\s*CFM', text)
                        if cfm_match:
                            cfm = int(cfm_match.group(1))
                        
                        # HRV/ERV efficiency
                        if vent_key in ['hrv', 'erv']:
                            eff_match = re.search(r'(\d{2})\s*%', text)
                            if eff_match:
                                efficiency = int(eff_match.group(1)) / 100
                            else:
                                efficiency = 0.70  # Typical HRV efficiency
        
        # If no mechanical ventilation found, estimate natural infiltration
        if vent_type == 'natural':
            # ASHRAE 62.2: 0.03 CFM/sqft + 7.5 CFM/bedroom
            floor_area = 2000  # Default
            bedrooms = 3  # Default
            cfm = (floor_area * 0.03) + (bedrooms * 7.5)
        
        return VentilationSystem(
            ventilation_type=vent_type,
            ventilation_rate_cfm=cfm,
            heat_recovery_efficiency=efficiency,
            controls='continuous' if vent_type in ['hrv', 'erv'] else 'intermittent'
        )
    
    def _check_for_ductless(self, text_blocks: List[Dict]) -> bool:
        """Check for ductless systems"""
        keywords = ['DUCTLESS', 'MINI SPLIT', 'MINI-SPLIT', 'VRF', 'VRV', 'WALL MOUNT']
        
        for block in text_blocks:
            text = block['text'].upper()
            for keyword in keywords:
                if keyword in text:
                    logger.debug(f"Found ductless system: {keyword}")
                    return True
        
        return False
    
    def _check_for_radiant(self, text_blocks: List[Dict]) -> bool:
        """Check for radiant heating"""
        keywords = ['RADIANT', 'IN-FLOOR', 'FLOOR HEAT', 'HYDRONIC']
        
        for block in text_blocks:
            text = block['text'].upper()
            for keyword in keywords:
                if keyword in text:
                    logger.debug(f"Found radiant heating: {keyword}")
                    return True
        
        return False
    
    def _check_for_baseboard(self, text_blocks: List[Dict]) -> bool:
        """Check for baseboard heating"""
        keywords = ['BASEBOARD', 'ELECTRIC HEAT', 'RESISTANCE HEAT']
        
        for block in text_blocks:
            text = block['text'].upper()
            for keyword in keywords:
                if keyword in text:
                    logger.debug(f"Found baseboard heating: {keyword}")
                    return True
        
        return False
    
    def _estimate_equipment_age(self, text_blocks: List[Dict]) -> str:
        """Estimate equipment age from dates or model numbers"""
        current_year = 2024
        
        for block in text_blocks:
            text = block['text']
            
            # Look for installation year
            year_match = re.search(r'(?:INSTALLED|REPLACED|NEW)\s*(?:IN\s*)?(\d{4})', text)
            if year_match:
                year = int(year_match.group(1))
                age = current_year - year
                
                if age <= 5:
                    return 'new'
                elif age <= 10:
                    return 'recent'
                elif age <= 20:
                    return 'moderate'
                else:
                    return 'old'
        
        # Check for "new construction" or similar
        for block in text_blocks:
            if 'NEW' in block['text'].upper():
                return 'new'
        
        return 'unknown'
    
    def calculate_duct_losses(
        self,
        duct_system: DuctSystem,
        delta_t_heating: float,
        delta_t_cooling: float
    ) -> Tuple[float, float]:
        """
        Calculate duct loss factors per ACCA Manual J
        
        Args:
            duct_system: Duct system characteristics
            delta_t_heating: Heating temperature difference
            delta_t_cooling: Cooling temperature difference
            
        Returns:
            (heating_loss_factor, cooling_loss_factor)
        """
        # Look up factors from table
        key = (duct_system.duct_location, duct_system.duct_insulation_r, duct_system.duct_sealing)
        
        # Find closest match in table
        if key in self.DUCT_LOSS_FACTORS:
            return self.DUCT_LOSS_FACTORS[key]
        
        # Estimate based on location
        location_factors = {
            'attic': (1.15, 1.20),
            'crawlspace': (1.10, 1.10),
            'basement': (1.05, 1.05),
            'garage': (1.12, 1.15),
            'conditioned': (1.00, 1.00)
        }
        
        base_factors = location_factors.get(duct_system.duct_location, (1.10, 1.10))
        
        # Adjust for insulation
        if duct_system.duct_insulation_r < 6:
            heating_adj = 1.05
            cooling_adj = 1.08
        elif duct_system.duct_insulation_r > 10:
            heating_adj = 0.95
            cooling_adj = 0.95
        else:
            heating_adj = 1.0
            cooling_adj = 1.0
        
        # Adjust for sealing
        sealing_adj = {
            'sealed': 0.95,
            'average': 1.0,
            'leaky': 1.10
        }
        
        seal_factor = sealing_adj.get(duct_system.duct_sealing, 1.0)
        
        heating_factor = base_factors[0] * heating_adj * seal_factor
        cooling_factor = base_factors[1] * cooling_adj * seal_factor
        
        logger.debug(f"Duct losses: Location={duct_system.duct_location}, "
                    f"R-{duct_system.duct_insulation_r}, {duct_system.duct_sealing} sealing")
        logger.debug(f"Factors: Heating={heating_factor:.2f}, Cooling={cooling_factor:.2f}")
        
        return heating_factor, cooling_factor
    
    def _apply_vision_results(self, mechanical_data: MechanicalData, vision_results: Dict):
        """Apply GPT-4V vision analysis results"""
        if 'equipment_type' in vision_results:
            # Update equipment based on vision
            pass
        
        if 'duct_location' in vision_results:
            if mechanical_data.duct_system:
                mechanical_data.duct_system.duct_location = vision_results['duct_location']


# Singleton instance
_mechanical_extractor = None


def get_mechanical_extractor() -> MechanicalExtractor:
    """Get or create the global mechanical extractor"""
    global _mechanical_extractor
    if _mechanical_extractor is None:
        _mechanical_extractor = MechanicalExtractor()
    return _mechanical_extractor