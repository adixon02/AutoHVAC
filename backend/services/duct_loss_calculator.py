"""
Duct Loss Calculator for Manual J
Calculates supply and return duct losses based on location and insulation
Replaces simplistic fixed percentage with proper modeling
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DuctLocation(Enum):
    """Where ducts are located affects heat loss/gain"""
    CONDITIONED = "conditioned"  # Inside conditioned space (minimal loss)
    ATTIC = "attic"  # Unconditioned attic (high loss)
    CRAWL = "crawl"  # Crawl space (moderate loss)
    BASEMENT = "basement"  # Unconditioned basement (moderate loss)
    GARAGE = "garage"  # Garage (moderate to high loss)
    EXTERIOR = "exterior"  # Outside/roof (highest loss)


class DuctSystem(Enum):
    """Type of duct distribution system"""
    CENTRAL = "central"  # Traditional central trunk and branch
    RADIAL = "radial"  # Home-run radial system
    PERIMETER = "perimeter"  # Perimeter loop (slab)
    HIGH_VELOCITY = "high_velocity"  # Small duct high velocity
    DUCTLESS = "ductless"  # Mini-split, no ducts


@dataclass
class DuctSegment:
    """Individual duct segment with properties"""
    location: DuctLocation
    length_ft: float
    diameter_in: float  # Equivalent diameter for rectangular
    insulation_r: float
    is_supply: bool  # True=supply, False=return
    serves_rooms: List[str]  # Which rooms this segment serves


@dataclass
class DuctLossResult:
    """Duct loss calculation results"""
    # Supply duct losses (BTU/hr)
    supply_loss_heating: float
    supply_loss_cooling: float
    supply_loss_sensible_cooling: float
    supply_loss_latent_cooling: float
    
    # Return duct losses (BTU/hr)
    return_loss_heating: float
    return_loss_cooling: float
    
    # Total system losses
    total_loss_heating: float
    total_loss_cooling: float
    
    # Leakage losses (CFM and BTU/hr)
    supply_leakage_cfm: float
    return_leakage_cfm: float
    leakage_loss_heating: float
    leakage_loss_cooling: float
    
    # Distribution efficiency
    distribution_efficiency_heating: float  # 0-1
    distribution_efficiency_cooling: float  # 0-1
    
    # Per-room distribution of losses
    room_duct_loss_heating: Dict[str, float]
    room_duct_loss_cooling: Dict[str, float]
    
    # Metadata
    duct_location_summary: str
    average_r_value: float
    notes: str


class DuctLossCalculator:
    """
    Calculate duct losses based on ACCA Manual J methodology.
    Considers duct location, insulation, leakage, and design conditions.
    """
    
    # Temperature differentials by location (ΔT from conditioned space)
    # Based on typical unconditioned space temperatures
    LOCATION_DELTA_T = {
        # Winter heating (70°F indoor)
        "heating": {
            DuctLocation.CONDITIONED: 0,  # No loss
            DuctLocation.ATTIC: 50,  # Attic at 20°F
            DuctLocation.CRAWL: 30,  # Crawl at 40°F
            DuctLocation.BASEMENT: 20,  # Basement at 50°F
            DuctLocation.GARAGE: 35,  # Garage at 35°F
            DuctLocation.EXTERIOR: 60,  # Outside at 10°F
        },
        # Summer cooling (75°F indoor)
        "cooling": {
            DuctLocation.CONDITIONED: 0,  # No loss
            DuctLocation.ATTIC: 65,  # Attic at 140°F
            DuctLocation.CRAWL: 15,  # Crawl at 90°F
            DuctLocation.BASEMENT: 5,   # Basement at 80°F
            DuctLocation.GARAGE: 25,  # Garage at 100°F
            DuctLocation.EXTERIOR: 30,  # Outside at 105°F
        }
    }
    
    # Duct leakage rates (% of airflow)
    LEAKAGE_RATES = {
        "sealed_new": 0.03,      # Well-sealed new construction
        "average": 0.10,         # Typical existing
        "poor": 0.20,            # Older unsealed
        "very_poor": 0.30,       # Very leaky old ducts
    }
    
    # Surface area per linear foot by diameter (πD/12 for ft²/ft)
    @staticmethod
    def surface_area_per_ft(diameter_in: float) -> float:
        """Calculate duct surface area per linear foot"""
        return math.pi * diameter_in / 12
    
    def calculate_duct_losses(
        self,
        total_heating_load: float,
        total_cooling_load: float,
        room_cfm: Dict[str, float],
        duct_location: str = "attic",
        duct_r_value: float = 8.0,
        duct_sealing: str = "average",
        climate_zone: str = "4",
        design_temps: Optional[Dict[str, float]] = None,
        duct_segments: Optional[List[DuctSegment]] = None
    ) -> DuctLossResult:
        """
        Calculate duct losses for the system.
        
        Args:
            total_heating_load: Building heating load (BTU/hr)
            total_cooling_load: Building cooling load (BTU/hr) 
            room_cfm: Airflow to each room (CFM)
            duct_location: Primary duct location
            duct_r_value: Duct insulation R-value
            duct_sealing: Sealing quality
            climate_zone: IECC climate zone
            design_temps: Optional specific design temperatures
            duct_segments: Optional detailed duct layout
            
        Returns:
            Comprehensive duct loss results
        """
        logger.info(f"Calculating duct losses - Location: {duct_location}, R-{duct_r_value}")
        
        # Parse duct location
        try:
            location = DuctLocation(duct_location.lower())
        except ValueError:
            location = DuctLocation.ATTIC
            logger.warning(f"Unknown duct location '{duct_location}', using attic")
        
        # Get temperature differentials
        delta_t_heating = self.LOCATION_DELTA_T["heating"][location]
        delta_t_cooling = self.LOCATION_DELTA_T["cooling"][location]
        
        # Adjust for extreme climates
        if climate_zone in ["1", "2"]:  # Hot climates
            delta_t_cooling *= 1.1
        elif climate_zone in ["7", "8"]:  # Cold climates
            delta_t_heating *= 1.1
        
        # Override with specific design temps if provided
        if design_temps:
            outdoor_winter = design_temps.get("outdoor_heating", 10)
            outdoor_summer = design_temps.get("outdoor_cooling", 95)
            indoor = design_temps.get("indoor", 70)
            
            # Recalculate based on actual conditions
            if location == DuctLocation.ATTIC:
                # Attic is hotter in summer, colder in winter
                delta_t_heating = max(70 - outdoor_winter, delta_t_heating)
                delta_t_cooling = max(outdoor_summer + 45 - 75, delta_t_cooling)
        
        # Calculate total CFM
        total_cfm = sum(room_cfm.values())
        
        # If we have detailed segments, use them
        if duct_segments:
            return self._calculate_detailed_losses(
                duct_segments,
                total_heating_load,
                total_cooling_load,
                room_cfm,
                duct_sealing,
                design_temps
            )
        
        # Otherwise use simplified method
        return self._calculate_simplified_losses(
            location,
            duct_r_value,
            delta_t_heating,
            delta_t_cooling,
            total_heating_load,
            total_cooling_load,
            total_cfm,
            room_cfm,
            duct_sealing
        )
    
    def _calculate_simplified_losses(
        self,
        location: DuctLocation,
        r_value: float,
        delta_t_heating: float,
        delta_t_cooling: float,
        total_heating_load: float,
        total_cooling_load: float,
        total_cfm: float,
        room_cfm: Dict[str, float],
        duct_sealing: str
    ) -> DuctLossResult:
        """
        Simplified duct loss calculation when detailed layout unknown.
        Uses typical duct surface area ratios.
        """
        
        # Estimate duct surface area based on building size
        # Typical: 0.15-0.25 sq ft of duct per CFM
        duct_area_sqft = total_cfm * 0.20
        
        # Split between supply (60%) and return (40%)
        supply_area = duct_area_sqft * 0.60
        return_area = duct_area_sqft * 0.40
        
        # Calculate U-factor including air films
        # U = 1 / (R_duct + R_inside_film + R_outside_film)
        r_total = r_value + 0.68 + 0.17  # Add air film resistances
        u_factor = 1.0 / r_total
        
        # Conduction losses: Q = U × A × ΔT
        supply_loss_heating = u_factor * supply_area * delta_t_heating
        supply_loss_cooling = u_factor * supply_area * delta_t_cooling
        return_loss_heating = u_factor * return_area * delta_t_heating
        return_loss_cooling = u_factor * return_area * delta_t_cooling
        
        # Leakage losses
        leakage_rate = self.LEAKAGE_RATES.get(duct_sealing, 0.10)
        supply_leakage_cfm = total_cfm * leakage_rate * 0.6  # 60% on supply side
        return_leakage_cfm = total_cfm * leakage_rate * 0.4  # 40% on return side
        
        # Leakage sensible loss: Q = 1.08 × CFM × ΔT
        leakage_loss_heating = 1.08 * (supply_leakage_cfm + return_leakage_cfm) * delta_t_heating
        leakage_loss_cooling = 1.08 * (supply_leakage_cfm + return_leakage_cfm) * delta_t_cooling
        
        # Latent cooling loss for supply in humid locations
        latent_factor = 0.0
        if location in [DuctLocation.ATTIC, DuctLocation.CRAWL]:
            # Moisture gain in humid spaces
            latent_factor = 0.15  # 15% additional for latent
        
        supply_loss_latent = supply_loss_cooling * latent_factor
        
        # Total losses
        total_loss_heating = (supply_loss_heating + return_loss_heating + 
                             leakage_loss_heating)
        total_loss_cooling = (supply_loss_cooling + return_loss_cooling + 
                             leakage_loss_cooling + supply_loss_latent)
        
        # Distribution efficiency
        dist_eff_heating = 1.0 - (total_loss_heating / max(total_heating_load, 1))
        dist_eff_cooling = 1.0 - (total_loss_cooling / max(total_cooling_load, 1))
        
        # Clamp efficiency between 0.5 and 1.0
        dist_eff_heating = max(0.5, min(1.0, dist_eff_heating))
        dist_eff_cooling = max(0.5, min(1.0, dist_eff_cooling))
        
        # Distribute losses to rooms proportionally by CFM
        room_loss_heating = {}
        room_loss_cooling = {}
        
        for room_name, cfm in room_cfm.items():
            cfm_fraction = cfm / total_cfm if total_cfm > 0 else 0
            room_loss_heating[room_name] = total_loss_heating * cfm_fraction
            room_loss_cooling[room_name] = total_loss_cooling * cfm_fraction
        
        # Generate notes
        notes = self._generate_notes(location, r_value, duct_sealing, dist_eff_heating)
        
        logger.info(f"Duct losses - Heating: {total_loss_heating:.0f} BTU/hr "
                   f"({(1-dist_eff_heating)*100:.1f}%), "
                   f"Cooling: {total_loss_cooling:.0f} BTU/hr "
                   f"({(1-dist_eff_cooling)*100:.1f}%)")
        
        return DuctLossResult(
            supply_loss_heating=supply_loss_heating,
            supply_loss_cooling=supply_loss_cooling,
            supply_loss_sensible_cooling=supply_loss_cooling,
            supply_loss_latent_cooling=supply_loss_latent,
            return_loss_heating=return_loss_heating,
            return_loss_cooling=return_loss_cooling,
            total_loss_heating=total_loss_heating,
            total_loss_cooling=total_loss_cooling,
            supply_leakage_cfm=supply_leakage_cfm,
            return_leakage_cfm=return_leakage_cfm,
            leakage_loss_heating=leakage_loss_heating,
            leakage_loss_cooling=leakage_loss_cooling,
            distribution_efficiency_heating=dist_eff_heating,
            distribution_efficiency_cooling=dist_eff_cooling,
            room_duct_loss_heating=room_loss_heating,
            room_duct_loss_cooling=room_loss_cooling,
            duct_location_summary=location.value,
            average_r_value=r_value,
            notes=notes
        )
    
    def _calculate_detailed_losses(
        self,
        segments: List[DuctSegment],
        total_heating_load: float,
        total_cooling_load: float,
        room_cfm: Dict[str, float],
        duct_sealing: str,
        design_temps: Optional[Dict[str, float]]
    ) -> DuctLossResult:
        """
        Detailed duct loss calculation with specific segment properties.
        More accurate when duct layout is known.
        """
        # Implementation would calculate losses for each segment
        # For now, delegate to simplified method
        
        # Find predominant location and average R-value
        location_counts = {}
        total_r_length = 0
        total_length = 0
        
        for segment in segments:
            location_counts[segment.location] = location_counts.get(segment.location, 0) + segment.length_ft
            total_r_length += segment.insulation_r * segment.length_ft
            total_length += segment.length_ft
        
        # Get most common location
        predominant_location = max(location_counts, key=location_counts.get)
        avg_r = total_r_length / total_length if total_length > 0 else 8.0
        
        logger.info(f"Detailed duct analysis: {len(segments)} segments, "
                   f"avg R-{avg_r:.1f}, mainly in {predominant_location.value}")
        
        # For now, use simplified with averaged values
        return self._calculate_simplified_losses(
            predominant_location,
            avg_r,
            self.LOCATION_DELTA_T["heating"][predominant_location],
            self.LOCATION_DELTA_T["cooling"][predominant_location],
            total_heating_load,
            total_cooling_load,
            sum(room_cfm.values()),
            room_cfm,
            duct_sealing
        )
    
    def _generate_notes(
        self,
        location: DuctLocation,
        r_value: float,
        sealing: str,
        efficiency: float
    ) -> str:
        """Generate descriptive notes about duct system"""
        
        notes = []
        
        # Location assessment
        if location == DuctLocation.CONDITIONED:
            notes.append("Ducts in conditioned space (excellent)")
        elif location == DuctLocation.ATTIC:
            notes.append("Ducts in unconditioned attic (high losses)")
        elif location == DuctLocation.CRAWL:
            notes.append("Ducts in crawl space (moderate losses)")
        
        # Insulation assessment
        if r_value < 4:
            notes.append(f"Poor insulation (R-{r_value})")
        elif r_value < 8:
            notes.append(f"Moderate insulation (R-{r_value})")
        else:
            notes.append(f"Good insulation (R-{r_value})")
        
        # Sealing assessment
        if sealing == "sealed_new":
            notes.append("Well-sealed duct system")
        elif sealing == "poor" or sealing == "very_poor":
            notes.append("Significant duct leakage")
        
        # Efficiency assessment
        if efficiency < 0.70:
            notes.append("Poor distribution efficiency - consider duct improvements")
        elif efficiency < 0.85:
            notes.append("Moderate distribution efficiency")
        else:
            notes.append("Good distribution efficiency")
        
        return "; ".join(notes)
    
    def recommend_improvements(
        self,
        current_result: DuctLossResult,
        location: DuctLocation
    ) -> List[Dict[str, Any]]:
        """
        Recommend duct system improvements based on current losses.
        
        Returns:
            List of recommendations with estimated savings
        """
        recommendations = []
        
        # Check distribution efficiency
        if current_result.distribution_efficiency_heating < 0.80:
            
            # Recommend sealing if leakage is high
            if current_result.supply_leakage_cfm + current_result.return_leakage_cfm > 100:
                recommendations.append({
                    "action": "Seal duct leaks",
                    "description": "Professional duct sealing with mastic or Aeroseal",
                    "estimated_savings": "10-20% reduction in HVAC energy use",
                    "priority": "high"
                })
            
            # Recommend insulation upgrade
            if current_result.average_r_value < 8:
                recommendations.append({
                    "action": "Add duct insulation",
                    "description": f"Upgrade from R-{current_result.average_r_value:.0f} to R-8 minimum",
                    "estimated_savings": "5-15% reduction in HVAC energy use",
                    "priority": "high" if location == DuctLocation.ATTIC else "medium"
                })
            
            # Consider relocation for attic ducts
            if location == DuctLocation.ATTIC:
                recommendations.append({
                    "action": "Consider duct relocation",
                    "description": "Move ducts to conditioned space or encapsulate in attic",
                    "estimated_savings": "15-25% reduction in HVAC energy use",
                    "priority": "medium",
                    "notes": "Most effective but higher cost"
                })
        
        # Check for very poor efficiency
        if current_result.distribution_efficiency_cooling < 0.70:
            recommendations.append({
                "action": "Consider ductless system",
                "description": "Mini-split heat pumps eliminate duct losses entirely",
                "estimated_savings": "20-30% reduction vs current ducted system",
                "priority": "low",
                "notes": "For major renovations or additions"
            })
        
        return recommendations


# Singleton instance
duct_loss_calculator = DuctLossCalculator()