"""
Building Envelope Defaults by Climate Zone and Vintage
Based on IECC codes and typical construction practices
Tracks provenance of all values (detected vs defaulted)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Track where envelope data came from"""
    DETECTED = "detected"  # Found in blueprint
    SCHEDULE = "schedule"  # From window/door schedule  
    CODE_DEFAULT = "code_default"  # IECC code minimum
    VINTAGE_DEFAULT = "vintage_default"  # Typical for age
    USER_OVERRIDE = "user_override"  # User provided


@dataclass
class EnvelopeValue:
    """Envelope parameter with provenance"""
    value: float
    source: DataSource
    confidence: float = 1.0
    notes: Optional[str] = None


@dataclass
class WallConstruction:
    """Wall construction details"""
    framing: str  # 2x4, 2x6, etc.
    cavity_r: EnvelopeValue  # Cavity insulation R-value
    continuous_r: EnvelopeValue  # Continuous insulation R-value
    total_r: EnvelopeValue  # Total R-value
    assembly_u: EnvelopeValue  # Assembly U-factor


@dataclass
class WindowSpec:
    """Window thermal specifications"""
    u_factor: EnvelopeValue
    shgc: EnvelopeValue  # Solar Heat Gain Coefficient
    window_type: str  # double_pane, triple_pane, etc.
    frame_type: str  # vinyl, aluminum, wood, fiberglass


@dataclass
class BuildingEnvelope:
    """Complete building envelope with provenance tracking"""
    # Walls
    walls: WallConstruction
    
    # Roof/Ceiling
    ceiling_r: EnvelopeValue
    roof_type: str  # vented_attic, cathedral, flat
    
    # Floor/Foundation
    floor_r: EnvelopeValue
    foundation_type: str  # slab, crawl, basement
    slab_perimeter_r: Optional[EnvelopeValue] = None
    basement_wall_r: Optional[EnvelopeValue] = None
    
    # Windows and Doors
    windows: WindowSpec
    door_u: EnvelopeValue
    
    # Air Infiltration
    air_changes_per_hour: EnvelopeValue  # ACH50
    
    # Thermal Mass
    thermal_mass: str  # light, medium, heavy
    
    # Tracking
    detected_count: int = 0  # How many values were detected
    defaulted_count: int = 0  # How many were defaulted
    confidence: float = 0.0  # Overall confidence


class EnvelopeDefaultProvider:
    """
    Provides building envelope defaults based on climate zone and vintage.
    All values include source tracking for transparency.
    """
    
    # IECC Climate Zone Requirements (2021 IECC)
    IECC_2021 = {
        "1": {  # Very Hot
            "wall_cavity_r": 13,
            "wall_continuous_r": 0,
            "ceiling_r": 30,
            "floor_r": 13,
            "slab_r": 0,
            "basement_wall_r": 0,
            "window_u": 0.50,
            "window_shgc": 0.25,
            "door_u": 0.61
        },
        "2": {  # Hot
            "wall_cavity_r": 13,
            "wall_continuous_r": 0,
            "ceiling_r": 38,
            "floor_r": 13,
            "slab_r": 0,
            "basement_wall_r": 0,
            "window_u": 0.40,
            "window_shgc": 0.25,
            "door_u": 0.61
        },
        "3": {  # Warm
            "wall_cavity_r": 20,
            "wall_continuous_r": 0,
            "ceiling_r": 38,
            "floor_r": 19,
            "slab_r": 0,
            "basement_wall_r": 5,
            "window_u": 0.30,
            "window_shgc": 0.25,
            "door_u": 0.61
        },
        "4": {  # Mixed
            "wall_cavity_r": 20,
            "wall_continuous_r": 0,
            "ceiling_r": 49,
            "floor_r": 19,
            "slab_r": 10,
            "basement_wall_r": 10,
            "window_u": 0.30,
            "window_shgc": 0.40,
            "door_u": 0.61
        },
        "5": {  # Cool
            "wall_cavity_r": 20,
            "wall_continuous_r": 0,
            "ceiling_r": 49,
            "floor_r": 30,
            "slab_r": 10,
            "basement_wall_r": 15,
            "window_u": 0.30,
            "window_shgc": 0.40,
            "door_u": 0.61
        },
        "6": {  # Cold
            "wall_cavity_r": 20,
            "wall_continuous_r": 5,
            "ceiling_r": 49,
            "floor_r": 30,
            "slab_r": 10,
            "basement_wall_r": 15,
            "window_u": 0.30,
            "window_shgc": 0.40,
            "door_u": 0.61
        },
        "7": {  # Very Cold
            "wall_cavity_r": 20,
            "wall_continuous_r": 5,
            "ceiling_r": 60,
            "floor_r": 38,
            "slab_r": 10,
            "basement_wall_r": 15,
            "window_u": 0.30,
            "window_shgc": 0.45,
            "door_u": 0.61
        },
        "8": {  # Subarctic
            "wall_cavity_r": 20,
            "wall_continuous_r": 10,
            "ceiling_r": 60,
            "floor_r": 38,
            "slab_r": 15,
            "basement_wall_r": 19,
            "window_u": 0.30,
            "window_shgc": 0.45,
            "door_u": 0.61
        }
    }
    
    # Vintage-based adjustments (typical existing construction)
    VINTAGE_FACTORS = {
        "pre-1950": {
            "wall_r_factor": 0.3,  # Often no insulation
            "ceiling_r_factor": 0.4,
            "window_u_factor": 3.0,  # Single pane
            "ach50": 15.0  # Very leaky
        },
        "1950-1970": {
            "wall_r_factor": 0.5,  # Some insulation
            "ceiling_r_factor": 0.6,
            "window_u_factor": 2.0,  # Single or poor double
            "ach50": 12.0  # Leaky
        },
        "1970-1990": {
            "wall_r_factor": 0.7,  # R-11 typical
            "ceiling_r_factor": 0.8,
            "window_u_factor": 1.5,  # Early double pane
            "ach50": 9.0  # Moderate
        },
        "1990-2010": {
            "wall_r_factor": 0.85,  # R-13 to R-19
            "ceiling_r_factor": 0.9,
            "window_u_factor": 1.2,  # Standard double pane
            "ach50": 7.0  # Tighter
        },
        "2010-2020": {
            "wall_r_factor": 0.95,  # Close to code
            "ceiling_r_factor": 0.95,
            "window_u_factor": 1.0,  # Low-E double
            "ach50": 5.0  # Energy Star level
        },
        "2020-present": {
            "wall_r_factor": 1.0,  # Meets current code
            "ceiling_r_factor": 1.0,
            "window_u_factor": 1.0,  # Modern Low-E
            "ach50": 3.0  # Very tight
        }
    }
    
    def get_envelope_defaults(
        self,
        climate_zone: str,
        vintage: str,
        foundation_type: str = "slab",
        detected_values: Optional[Dict[str, Any]] = None
    ) -> BuildingEnvelope:
        """
        Get building envelope with defaults and detected values.
        
        Args:
            climate_zone: IECC climate zone (1-8, with optional A/B/C)
            vintage: Building age category
            foundation_type: slab, crawl, or basement
            detected_values: Any values detected from blueprint
            
        Returns:
            Complete BuildingEnvelope with provenance tracking
        """
        # Strip letter from climate zone for lookup
        zone_num = climate_zone[0] if climate_zone else "4"
        if zone_num not in self.IECC_2021:
            zone_num = "4"  # Default to zone 4
            logger.warning(f"Unknown climate zone {climate_zone}, using zone 4 defaults")
        
        iecc = self.IECC_2021[zone_num]
        detected = detected_values or {}
        
        # Get vintage factors
        vintage_factor = self.VINTAGE_FACTORS.get(vintage, self.VINTAGE_FACTORS["1990-2010"])
        
        # Initialize tracking
        detected_count = 0
        defaulted_count = 0
        
        # Walls
        if "wall_r" in detected:
            wall_cavity_r = EnvelopeValue(
                value=detected["wall_r"],
                source=DataSource.DETECTED,
                confidence=0.9
            )
            detected_count += 1
        else:
            wall_cavity_r = EnvelopeValue(
                value=iecc["wall_cavity_r"] * vintage_factor["wall_r_factor"],
                source=DataSource.VINTAGE_DEFAULT,
                confidence=0.7,
                notes=f"Typical for {vintage} in zone {climate_zone}"
            )
            defaulted_count += 1
        
        wall_continuous_r = EnvelopeValue(
            value=iecc.get("wall_continuous_r", 0),
            source=DataSource.CODE_DEFAULT,
            confidence=0.6
        )
        defaulted_count += 1
        
        # Calculate wall assembly U-factor
        total_r = wall_cavity_r.value + wall_continuous_r.value + 1.5  # Add air films
        wall_u = EnvelopeValue(
            value=1.0 / total_r,
            source=DataSource.CODE_DEFAULT,
            confidence=0.7
        )
        
        walls = WallConstruction(
            framing="2x6" if wall_cavity_r.value >= 19 else "2x4",
            cavity_r=wall_cavity_r,
            continuous_r=wall_continuous_r,
            total_r=EnvelopeValue(value=total_r, source=DataSource.CODE_DEFAULT),
            assembly_u=wall_u
        )
        
        # Ceiling
        if "ceiling_r" in detected:
            ceiling_r = EnvelopeValue(
                value=detected["ceiling_r"],
                source=DataSource.DETECTED,
                confidence=0.9
            )
            detected_count += 1
        else:
            ceiling_r = EnvelopeValue(
                value=iecc["ceiling_r"] * vintage_factor["ceiling_r_factor"],
                source=DataSource.VINTAGE_DEFAULT,
                confidence=0.7
            )
            defaulted_count += 1
        
        # Floor
        if "floor_r" in detected:
            floor_r = EnvelopeValue(
                value=detected["floor_r"],
                source=DataSource.DETECTED,
                confidence=0.9
            )
            detected_count += 1
        else:
            floor_r = EnvelopeValue(
                value=iecc["floor_r"],
                source=DataSource.CODE_DEFAULT,
                confidence=0.6
            )
            defaulted_count += 1
        
        # Foundation-specific
        slab_r = None
        basement_r = None
        
        if foundation_type == "slab":
            slab_r = EnvelopeValue(
                value=iecc.get("slab_r", 0),
                source=DataSource.CODE_DEFAULT,
                confidence=0.6
            )
            defaulted_count += 1
        elif foundation_type == "basement":
            basement_r = EnvelopeValue(
                value=iecc.get("basement_wall_r", 10),
                source=DataSource.CODE_DEFAULT,
                confidence=0.6
            )
            defaulted_count += 1
        
        # Windows
        if "window_u" in detected:
            window_u = EnvelopeValue(
                value=detected["window_u"],
                source=DataSource.DETECTED,
                confidence=0.95
            )
            detected_count += 1
        else:
            window_u = EnvelopeValue(
                value=iecc["window_u"] * vintage_factor["window_u_factor"],
                source=DataSource.VINTAGE_DEFAULT,
                confidence=0.6,
                notes=f"Typical for {vintage}"
            )
            defaulted_count += 1
        
        if "window_shgc" in detected:
            window_shgc = EnvelopeValue(
                value=detected["window_shgc"],
                source=DataSource.DETECTED,
                confidence=0.95
            )
            detected_count += 1
        else:
            window_shgc = EnvelopeValue(
                value=iecc["window_shgc"],
                source=DataSource.CODE_DEFAULT,
                confidence=0.5
            )
            defaulted_count += 1
        
        windows = WindowSpec(
            u_factor=window_u,
            shgc=window_shgc,
            window_type=self._get_window_type(window_u.value),
            frame_type="vinyl"  # Most common
        )
        
        # Doors
        door_u = EnvelopeValue(
            value=detected.get("door_u", iecc["door_u"]),
            source=DataSource.DETECTED if "door_u" in detected else DataSource.CODE_DEFAULT,
            confidence=0.7
        )
        if "door_u" in detected:
            detected_count += 1
        else:
            defaulted_count += 1
        
        # Air infiltration
        ach = EnvelopeValue(
            value=vintage_factor["ach50"],
            source=DataSource.VINTAGE_DEFAULT,
            confidence=0.6,
            notes=f"Typical ACH50 for {vintage}"
        )
        defaulted_count += 1
        
        # Calculate overall confidence
        total_values = detected_count + defaulted_count
        confidence = detected_count / total_values if total_values > 0 else 0.0
        
        return BuildingEnvelope(
            walls=walls,
            ceiling_r=ceiling_r,
            roof_type="vented_attic",  # Most common
            floor_r=floor_r,
            foundation_type=foundation_type,
            slab_perimeter_r=slab_r,
            basement_wall_r=basement_r,
            windows=windows,
            door_u=door_u,
            air_changes_per_hour=ach,
            thermal_mass="medium",  # Default
            detected_count=detected_count,
            defaulted_count=defaulted_count,
            confidence=confidence
        )
    
    def _get_window_type(self, u_factor: float) -> str:
        """Determine window type from U-factor"""
        if u_factor > 0.8:
            return "single_pane"
        elif u_factor > 0.5:
            return "double_pane"
        elif u_factor > 0.3:
            return "double_pane_lowe"
        else:
            return "triple_pane_lowe"
    
    def log_envelope_summary(self, envelope: BuildingEnvelope) -> None:
        """Log a summary of the envelope with sources"""
        logger.info("=" * 60)
        logger.info("BUILDING ENVELOPE SUMMARY")
        logger.info(f"Detected values: {envelope.detected_count}")
        logger.info(f"Defaulted values: {envelope.defaulted_count}")
        logger.info(f"Confidence: {envelope.confidence:.0%}")
        logger.info("-" * 60)
        
        logger.info(f"Wall R-value: R-{envelope.walls.cavity_r.value:.1f} "
                   f"({envelope.walls.cavity_r.source.value})")
        logger.info(f"Ceiling R-value: R-{envelope.ceiling_r.value:.1f} "
                   f"({envelope.ceiling_r.source.value})")
        logger.info(f"Floor R-value: R-{envelope.floor_r.value:.1f} "
                   f"({envelope.floor_r.source.value})")
        logger.info(f"Window U-factor: {envelope.windows.u_factor.value:.2f} "
                   f"({envelope.windows.u_factor.source.value})")
        logger.info(f"Window SHGC: {envelope.windows.shgc.value:.2f} "
                   f"({envelope.windows.shgc.source.value})")
        logger.info(f"Air Infiltration: {envelope.air_changes_per_hour.value:.1f} ACH50 "
                   f"({envelope.air_changes_per_hour.source.value})")
        logger.info("=" * 60)


# Singleton instance
envelope_defaults = EnvelopeDefaultProvider()