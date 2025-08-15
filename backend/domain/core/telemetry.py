"""
Reliability Telemetry and Reporting
Provides full transparency into reliability engine decisions
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .reliability import ReliabilityResult

logger = logging.getLogger(__name__)


@dataclass
class TelemetryReport:
    """Complete telemetry report for reliability analysis"""
    # Timestamp and identification
    timestamp: str
    blueprint_id: Optional[str]
    
    # Quality assessment
    quality_score: float
    routing_decision: str
    confidence: float
    
    # Method results and weights
    method_results: Dict[str, Dict[str, float]]
    ensemble_weights: Dict[str, float]
    method_spread: float
    
    # Final results
    final_loads: Dict[str, float]
    
    # Applied safeguards
    conservative_policies: List[str]
    clamps_applied: List[Dict[str, Any]]
    
    # Orientation handling
    orientation_band: Optional[Dict[str, Any]]
    
    # Decision rationale
    decision_notes: List[str]
    quality_factors: List[str]
    
    # Performance metrics
    processing_time: float
    accuracy_prediction: Dict[str, Any]


class ReliabilityTelemetry:
    """
    Collects and formats telemetry data from reliability engine decisions.
    Provides transparency and debugging information for accuracy analysis.
    """
    
    def __init__(self):
        self.reports = []
    
    def create_report(
        self,
        reliability_result: ReliabilityResult,
        processing_time: float = 0,
        blueprint_id: Optional[str] = None
    ) -> TelemetryReport:
        """
        Create comprehensive telemetry report from reliability result.
        
        Args:
            reliability_result: Result from ensemble decision engine
            processing_time: Total processing time in seconds
            blueprint_id: Optional identifier for blueprint
            
        Returns:
            TelemetryReport with full transparency data
        """
        
        # Extract method results
        method_results = {}
        for candidate in reliability_result.candidates:
            method_results[candidate.name] = {
                'heating_btuh': candidate.heating_btuh,
                'cooling_btuh': candidate.cooling_btuh
            }
        
        # Create accuracy prediction
        accuracy_prediction = self._predict_accuracy(reliability_result)
        
        report = TelemetryReport(
            timestamp=datetime.now().isoformat(),
            blueprint_id=blueprint_id,
            quality_score=reliability_result.quality_score,
            routing_decision=reliability_result.routing_decision,
            confidence=reliability_result.confidence,
            method_results=method_results,
            ensemble_weights=reliability_result.weights,
            method_spread=reliability_result.spread,
            final_loads={
                'heating_btuh': reliability_result.heating_btuh,
                'cooling_btuh': reliability_result.cooling_btuh
            },
            conservative_policies=reliability_result.conservative_policies or [],
            clamps_applied=reliability_result.clamps_applied or [],
            orientation_band=reliability_result.orientation_band,
            decision_notes=reliability_result.notes or [],
            quality_factors=getattr(reliability_result, 'confidence_factors', []),
            processing_time=processing_time,
            accuracy_prediction=accuracy_prediction
        )
        
        self.reports.append(report)
        return report
    
    def _predict_accuracy(self, reliability_result: ReliabilityResult) -> Dict[str, Any]:
        """
        Predict expected accuracy based on reliability metrics.
        """
        
        # Base accuracy prediction on confidence and spread
        confidence = reliability_result.confidence
        spread = reliability_result.spread
        
        # Predict accuracy range
        if confidence >= 0.9 and spread <= 0.05:
            predicted_range = "±5%"
            expected_accuracy = ">95%"
            risk_level = "very_low"
        elif confidence >= 0.8 and spread <= 0.10:
            predicted_range = "±8%"
            expected_accuracy = "90-95%"
            risk_level = "low"
        elif confidence >= 0.6 and spread <= 0.15:
            predicted_range = "±12%"
            expected_accuracy = "85-90%"
            risk_level = "medium"
        else:
            predicted_range = "±15%"
            expected_accuracy = "75-85%"
            risk_level = "high"
        
        # Risk factors
        risk_factors = []
        if reliability_result.quality_score < 0.5:
            risk_factors.append("Low blueprint quality")
        if spread > 0.15:
            risk_factors.append("High method disagreement")
        if reliability_result.clamps_applied:
            risk_factors.append("Sanity clamps triggered")
        if len(reliability_result.conservative_policies or []) > 5:
            risk_factors.append("Many missing specifications")
        
        return {
            'predicted_range': predicted_range,
            'expected_accuracy': expected_accuracy,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'confidence_score': confidence,
            'method_spread': spread
        }
    
    def format_json_report(self, report: TelemetryReport) -> Dict[str, Any]:
        """
        Format telemetry report for JSON output in API responses.
        """
        
        return {
            "reliability": {
                "quality_score": round(report.quality_score, 3),
                "routing_decision": report.routing_decision,
                "confidence": round(report.confidence, 3),
                "method_spread": round(report.method_spread, 3),
                
                "candidates": [
                    {
                        "name": name,
                        "heating": round(data["heating_btuh"], 0),
                        "cooling": round(data["cooling_btuh"], 0)
                    }
                    for name, data in report.method_results.items()
                ],
                
                "ensemble_weights": {
                    name: round(weight, 3) 
                    for name, weight in report.ensemble_weights.items()
                },
                
                "final_result": {
                    "heating": round(report.final_loads["heating_btuh"], 0),
                    "cooling": round(report.final_loads["cooling_btuh"], 0)
                },
                
                "accuracy_prediction": report.accuracy_prediction,
                
                "safeguards_applied": {
                    "conservative_policies": report.conservative_policies,
                    "clamps_applied": [
                        {
                            "type": clamp.get("type", "unknown"),
                            "reason": clamp.get("reason", "")
                        }
                        for clamp in report.clamps_applied
                    ],
                    "orientation_band": report.orientation_band
                },
                
                "decision_rationale": {
                    "notes": report.decision_notes,
                    "quality_factors": report.quality_factors,
                    "processing_time": round(report.processing_time, 2)
                }
            }
        }
    
    def format_summary_log(self, report: TelemetryReport) -> str:
        """
        Format concise summary for logging.
        """
        
        # Method values summary
        method_summary = ", ".join([
            f"{name}:{data['heating_btuh']:,.0f}"
            for name, data in report.method_results.items()
        ])
        
        # Safeguards summary
        safeguards_count = len(report.conservative_policies) + len(report.clamps_applied)
        
        summary = (
            f"🎯 Reliability Summary: "
            f"Q={report.quality_score:.2f} → {report.routing_decision}, "
            f"Confidence={report.confidence:.1%}, "
            f"Spread={report.method_spread:.1%}, "
            f"Methods=[{method_summary}], "
            f"Final={report.final_loads['heating_btuh']:,.0f}h/{report.final_loads['cooling_btuh']:,.0f}c, "
            f"Safeguards={safeguards_count}, "
            f"Risk={report.accuracy_prediction['risk_level']}"
        )
        
        return summary
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated performance metrics across all reports.
        """
        
        if not self.reports:
            return {"error": "No reports available"}
        
        # Aggregate metrics
        avg_quality = sum(r.quality_score for r in self.reports) / len(self.reports)
        avg_confidence = sum(r.confidence for r in self.reports) / len(self.reports)
        avg_spread = sum(r.method_spread for r in self.reports) / len(self.reports)
        
        # Routing distribution
        routing_counts = {}
        for report in self.reports:
            routing = report.routing_decision
            routing_counts[routing] = routing_counts.get(routing, 0) + 1
        
        # Risk level distribution
        risk_counts = {}
        for report in self.reports:
            risk = report.accuracy_prediction['risk_level']
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        return {
            "total_reports": len(self.reports),
            "averages": {
                "quality_score": round(avg_quality, 3),
                "confidence": round(avg_confidence, 3),
                "method_spread": round(avg_spread, 3)
            },
            "routing_distribution": routing_counts,
            "risk_distribution": risk_counts,
            "high_confidence_rate": sum(1 for r in self.reports if r.confidence >= 0.8) / len(self.reports)
        }


# Singleton instance
_telemetry = None

def get_telemetry() -> ReliabilityTelemetry:
    """Get or create the global telemetry collector"""
    global _telemetry
    if _telemetry is None:
        _telemetry = ReliabilityTelemetry()
    return _telemetry