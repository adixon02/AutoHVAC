"""
Confidence Scoring and Uncertainty Bands for HVAC Load Calculations
Tracks data quality and provides uncertainty ranges for load estimates
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class DataQuality(Enum):
    """Quality levels for input data"""
    MEASURED = "measured"  # Direct measurement (highest confidence)
    DETECTED = "detected"  # Detected from blueprint
    INFERRED = "inferred"  # Inferred from context
    DEFAULT = "default"  # Using defaults (lowest confidence)


class UncertaintySource(Enum):
    """Sources of uncertainty in calculations"""
    SCALE_DETECTION = "scale_detection"
    ROOM_DETECTION = "room_detection"
    ENVELOPE_VALUES = "envelope_values"
    INFILTRATION = "infiltration"
    INTERNAL_GAINS = "internal_gains"
    DUCT_LOSSES = "duct_losses"
    CLIMATE_DATA = "climate_data"
    OCCUPANCY = "occupancy"


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown by component"""
    overall: float  # 0-1 overall confidence
    components: Dict[str, float]  # Component-wise scores
    data_quality: Dict[str, DataQuality]  # Quality of each input
    uncertainty_factors: List[str]  # What's driving uncertainty
    notes: str


@dataclass
class UncertaintyBand:
    """Uncertainty range for a calculated value"""
    nominal: float  # Best estimate
    lower_bound: float  # Conservative lower bound
    upper_bound: float  # Conservative upper bound
    confidence_level: float  # Confidence level (e.g., 0.90 for 90%)
    distribution: str  # normal, uniform, etc.
    
    @property
    def range_percent(self) -> float:
        """Uncertainty as % of nominal"""
        if self.nominal == 0:
            return 0
        return ((self.upper_bound - self.lower_bound) / self.nominal) * 100
    
    def contains(self, value: float) -> bool:
        """Check if value is within uncertainty band"""
        return self.lower_bound <= value <= self.upper_bound


@dataclass
class LoadCalculationConfidence:
    """Complete confidence assessment for load calculation"""
    # Confidence scores
    geometry_confidence: ConfidenceScore
    envelope_confidence: ConfidenceScore
    infiltration_confidence: ConfidenceScore
    loads_confidence: ConfidenceScore
    
    # Overall assessment
    overall_confidence: float  # 0-1
    overall_quality: str  # high, medium, low
    
    # Load uncertainty bands
    heating_load_band: UncertaintyBand
    cooling_load_band: UncertaintyBand
    
    # Equipment sizing with safety factors
    heating_size_recommended: UncertaintyBand
    cooling_size_recommended: UncertaintyBand
    
    # Risk assessment
    oversizing_risk: float  # 0-1, risk of oversizing
    undersizing_risk: float  # 0-1, risk of undersizing
    
    # Recommendations
    recommendations: List[str]
    data_gaps: List[str]


class ConfidenceScorer:
    """
    Calculate confidence scores and uncertainty bands for HVAC calculations.
    Provides transparent assessment of data quality and calculation reliability.
    """
    
    # Confidence weights for different components
    COMPONENT_WEIGHTS = {
        "geometry": 0.35,  # Room detection and areas
        "envelope": 0.25,  # Insulation, windows, etc.
        "infiltration": 0.20,  # Air leakage
        "internal_gains": 0.10,  # People, equipment
        "duct_losses": 0.10,  # Distribution losses
    }
    
    # Uncertainty multipliers by data quality
    QUALITY_UNCERTAINTY = {
        DataQuality.MEASURED: 0.05,  # ±5% for measured
        DataQuality.DETECTED: 0.15,  # ±15% for detected
        DataQuality.INFERRED: 0.25,  # ±25% for inferred
        DataQuality.DEFAULT: 0.40,  # ±40% for defaults
    }
    
    def calculate_confidence(
        self,
        geometry_data: Dict[str, Any],
        envelope_data: Dict[str, Any],
        infiltration_data: Dict[str, Any],
        loads_data: Dict[str, Any],
        calculation_method: str = "manual_j"
    ) -> LoadCalculationConfidence:
        """
        Calculate comprehensive confidence scores and uncertainty bands.
        
        Args:
            geometry_data: Room detection and area data
            envelope_data: Building envelope parameters
            infiltration_data: Infiltration calculation data
            loads_data: Load calculation results
            calculation_method: Method used for calculations
            
        Returns:
            Complete confidence assessment with uncertainty bands
        """
        logger.info("Calculating confidence scores and uncertainty bands")
        
        # Score individual components
        geometry_conf = self._score_geometry(geometry_data)
        envelope_conf = self._score_envelope(envelope_data)
        infiltration_conf = self._score_infiltration(infiltration_data)
        loads_conf = self._score_loads(loads_data, calculation_method)
        
        # Calculate overall confidence
        overall = self._calculate_overall_confidence({
            "geometry": geometry_conf.overall,
            "envelope": envelope_conf.overall,
            "infiltration": infiltration_conf.overall,
            "loads": loads_conf.overall
        })
        
        # Determine quality level
        if overall >= 0.85:
            quality = "high"
        elif overall >= 0.70:
            quality = "medium"
        else:
            quality = "low"
        
        # Calculate load uncertainty bands
        heating_band = self._calculate_load_uncertainty(
            loads_data.get("total_heating_load", 0),
            overall,
            "heating"
        )
        
        cooling_band = self._calculate_load_uncertainty(
            loads_data.get("total_cooling_load", 0),
            overall,
            "cooling"
        )
        
        # Equipment sizing with appropriate safety factors
        heating_size = self._recommend_equipment_size(heating_band, overall, "heating")
        cooling_size = self._recommend_equipment_size(cooling_band, overall, "cooling")
        
        # Risk assessment
        oversizing_risk = self._assess_oversizing_risk(overall, quality)
        undersizing_risk = self._assess_undersizing_risk(overall, quality)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall, geometry_conf, envelope_conf, infiltration_conf
        )
        
        # Identify data gaps
        data_gaps = self._identify_data_gaps(
            geometry_conf, envelope_conf, infiltration_conf
        )
        
        logger.info(f"Overall confidence: {overall:.1%} ({quality})")
        logger.info(f"Heating load: {heating_band.nominal:.0f} BTU/hr "
                   f"({heating_band.lower_bound:.0f}-{heating_band.upper_bound:.0f})")
        logger.info(f"Cooling load: {cooling_band.nominal:.0f} BTU/hr "
                   f"({cooling_band.lower_bound:.0f}-{cooling_band.upper_bound:.0f})")
        
        return LoadCalculationConfidence(
            geometry_confidence=geometry_conf,
            envelope_confidence=envelope_conf,
            infiltration_confidence=infiltration_conf,
            loads_confidence=loads_conf,
            overall_confidence=overall,
            overall_quality=quality,
            heating_load_band=heating_band,
            cooling_load_band=cooling_band,
            heating_size_recommended=heating_size,
            cooling_size_recommended=cooling_size,
            oversizing_risk=oversizing_risk,
            undersizing_risk=undersizing_risk,
            recommendations=recommendations,
            data_gaps=data_gaps
        )
    
    def _score_geometry(self, data: Dict[str, Any]) -> ConfidenceScore:
        """Score confidence in geometry detection"""
        
        components = {}
        quality = {}
        factors = []
        
        # Scale detection confidence
        scale_method = data.get("scale_method", "default")
        if scale_method == "consensus":
            components["scale"] = 0.95
            quality["scale"] = DataQuality.DETECTED
        elif scale_method == "single_method":
            components["scale"] = 0.75
            quality["scale"] = DataQuality.DETECTED
            factors.append("Single scale detection method")
        else:
            components["scale"] = 0.40
            quality["scale"] = DataQuality.DEFAULT
            factors.append("No scale detected - using default")
        
        # Room detection confidence
        num_rooms = data.get("num_rooms", 0)
        avg_room_size = data.get("avg_room_size", 0)
        
        if num_rooms > 0 and 40 <= avg_room_size <= 500:
            components["rooms"] = 0.90
            quality["rooms"] = DataQuality.DETECTED
        elif num_rooms > 0:
            components["rooms"] = 0.70
            quality["rooms"] = DataQuality.DETECTED
            factors.append("Unusual room sizes detected")
        else:
            components["rooms"] = 0.30
            quality["rooms"] = DataQuality.DEFAULT
            factors.append("Room detection failed")
        
        # Area calculation confidence
        total_area = data.get("total_area", 0)
        if 500 <= total_area <= 10000:
            components["area"] = 0.85
        else:
            components["area"] = 0.50
            factors.append("Unusual total area")
        
        # Calculate overall geometry confidence
        overall = np.average(
            list(components.values()),
            weights=[0.4, 0.4, 0.2]  # Scale most important
        )
        
        notes = f"Geometry confidence: {overall:.1%}"
        if factors:
            notes += f" - Issues: {', '.join(factors)}"
        
        return ConfidenceScore(
            overall=overall,
            components=components,
            data_quality=quality,
            uncertainty_factors=factors,
            notes=notes
        )
    
    def _score_envelope(self, data: Dict[str, Any]) -> ConfidenceScore:
        """Score confidence in envelope parameters"""
        
        components = {}
        quality = {}
        factors = []
        
        # Check detected vs defaulted values
        detected_count = data.get("detected_count", 0)
        defaulted_count = data.get("defaulted_count", 0)
        total_count = detected_count + defaulted_count
        
        if total_count > 0:
            detection_ratio = detected_count / total_count
            components["detection"] = detection_ratio
            
            if detection_ratio < 0.3:
                factors.append("Most envelope values are defaults")
                quality["envelope"] = DataQuality.DEFAULT
            elif detection_ratio < 0.7:
                quality["envelope"] = DataQuality.INFERRED
            else:
                quality["envelope"] = DataQuality.DETECTED
        else:
            components["detection"] = 0.0
            quality["envelope"] = DataQuality.DEFAULT
        
        # Wall R-value confidence
        wall_r_source = data.get("wall_r_source", "default")
        if wall_r_source == "detected":
            components["walls"] = 0.90
        elif wall_r_source == "vintage_default":
            components["walls"] = 0.60
        else:
            components["walls"] = 0.40
        
        # Window confidence
        window_source = data.get("window_source", "default")
        if window_source == "schedule":
            components["windows"] = 0.95
            quality["windows"] = DataQuality.DETECTED
        elif window_source == "detected":
            components["windows"] = 0.80
            quality["windows"] = DataQuality.DETECTED
        else:
            components["windows"] = 0.50
            quality["windows"] = DataQuality.DEFAULT
            factors.append("Window specifications not found")
        
        # Calculate overall
        overall = np.mean(list(components.values()))
        
        notes = f"Envelope confidence: {overall:.1%}"
        if detected_count > 0:
            notes += f" ({detected_count} detected, {defaulted_count} defaulted)"
        
        return ConfidenceScore(
            overall=overall,
            components=components,
            data_quality=quality,
            uncertainty_factors=factors,
            notes=notes
        )
    
    def _score_infiltration(self, data: Dict[str, Any]) -> ConfidenceScore:
        """Score confidence in infiltration calculations"""
        
        components = {}
        quality = {}
        factors = []
        
        # Method used
        method = data.get("method", "default")
        if method == "blower_door":
            components["method"] = 0.95
            quality["infiltration"] = DataQuality.MEASURED
        elif method == "construction_quality":
            components["method"] = 0.60
            quality["infiltration"] = DataQuality.INFERRED
        else:
            components["method"] = 0.40
            quality["infiltration"] = DataQuality.DEFAULT
            factors.append("Using default infiltration rate")
        
        # ACH50 value reasonableness
        ach50 = data.get("ach50", 7.0)
        if 1.0 <= ach50 <= 25.0:
            components["value"] = 0.80
        else:
            components["value"] = 0.40
            factors.append("Unusual ACH50 value")
        
        overall = np.mean(list(components.values()))
        
        return ConfidenceScore(
            overall=overall,
            components=components,
            data_quality=quality,
            uncertainty_factors=factors,
            notes=f"Infiltration confidence: {overall:.1%} ({method})"
        )
    
    def _score_loads(self, data: Dict[str, Any], method: str) -> ConfidenceScore:
        """Score confidence in load calculations"""
        
        components = {}
        factors = []
        
        # Method confidence
        if method == "manual_j":
            components["method"] = 0.90
        elif method == "simplified":
            components["method"] = 0.70
        else:
            components["method"] = 0.50
        
        # Load reasonableness check
        total_area = data.get("total_area", 2000)
        heating_load = data.get("total_heating_load", 0)
        cooling_load = data.get("total_cooling_load", 0)
        
        # BTU/sqft sanity checks
        heating_per_sqft = heating_load / total_area if total_area > 0 else 0
        cooling_per_sqft = cooling_load / total_area if total_area > 0 else 0
        
        # Typical ranges: 15-60 BTU/sqft heating, 10-40 BTU/sqft cooling
        if 15 <= heating_per_sqft <= 60:
            components["heating_range"] = 0.90
        elif 10 <= heating_per_sqft <= 80:
            components["heating_range"] = 0.70
        else:
            components["heating_range"] = 0.40
            factors.append(f"Unusual heating load: {heating_per_sqft:.0f} BTU/sqft")
        
        if 10 <= cooling_per_sqft <= 40:
            components["cooling_range"] = 0.90
        elif 5 <= cooling_per_sqft <= 50:
            components["cooling_range"] = 0.70
        else:
            components["cooling_range"] = 0.40
            factors.append(f"Unusual cooling load: {cooling_per_sqft:.0f} BTU/sqft")
        
        overall = np.mean(list(components.values()))
        
        return ConfidenceScore(
            overall=overall,
            components=components,
            data_quality={"method": DataQuality.DETECTED},
            uncertainty_factors=factors,
            notes=f"Load calculation confidence: {overall:.1%}"
        )
    
    def _calculate_overall_confidence(
        self,
        component_scores: Dict[str, float]
    ) -> float:
        """Calculate weighted overall confidence"""
        
        total_weight = 0
        weighted_sum = 0
        
        for component, score in component_scores.items():
            weight = self.COMPONENT_WEIGHTS.get(component, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _calculate_load_uncertainty(
        self,
        nominal_load: float,
        confidence: float,
        load_type: str
    ) -> UncertaintyBand:
        """Calculate uncertainty band for load estimate"""
        
        # Base uncertainty from confidence
        base_uncertainty = 1.0 - confidence
        
        # Adjust for load type
        if load_type == "heating":
            # Heating tends to have higher uncertainty (weather variability)
            uncertainty_factor = base_uncertainty * 1.2
        else:
            # Cooling is more predictable
            uncertainty_factor = base_uncertainty * 1.0
        
        # Calculate bounds
        # Higher confidence = tighter bands
        if confidence >= 0.85:
            lower_mult = 0.90  # -10%
            upper_mult = 1.15  # +15%
        elif confidence >= 0.70:
            lower_mult = 0.80  # -20%
            upper_mult = 1.30  # +30%
        else:
            lower_mult = 0.65  # -35%
            upper_mult = 1.50  # +50%
        
        return UncertaintyBand(
            nominal=nominal_load,
            lower_bound=nominal_load * lower_mult,
            upper_bound=nominal_load * upper_mult,
            confidence_level=0.90,  # 90% confidence interval
            distribution="normal"
        )
    
    def _recommend_equipment_size(
        self,
        load_band: UncertaintyBand,
        confidence: float,
        equipment_type: str
    ) -> UncertaintyBand:
        """Recommend equipment size with appropriate safety factor"""
        
        # Base sizing on upper bound for safety
        # But adjust safety factor based on confidence
        if confidence >= 0.85:
            # High confidence: use nominal + 10%
            size = load_band.nominal * 1.10
        elif confidence >= 0.70:
            # Medium confidence: use midpoint + 15%
            midpoint = (load_band.nominal + load_band.upper_bound) / 2
            size = midpoint * 1.15
        else:
            # Low confidence: use upper bound
            size = load_band.upper_bound
        
        # Round to standard equipment sizes (tons)
        tons = size / 12000
        
        # Standard residential sizes: 1.5, 2, 2.5, 3, 3.5, 4, 5 tons
        standard_sizes = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
        
        # Find next size up
        for standard in standard_sizes:
            if standard >= tons:
                recommended_tons = standard
                break
        else:
            recommended_tons = math.ceil(tons)
        
        recommended_btu = recommended_tons * 12000
        
        return UncertaintyBand(
            nominal=recommended_btu,
            lower_bound=recommended_btu * 0.9,  # Could go one size down
            upper_bound=recommended_btu * 1.1,  # Might need one size up
            confidence_level=confidence,
            distribution="discrete"
        )
    
    def _assess_oversizing_risk(self, confidence: float, quality: str) -> float:
        """Assess risk of oversizing equipment"""
        
        if quality == "high":
            return 0.10  # Low risk with good data
        elif quality == "medium":
            return 0.30  # Moderate risk
        else:
            return 0.60  # High risk with poor data
    
    def _assess_undersizing_risk(self, confidence: float, quality: str) -> float:
        """Assess risk of undersizing equipment"""
        
        if quality == "high":
            return 0.05  # Very low risk
        elif quality == "medium":
            return 0.15  # Low to moderate
        else:
            return 0.25  # Moderate risk (we're conservative)
    
    def _generate_recommendations(
        self,
        overall: float,
        geometry: ConfidenceScore,
        envelope: ConfidenceScore,
        infiltration: ConfidenceScore
    ) -> List[str]:
        """Generate recommendations to improve confidence"""
        
        recommendations = []
        
        if overall < 0.70:
            recommendations.append(
                "Consider professional load calculation for final equipment sizing"
            )
        
        if geometry.overall < 0.70:
            recommendations.append(
                "Verify room dimensions and total square footage on-site"
            )
        
        if envelope.overall < 0.60:
            recommendations.append(
                "Inspect actual insulation levels and window specifications"
            )
        
        if infiltration.overall < 0.60:
            recommendations.append(
                "Consider blower door test for accurate infiltration rate"
            )
        
        if overall >= 0.85:
            recommendations.append(
                "High confidence calculation - suitable for equipment selection"
            )
        
        return recommendations
    
    def _identify_data_gaps(
        self,
        geometry: ConfidenceScore,
        envelope: ConfidenceScore,
        infiltration: ConfidenceScore
    ) -> List[str]:
        """Identify missing or low-quality data"""
        
        gaps = []
        
        # Check each component's factors
        for factor in geometry.uncertainty_factors:
            if "scale" in factor.lower():
                gaps.append("Blueprint scale not clearly marked")
            if "room" in factor.lower():
                gaps.append("Room boundaries unclear or missing")
        
        for factor in envelope.uncertainty_factors:
            if "window" in factor.lower():
                gaps.append("Window schedule or specifications missing")
            if "insulation" in factor.lower():
                gaps.append("Insulation R-values not specified")
        
        for factor in infiltration.uncertainty_factors:
            if "default" in factor.lower():
                gaps.append("Building tightness unknown - using defaults")
        
        return gaps


# Singleton instance
confidence_scorer = ConfidenceScorer()