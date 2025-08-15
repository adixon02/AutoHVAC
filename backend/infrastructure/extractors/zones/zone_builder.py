"""
Zone Builder
Groups spaces into thermal zones based on HVAC control and thermal characteristics
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from domain.models.spaces import Space, SpaceType
from domain.models.zones import ThermalZone, ZoneType, BuildingThermalModel

logger = logging.getLogger(__name__)


@dataclass
class ZoneConfiguration:
    """Configuration for zone creation"""
    group_by_floor: bool = True
    separate_bedrooms: bool = False  # Separate sleeping zone?
    separate_bonus: bool = True  # Separate bonus room zone?
    max_spaces_per_zone: int = 10
    min_zone_area_sqft: float = 200


class ZoneBuilder:
    """
    Groups spaces into thermal zones for load calculations.
    A zone is a group of spaces with:
    - Same temperature setpoint
    - Same HVAC equipment serving them
    - Similar occupancy patterns
    """
    
    # Default zone grouping rules
    ZONE_RULES = {
        # Main living spaces typically grouped together
        'main_living': [
            SpaceType.LIVING,
            SpaceType.DINING,
            SpaceType.KITCHEN,
            SpaceType.HALLWAY
        ],
        # Bedrooms can be separate zone for night setback
        'sleeping': [
            SpaceType.BEDROOM,
            SpaceType.BATHROOM  # Usually with bedrooms
        ],
        # Storage/utility often unconditioned or minimal
        'utility': [
            SpaceType.STORAGE,
            SpaceType.MECHANICAL
        ],
        # Garage is always separate (unconditioned)
        'garage': [
            SpaceType.GARAGE
        ]
    }
    
    def build_zones(
        self,
        spaces: List[Space],
        building_info: Dict[str, Any],
        config: Optional[ZoneConfiguration] = None
    ) -> BuildingThermalModel:
        """
        Build thermal zones from detected spaces.
        
        Args:
            spaces: List of detected spaces
            building_info: Building metadata (sqft, floors, etc.)
            config: Zone configuration options
            
        Returns:
            Complete BuildingThermalModel with zones
        """
        if config is None:
            config = ZoneConfiguration()
        
        logger.info(f"Building zones from {len(spaces)} spaces")
        
        # 1. Group spaces by criteria
        zones = []
        
        if config.group_by_floor:
            # Group by floor first
            floors = {}
            for space in spaces:
                floor = space.floor_level
                if floor not in floors:
                    floors[floor] = []
                floors[floor].append(space)
            
            # Create zones for each floor
            for floor_num, floor_spaces in floors.items():
                floor_zones = self._create_floor_zones(
                    floor_spaces,
                    floor_num,
                    config
                )
                zones.extend(floor_zones)
        else:
            # Create zones ignoring floors
            zones = self._create_building_zones(spaces, config)
        
        # 2. Identify special zones
        self._identify_special_zones(zones, building_info)
        
        # 3. Create building model
        model = BuildingThermalModel(
            building_id=building_info.get('project_id', 'unknown'),
            total_conditioned_area_sqft=building_info.get('total_sqft', 0),
            total_floors=building_info.get('floor_count', 1),
            zones=zones,
            foundation_type=building_info.get('foundation_type', 'slab'),
            has_bonus_over_garage=any(z.is_bonus_zone for z in zones),
            has_vaulted_spaces=any(
                s.has_cathedral_ceiling for z in zones for s in z.spaces
            ),
            climate_zone=building_info.get('climate_zone', ''),
            winter_design_temp=building_info.get('winter_design_temp', 0),
            summer_design_temp=building_info.get('summer_design_temp', 95)
        )
        
        # 4. Validate model
        is_valid, issues = model.validate_model()
        if not is_valid:
            logger.warning(f"Zone model has {len(issues)} validation issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        logger.info(f"Created {len(zones)} zones: "
                   f"{len(model.conditioned_zones)} conditioned, "
                   f"{len(model.bonus_zones)} bonus")
        
        return model
    
    def _create_floor_zones(
        self,
        spaces: List[Space],
        floor_num: int,
        config: ZoneConfiguration
    ) -> List[ThermalZone]:
        """Create zones for a single floor"""
        zones = []
        
        # Separate by space type groups
        groups = {
            'main': [],
            'sleeping': [],
            'bonus': [],
            'utility': [],
            'garage': []
        }
        
        for space in spaces:
            # Check for bonus room
            if space.is_bonus_room:
                groups['bonus'].append(space)
            # Check for garage
            elif space.space_type == SpaceType.GARAGE:
                groups['garage'].append(space)
            # Check sleeping spaces
            elif space.space_type in self.ZONE_RULES['sleeping']:
                if config.separate_bedrooms:
                    groups['sleeping'].append(space)
                else:
                    groups['main'].append(space)
            # Check utility
            elif space.space_type in self.ZONE_RULES['utility']:
                groups['utility'].append(space)
            # Everything else is main living
            else:
                groups['main'].append(space)
        
        # Create zones from groups
        if groups['main']:
            zone = ThermalZone(
                zone_id=f"floor_{floor_num}_main",
                name=f"Floor {floor_num} Main Living",
                zone_type=ZoneType.MAIN_LIVING,
                floor_level=floor_num,
                spaces=groups['main'],
                is_conditioned=True,
                heating_setpoint_f=70.0,
                cooling_setpoint_f=75.0,
                occupancy_schedule="residential",
                primary_occupancy=True
            )
            zones.append(zone)
        
        if groups['sleeping'] and config.separate_bedrooms:
            zone = ThermalZone(
                zone_id=f"floor_{floor_num}_sleeping",
                name=f"Floor {floor_num} Bedrooms",
                zone_type=ZoneType.SLEEPING,
                floor_level=floor_num,
                spaces=groups['sleeping'],
                is_conditioned=True,
                heating_setpoint_f=68.0,  # Night setback
                cooling_setpoint_f=76.0,
                occupancy_schedule="sleeping",
                primary_occupancy=True,
                has_separate_control=True
            )
            zones.append(zone)
        
        if groups['bonus']:
            zone = ThermalZone(
                zone_id=f"floor_{floor_num}_bonus",
                name=f"Bonus Room",
                zone_type=ZoneType.BONUS,
                floor_level=floor_num,
                spaces=groups['bonus'],
                is_conditioned=True,
                heating_setpoint_f=70.0,
                cooling_setpoint_f=78.0,  # Less critical cooling
                occupancy_schedule="occasional",
                primary_occupancy=False,  # Not primary for cooling
                is_bonus_zone=True,
                requires_zoning=True  # May need dampers
            )
            zones.append(zone)
        
        if groups['garage']:
            zone = ThermalZone(
                zone_id=f"floor_{floor_num}_garage",
                name=f"Garage",
                zone_type=ZoneType.GARAGE,
                floor_level=floor_num,
                spaces=groups['garage'],
                is_conditioned=False,
                heating_setpoint_f=32.0,  # Freeze protection only
                cooling_setpoint_f=120.0,  # No cooling
                occupancy_schedule="none",
                primary_occupancy=False
            )
            zones.append(zone)
        
        if groups['utility']:
            # Utility spaces - add to main zone if small
            total_utility_area = sum(s.area_sqft for s in groups['utility'])
            if total_utility_area < config.min_zone_area_sqft and groups['main']:
                # Add to main zone
                zones[0].spaces.extend(groups['utility'])
            else:
                # Create separate utility zone (minimal conditioning)
                zone = ThermalZone(
                    zone_id=f"floor_{floor_num}_utility",
                    name=f"Floor {floor_num} Utility",
                    zone_type=ZoneType.MAIN_LIVING,  # Treated as main but minimal
                    floor_level=floor_num,
                    spaces=groups['utility'],
                    is_conditioned=True,
                    heating_setpoint_f=60.0,  # Minimal heating
                    cooling_setpoint_f=85.0,  # Minimal cooling
                    occupancy_schedule="minimal",
                    primary_occupancy=False
                )
                zones.append(zone)
        
        return zones
    
    def _create_building_zones(
        self,
        spaces: List[Space],
        config: ZoneConfiguration
    ) -> List[ThermalZone]:
        """Create zones for entire building (not by floor)"""
        # Simplified implementation - just use floor 1
        return self._create_floor_zones(spaces, 1, config)
    
    def _identify_special_zones(
        self,
        zones: List[ThermalZone],
        building_info: Dict[str, Any]
    ):
        """Identify and mark special zone conditions"""
        
        # Check for bonus over garage
        garage_zones = [z for z in zones if z.zone_type == ZoneType.GARAGE]
        bonus_zones = [z for z in zones if z.is_bonus_zone]
        
        if garage_zones and bonus_zones:
            # Verify bonus is actually over garage (same footprint area)
            garage_area = garage_zones[0].total_area_sqft
            bonus_area = bonus_zones[0].total_area_sqft
            
            if abs(garage_area - bonus_area) / garage_area < 0.2:
                # Areas match within 20%
                logger.info(f"Confirmed bonus room ({bonus_area:.0f} sqft) "
                           f"over garage ({garage_area:.0f} sqft)")
                
                # Update bonus zone spaces
                for space in bonus_zones[0].spaces:
                    space.is_over_garage = True
                    space.floor_over = BoundaryCondition.GARAGE
            else:
                logger.warning(f"Bonus area ({bonus_area:.0f}) doesn't match "
                              f"garage area ({garage_area:.0f})")
        
        # Check for multi-story open spaces
        for zone in zones:
            for space in zone.spaces:
                if space.open_to_below and zone.floor_level > 1:
                    # This affects infiltration and volume calculations
                    zone.has_open_to_below = True
                    logger.info(f"Zone {zone.name} has open-to-below space")


# Singleton instance
_zone_builder = None


def get_zone_builder() -> ZoneBuilder:
    """Get or create the global zone builder"""
    global _zone_builder
    if _zone_builder is None:
        _zone_builder = ZoneBuilder()
    return _zone_builder