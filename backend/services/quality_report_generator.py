"""
Quality Report Generator for HVAC Load Calculations
Generates comprehensive reports with confidence scores and data provenance
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Comprehensive quality report for load calculation"""
    # Identification
    job_id: str
    timestamp: datetime
    pdf_filename: str
    
    # Summary Results
    total_area_sqft: float
    num_rooms: int
    heating_load_btu: float
    cooling_load_btu: float
    heating_tons: float
    cooling_tons: float
    
    # Confidence Metrics
    overall_confidence: float
    geometry_confidence: float
    envelope_confidence: float
    infiltration_confidence: float
    loads_confidence: float
    
    # Data Quality
    data_completeness: float
    detected_values: int
    defaulted_values: int
    data_gaps: List[str]
    
    # Uncertainty Bands
    heating_range: Dict[str, float]  # nominal, lower, upper
    cooling_range: Dict[str, float]
    
    # Equipment Recommendations
    heating_size_recommended: float
    cooling_size_recommended: float
    oversizing_risk: float
    undersizing_risk: float
    
    # Processing Metrics
    processing_time_ms: float
    stages_completed: int
    stages_failed: int
    warnings_count: int
    
    # Key Decisions
    scale_method: str
    scale_value: float
    infiltration_method: str
    ach50_value: float
    duct_location: str
    duct_r_value: float
    
    # Recommendations
    confidence_improvements: List[str]
    system_recommendations: List[str]
    
    # Raw data for detailed analysis
    stage_metrics: List[Dict[str, Any]]
    provenance_data: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


class QualityReportGenerator:
    """
    Generates comprehensive quality reports for HVAC load calculations.
    Combines metrics, confidence scores, and provenance tracking.
    """
    
    def generate_report(
        self,
        metrics: Dict[str, Any],
        confidence: Dict[str, Any],
        results: Dict[str, Any],
        provenance: List[Dict[str, Any]]
    ) -> QualityReport:
        """
        Generate comprehensive quality report.
        
        Args:
            metrics: Pipeline metrics from MetricsCollector
            confidence: Confidence scores from ConfidenceScorer
            results: Load calculation results
            provenance: Data provenance tracking
            
        Returns:
            Complete quality report
        """
        logger.info(f"Generating quality report for job {metrics.get('job_id')}")
        
        # Extract key values
        job_id = metrics.get("job_id", "unknown")
        
        # Summary results
        total_area = results.get("total_area", 0)
        num_rooms = results.get("num_rooms", 0)
        heating_load = results.get("total_heating_load", 0)
        cooling_load = results.get("total_cooling_load", 0)
        heating_tons = heating_load / 12000
        cooling_tons = cooling_load / 12000
        
        # Confidence scores
        overall_conf = confidence.get("overall_confidence", 0)
        geometry_conf = confidence.get("geometry_confidence", {}).get("overall", 0)
        envelope_conf = confidence.get("envelope_confidence", {}).get("overall", 0)
        infiltration_conf = confidence.get("infiltration_confidence", {}).get("overall", 0)
        loads_conf = confidence.get("loads_confidence", {}).get("overall", 0)
        
        # Data quality
        detected = sum(1 for p in provenance if p.get("source") == "detected")
        defaulted = sum(1 for p in provenance if p.get("source") in ["default", "code_default"])
        total_values = len(provenance)
        completeness = detected / total_values if total_values > 0 else 0
        
        data_gaps = confidence.get("data_gaps", [])
        
        # Uncertainty bands
        heating_band = confidence.get("heating_load_band", {})
        cooling_band = confidence.get("cooling_load_band", {})
        
        heating_range = {
            "nominal": heating_band.get("nominal", heating_load),
            "lower": heating_band.get("lower_bound", heating_load * 0.8),
            "upper": heating_band.get("upper_bound", heating_load * 1.2)
        }
        
        cooling_range = {
            "nominal": cooling_band.get("nominal", cooling_load),
            "lower": cooling_band.get("lower_bound", cooling_load * 0.8),
            "upper": cooling_band.get("upper_bound", cooling_load * 1.2)
        }
        
        # Equipment recommendations
        heating_size = confidence.get("heating_size_recommended", {}).get("nominal", heating_tons * 12000)
        cooling_size = confidence.get("cooling_size_recommended", {}).get("nominal", cooling_tons * 12000)
        oversizing_risk = confidence.get("oversizing_risk", 0.3)
        undersizing_risk = confidence.get("undersizing_risk", 0.1)
        
        # Processing metrics
        processing_time = metrics.get("total_duration_ms", 0)
        stages = metrics.get("stages", [])
        stages_completed = sum(1 for s in stages if s.get("success"))
        stages_failed = len(stages) - stages_completed
        warnings = metrics.get("warnings", [])
        
        # Key decisions from provenance
        scale_data = self._find_provenance(provenance, "scale")
        infiltration_data = self._find_provenance(provenance, "infiltration")
        duct_data = self._find_provenance(provenance, "duct")
        
        # Recommendations
        confidence_improvements = confidence.get("recommendations", [])
        system_recommendations = self._generate_system_recommendations(
            heating_tons, cooling_tons, overall_conf
        )
        
        # Create report
        report = QualityReport(
            job_id=job_id,
            timestamp=datetime.now(),
            pdf_filename=metrics.get("pdf_filename", "unknown"),
            total_area_sqft=total_area,
            num_rooms=num_rooms,
            heating_load_btu=heating_load,
            cooling_load_btu=cooling_load,
            heating_tons=heating_tons,
            cooling_tons=cooling_tons,
            overall_confidence=overall_conf,
            geometry_confidence=geometry_conf,
            envelope_confidence=envelope_conf,
            infiltration_confidence=infiltration_conf,
            loads_confidence=loads_conf,
            data_completeness=completeness,
            detected_values=detected,
            defaulted_values=defaulted,
            data_gaps=data_gaps,
            heating_range=heating_range,
            cooling_range=cooling_range,
            heating_size_recommended=heating_size / 12000,  # Convert to tons
            cooling_size_recommended=cooling_size / 12000,
            oversizing_risk=oversizing_risk,
            undersizing_risk=undersizing_risk,
            processing_time_ms=processing_time,
            stages_completed=stages_completed,
            stages_failed=stages_failed,
            warnings_count=len(warnings),
            scale_method=scale_data.get("method", "unknown"),
            scale_value=scale_data.get("value", 48.0),
            infiltration_method=infiltration_data.get("method", "default"),
            ach50_value=infiltration_data.get("ach50", 7.0),
            duct_location=duct_data.get("location", "attic"),
            duct_r_value=duct_data.get("r_value", 8.0),
            confidence_improvements=confidence_improvements,
            system_recommendations=system_recommendations,
            stage_metrics=stages,
            provenance_data=provenance,
            warnings=warnings
        )
        
        return report
    
    def _find_provenance(
        self,
        provenance: List[Dict[str, Any]],
        field_prefix: str
    ) -> Dict[str, Any]:
        """Find provenance data for a field"""
        result = {}
        for p in provenance:
            field = p.get("field", "")
            if field_prefix in field.lower():
                result[field] = p.get("value")
                result["method"] = p.get("source", "unknown")
                result["confidence"] = p.get("confidence", 0)
        return result
    
    def _generate_system_recommendations(
        self,
        heating_tons: float,
        cooling_tons: float,
        confidence: float
    ) -> List[str]:
        """Generate HVAC system recommendations"""
        recommendations = []
        
        # Equipment type recommendations
        if cooling_tons <= 5:
            recommendations.append(
                "Consider high-efficiency split system or ductless mini-splits"
            )
        else:
            recommendations.append(
                "Commercial-grade equipment may be required for this load"
            )
        
        # Efficiency recommendations
        recommendations.append(
            "Recommend minimum 16 SEER cooling, 95% AFUE heating for energy savings"
        )
        
        # Zoning recommendations
        if cooling_tons >= 3:
            recommendations.append(
                "Consider zoning system for improved comfort and efficiency"
        )
        
        # Heat pump consideration
        if heating_tons <= cooling_tons * 1.5:
            recommendations.append(
                "Heat pump may be cost-effective for both heating and cooling"
            )
        
        return recommendations
    
    def format_text_report(self, report: QualityReport) -> str:
        """Format report as text"""
        lines = []
        lines.append("=" * 80)
        lines.append("HVAC LOAD CALCULATION QUALITY REPORT")
        lines.append("=" * 80)
        lines.append(f"Job ID: {report.job_id}")
        lines.append(f"Date: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"PDF: {report.pdf_filename}")
        lines.append("")
        
        # Summary Results
        lines.append("CALCULATED LOADS")
        lines.append("-" * 40)
        lines.append(f"Building Area: {report.total_area_sqft:,.0f} sq ft")
        lines.append(f"Number of Rooms: {report.num_rooms}")
        lines.append(f"Heating Load: {report.heating_load_btu:,.0f} BTU/hr ({report.heating_tons:.1f} tons)")
        lines.append(f"Cooling Load: {report.cooling_load_btu:,.0f} BTU/hr ({report.cooling_tons:.1f} tons)")
        lines.append("")
        
        # Confidence Assessment
        lines.append("CONFIDENCE ASSESSMENT")
        lines.append("-" * 40)
        lines.append(f"Overall Confidence: {report.overall_confidence:.1%} {self._get_confidence_emoji(report.overall_confidence)}")
        lines.append(f"  Geometry: {report.geometry_confidence:.1%}")
        lines.append(f"  Envelope: {report.envelope_confidence:.1%}")
        lines.append(f"  Infiltration: {report.infiltration_confidence:.1%}")
        lines.append(f"  Load Calculation: {report.loads_confidence:.1%}")
        lines.append(f"Data Completeness: {report.data_completeness:.1%}")
        lines.append(f"  Detected Values: {report.detected_values}")
        lines.append(f"  Defaulted Values: {report.defaulted_values}")
        lines.append("")
        
        # Uncertainty Ranges
        lines.append("LOAD UNCERTAINTY RANGES (90% confidence)")
        lines.append("-" * 40)
        lines.append(f"Heating: {report.heating_range['lower']:,.0f} - {report.heating_range['upper']:,.0f} BTU/hr")
        lines.append(f"Cooling: {report.cooling_range['lower']:,.0f} - {report.cooling_range['upper']:,.0f} BTU/hr")
        lines.append("")
        
        # Equipment Sizing
        lines.append("EQUIPMENT SIZING RECOMMENDATIONS")
        lines.append("-" * 40)
        lines.append(f"Heating System: {report.heating_size_recommended:.1f} tons")
        lines.append(f"Cooling System: {report.cooling_size_recommended:.1f} tons")
        lines.append(f"Oversizing Risk: {report.oversizing_risk:.0%}")
        lines.append(f"Undersizing Risk: {report.undersizing_risk:.0%}")
        lines.append("")
        
        # Key Parameters
        lines.append("KEY CALCULATION PARAMETERS")
        lines.append("-" * 40)
        lines.append(f"Scale Detection: {report.scale_method} ({report.scale_value:.1f} px/ft)")
        lines.append(f"Infiltration: {report.infiltration_method} ({report.ach50_value:.1f} ACH50)")
        lines.append(f"Duct Location: {report.duct_location} (R-{report.duct_r_value})")
        lines.append("")
        
        # Data Gaps
        if report.data_gaps:
            lines.append("DATA GAPS IDENTIFIED")
            lines.append("-" * 40)
            for gap in report.data_gaps[:10]:
                lines.append(f"  • {gap}")
            lines.append("")
        
        # Recommendations
        if report.confidence_improvements:
            lines.append("TO IMPROVE CONFIDENCE")
            lines.append("-" * 40)
            for rec in report.confidence_improvements:
                lines.append(f"  • {rec}")
            lines.append("")
        
        if report.system_recommendations:
            lines.append("SYSTEM RECOMMENDATIONS")
            lines.append("-" * 40)
            for rec in report.system_recommendations:
                lines.append(f"  • {rec}")
            lines.append("")
        
        # Processing Metrics
        lines.append("PROCESSING METRICS")
        lines.append("-" * 40)
        lines.append(f"Processing Time: {report.processing_time_ms:.0f}ms")
        lines.append(f"Stages Completed: {report.stages_completed}")
        lines.append(f"Warnings: {report.warnings_count}")
        lines.append("")
        
        # Quality Assessment
        lines.append("QUALITY ASSESSMENT")
        lines.append("-" * 40)
        if report.overall_confidence >= 0.85:
            lines.append("✓ HIGH CONFIDENCE - Results suitable for equipment selection")
        elif report.overall_confidence >= 0.70:
            lines.append("⚠ MEDIUM CONFIDENCE - Verify key parameters before final sizing")
        else:
            lines.append("✗ LOW CONFIDENCE - Professional verification recommended")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _get_confidence_emoji(self, confidence: float) -> str:
        """Get emoji for confidence level"""
        if confidence >= 0.85:
            return "✅"
        elif confidence >= 0.70:
            return "⚠️"
        else:
            return "❌"
    
    def generate_pdf_report(
        self,
        report: QualityReport,
        output_path: str
    ) -> str:
        """Generate PDF report with visualizations"""
        try:
            with PdfPages(output_path) as pdf:
                # Page 1: Summary and confidence
                fig = plt.figure(figsize=(8.5, 11))
                
                # Title
                fig.suptitle("HVAC Load Calculation Quality Report", fontsize=16, fontweight='bold')
                
                # Create subplots
                gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)
                
                # Confidence radar chart
                ax1 = fig.add_subplot(gs[0:2, :])
                self._plot_confidence_radar(ax1, report)
                
                # Load ranges
                ax2 = fig.add_subplot(gs[2, :])
                self._plot_load_ranges(ax2, report)
                
                # Data quality pie
                ax3 = fig.add_subplot(gs[3, 0])
                self._plot_data_quality(ax3, report)
                
                # Risk assessment
                ax4 = fig.add_subplot(gs[3, 1])
                self._plot_risk_assessment(ax4, report)
                
                pdf.savefig(fig)
                plt.close(fig)
                
                # Page 2: Detailed metrics
                fig = plt.figure(figsize=(8.5, 11))
                ax = fig.add_subplot(111)
                ax.axis('off')
                
                # Format text report
                text_report = self.format_text_report(report)
                ax.text(0.05, 0.95, text_report, transform=ax.transAxes,
                       fontsize=8, fontfamily='monospace',
                       verticalalignment='top')
                
                pdf.savefig(fig)
                plt.close(fig)
                
            logger.info(f"PDF report generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            # Fall back to text report
            text_path = output_path.replace('.pdf', '.txt')
            with open(text_path, 'w') as f:
                f.write(self.format_text_report(report))
            return text_path
    
    def _plot_confidence_radar(self, ax, report: QualityReport):
        """Plot confidence radar chart"""
        categories = ['Geometry', 'Envelope', 'Infiltration', 'Loads', 'Overall']
        values = [
            report.geometry_confidence,
            report.envelope_confidence,
            report.infiltration_confidence,
            report.loads_confidence,
            report.overall_confidence
        ]
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values_plot = values + values[:1]  # Complete the circle
        angles += angles[:1]
        
        ax.plot(angles, values_plot, 'o-', linewidth=2, color='blue')
        ax.fill(angles, values_plot, alpha=0.25, color='blue')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.set_title("Confidence Scores by Component", fontweight='bold')
        ax.grid(True)
    
    def _plot_load_ranges(self, ax, report: QualityReport):
        """Plot load uncertainty ranges"""
        loads = ['Heating', 'Cooling']
        nominals = [report.heating_load_btu / 1000, report.cooling_load_btu / 1000]  # kBTU
        lowers = [report.heating_range['lower'] / 1000, report.cooling_range['lower'] / 1000]
        uppers = [report.heating_range['upper'] / 1000, report.cooling_range['upper'] / 1000]
        
        x = np.arange(len(loads))
        width = 0.35
        
        bars = ax.bar(x, nominals, width, label='Nominal', color='green', alpha=0.7)
        ax.errorbar(x, nominals, yerr=[np.array(nominals) - np.array(lowers),
                                       np.array(uppers) - np.array(nominals)],
                   fmt='none', color='black', capsize=10, capthick=2)
        
        ax.set_ylabel('Load (kBTU/hr)')
        ax.set_title('Load Estimates with Uncertainty Bands')
        ax.set_xticks(x)
        ax.set_xticklabels(loads)
        ax.legend()
    
    def _plot_data_quality(self, ax, report: QualityReport):
        """Plot data quality pie chart"""
        sizes = [report.detected_values, report.defaulted_values]
        labels = ['Detected', 'Defaulted']
        colors = ['green', 'orange']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%',
               startangle=90)
        ax.set_title('Data Sources')
    
    def _plot_risk_assessment(self, ax, report: QualityReport):
        """Plot risk assessment bars"""
        risks = ['Oversizing', 'Undersizing']
        values = [report.oversizing_risk, report.undersizing_risk]
        colors = ['orange' if v > 0.3 else 'green' for v in values]
        
        bars = ax.bar(risks, values, color=colors, alpha=0.7)
        ax.set_ylim(0, 1)
        ax.set_ylabel('Risk Level')
        ax.set_title('Equipment Sizing Risks')
        ax.axhline(y=0.3, color='r', linestyle='--', alpha=0.3)
        
        # Add percentage labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.0%}', ha='center', va='bottom')
    
    def export_json(self, report: QualityReport, output_path: str) -> str:
        """Export report as JSON"""
        data = asdict(report)
        # Convert datetime
        data['timestamp'] = report.timestamp.isoformat()
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"JSON report exported: {output_path}")
        return output_path


# Singleton instance
quality_report_generator = QualityReportGenerator()