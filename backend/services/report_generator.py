"""
High-Value HVAC Report Generator
Creates conversion-focused reports with user-aware upselling and viral share features
"""

from typing import Dict, Any, List, Optional
import math
import uuid
from datetime import datetime
from domain.core.climate_zones import get_climate_data_for_zip, get_zone_config


class ValueReportGenerator:
    """Generates high-value professional HVAC reports with viral sharing capabilities"""
    
    def __init__(self):
        # Equipment database for recommendations
        self.heat_pump_models = {
            (1.5, 3.0): ["Carrier 25VNA8", "Trane XV18", "Mitsubishi PUZ-HA30"],
            (3.0, 4.5): ["Carrier 25VNA6", "Trane XV20i", "Mitsubishi PUZ-HA42"], 
            (4.5, 6.0): ["Carrier 25HCE6", "Trane XV20i", "Mitsubishi PUZ-HA60"],
            (6.0, 8.0): ["Carrier 25HCE8", "Trane XR17", "Mitsubishi PUZ-HA72"]
        }
        
        # Industry benchmarks for context
        self.industry_ranges = {
            "heating_per_sqft": {"min": 25, "max": 45, "typical": 35},
            "cooling_per_sqft": {"min": 10, "max": 20, "typical": 15}
        }
    
    def generate_complete_report(
        self, 
        pipeline_result: Any, 
        zip_code: str,
        user_subscription_status: str = "free",
        report_context: str = "user"  # "user", "shared", "pdf"
    ) -> Dict[str, Any]:
        """Generate complete report with user-aware features and sharing capabilities"""
        
        # Generate core report sections
        base_report = {
            "building_profile": self._generate_building_profile(pipeline_result, zip_code),
            "load_breakdown": self._generate_load_breakdown(pipeline_result, zip_code),
            "equipment_recommendations": self._generate_equipment_recommendations(pipeline_result),
            "professional_insights": self._generate_professional_insights(pipeline_result),
            "industry_context": self._generate_industry_context(pipeline_result),
            "share_features": self._generate_share_features(pipeline_result, report_context),
            "report_metadata": self._generate_metadata(pipeline_result, user_subscription_status, report_context)
        }
        
        # Add user-specific sections
        if user_subscription_status == "free" and report_context == "user":
            base_report["upgrade_benefits"] = self._generate_subtle_upgrade_hooks(pipeline_result)
        elif user_subscription_status == "paid":
            base_report["premium_sections"] = self._generate_premium_sections(pipeline_result)
        
        # Add viral elements for shared reports
        if report_context == "shared":
            base_report["viral_elements"] = self._generate_viral_elements(pipeline_result)
        
        return base_report
    
    def _generate_building_profile(self, result: Any, zip_code: str) -> Dict[str, Any]:
        """Generate building profile section"""
        
        climate_data = get_climate_data_for_zip(zip_code)
        zone_config = get_zone_config(climate_data['climate_zone'])
        
        # Determine building characteristics
        building_type = "Single-story"
        if hasattr(result, 'building_model') and result.building_model:
            floor_count = len(set(
                space.floor_level 
                for zone in result.building_model.zones 
                for space in zone.spaces 
                if hasattr(space, 'floor_level')
            ))
            if floor_count > 1:
                building_type = f"{floor_count}-story"
        
        # Special features
        special_features = []
        if getattr(result, 'bonus_over_garage', False):
            special_features.append("Bonus room over garage")
        if getattr(result, 'garage_detected', False):
            special_features.append("Attached garage")
        
        return {
            "conditioned_area": f"{result.total_conditioned_area_sqft:,.0f} sq ft",
            "building_type": building_type,
            "zones_analyzed": f"{result.zones_created} thermal zones",
            "spaces_detected": f"{result.spaces_detected} spaces analyzed",
            "climate_zone": f"Zone {climate_data['climate_zone']} ({zone_config.get('name', 'Mixed Climate')})",
            "climate_location": climate_data.get('location', 'US'),
            "analysis_confidence": f"{result.confidence_score:.0%}",
            "confidence_level": self._get_confidence_level(result.confidence_score),
            "special_features": special_features,
            "design_temperatures": {
                "winter_99": f"{climate_data['winter_99']:.0f}°F",
                "summer_1": f"{climate_data['summer_1']:.0f}°F"
            }
        }
    
    def _generate_load_breakdown(self, result: Any, zip_code: str) -> Dict[str, Any]:
        """Generate detailed load calculation breakdown"""
        
        climate_data = get_climate_data_for_zip(zip_code)
        zone_config = get_zone_config(climate_data['climate_zone'])
        
        # Calculate base vs safety factor breakdown
        heating_safety = zone_config.get('safety_factor_heating', 1.08)
        cooling_safety = zone_config.get('safety_factor_cooling', 1.05)
        
        # Estimate base loads (reverse engineer from final)
        base_heating = result.heating_load_btu_hr / heating_safety
        base_cooling = result.cooling_load_btu_hr / cooling_safety
        
        heating_safety_btus = result.heating_load_btu_hr - base_heating
        cooling_safety_btus = result.cooling_load_btu_hr - base_cooling
        
        return {
            "heating_analysis": {
                "final_load": f"{result.heating_load_btu_hr:,.0f} BTU/hr",
                "final_tons": f"{result.heating_tons:.1f} tons", 
                "base_load": f"{base_heating:,.0f} BTU/hr",
                "safety_factor": f"+{(heating_safety-1)*100:.0f}% (Zone {climate_data['climate_zone']})",
                "safety_btus": f"+{heating_safety_btus:,.0f} BTU/hr",
                "per_sqft": f"{result.heating_per_sqft:.1f} BTU/sq ft"
            },
            "cooling_analysis": {
                "final_load": f"{result.cooling_load_btu_hr:,.0f} BTU/hr", 
                "final_tons": f"{result.cooling_tons:.1f} tons",
                "base_load": f"{base_cooling:,.0f} BTU/hr",
                "safety_factor": f"+{(cooling_safety-1)*100:.0f}% (Zone {climate_data['climate_zone']})",
                "safety_btus": f"+{cooling_safety_btus:,.0f} BTU/hr",
                "per_sqft": f"{result.cooling_per_sqft:.1f} BTU/sq ft"
            },
            "calculation_method": "ACCA Manual J with climate-adaptive safety factors",
            "standards_compliance": ["ACCA Manual J 8th Edition", "IECC 2021", "ASHRAE Standards"]
        }
    
    def _generate_equipment_recommendations(self, result: Any) -> Dict[str, Any]:
        """Generate equipment sizing and model recommendations"""
        
        heating_tons = result.heating_tons
        cooling_tons = max(result.heating_tons, result.cooling_tons)  # Size for larger load
        
        # Find appropriate equipment models
        recommended_models = []
        for (min_tons, max_tons), models in self.heat_pump_models.items():
            if min_tons <= cooling_tons <= max_tons:
                recommended_models = models[:2]  # Top 2 recommendations
                break
        
        # Calculate backup heat requirements (typical for heat pumps)
        backup_heat_kw = min(20, max(10, heating_tons * 3))  # 3kW per ton, 10-20kW range
        
        return {
            "primary_system": {
                "type": "Heat Pump System",
                "recommended_size": f"{math.ceil(cooling_tons)} tons",
                "capacity_range": f"{cooling_tons * 12000:,.0f} BTU/hr",
                "popular_models": recommended_models,
                "system_type": "Cold-climate heat pump with backup heat"
            },
            "backup_heating": {
                "type": "Electric Resistance",
                "size": f"{backup_heat_kw:.0f}kW",
                "note": "Required for heat pump backup in cold climates"
            },
            "sizing_notes": [
                f"Sized for {cooling_tons:.1f} tons (larger of heating/cooling loads)",
                "Cold-climate models recommended for Zone 5B+ regions",
                "Backup heat ensures comfort during extreme cold"
            ]
        }
    
    def _generate_professional_insights(self, result: Any) -> Dict[str, Any]:
        """Generate professional insights and recommendations"""
        
        insights = []
        considerations = []
        
        # Analyze heating vs cooling ratio
        if result.heating_tons > result.cooling_tons * 1.5:
            insights.append("High heating load indicates potential insulation upgrades needed")
            considerations.append("Consider envelope improvements before equipment sizing")
        
        # Bonus room analysis
        if getattr(result, 'bonus_over_garage', False):
            insights.append("Bonus room over garage may need dedicated zone control")
            considerations.append("Zone dampers or separate unit may be required")
        
        # Confidence-based insights
        if result.confidence_score < 0.8:
            insights.append("Blueprint analysis confidence indicates site verification recommended")
            considerations.append("Field measurements may refine load calculations")
        
        # Large loads
        if result.heating_per_sqft > 40:
            insights.append("Higher than typical heating load per square foot")
            considerations.append("Review building envelope and insulation levels")
        
        return {
            "key_insights": insights,
            "installation_considerations": considerations,
            "climate_factors": [
                f"Zone {getattr(result, 'climate_zone', '5B')} requires cold-climate equipment",
                "Heating-dominated climate with significant cooling needs",
                "Ductwork location affects efficiency significantly"
            ],
            "next_steps": [
                "Verify field measurements for critical dimensions",
                "Consider duct design and zone control requirements", 
                "Evaluate existing electrical capacity for heat pump installation"
            ]
        }
    
    def _generate_industry_context(self, result: Any) -> Dict[str, Any]:
        """Generate industry benchmarking context"""
        
        heating_benchmark = self._benchmark_value(
            result.heating_per_sqft, 
            self.industry_ranges["heating_per_sqft"]
        )
        cooling_benchmark = self._benchmark_value(
            result.cooling_per_sqft,
            self.industry_ranges["cooling_per_sqft"] 
        )
        
        return {
            "heating_benchmark": {
                "your_value": f"{result.heating_per_sqft:.1f} BTU/sq ft",
                "industry_range": f"{self.industry_ranges['heating_per_sqft']['min']}-{self.industry_ranges['heating_per_sqft']['max']} BTU/sq ft",
                "status": heating_benchmark,
                "typical": f"{self.industry_ranges['heating_per_sqft']['typical']} BTU/sq ft"
            },
            "cooling_benchmark": {
                "your_value": f"{result.cooling_per_sqft:.1f} BTU/sq ft", 
                "industry_range": f"{self.industry_ranges['cooling_per_sqft']['min']}-{self.industry_ranges['cooling_per_sqft']['max']} BTU/sq ft",
                "status": cooling_benchmark,
                "typical": f"{self.industry_ranges['cooling_per_sqft']['typical']} BTU/sq ft"
            }
        }
    
    def _generate_subtle_upgrade_hooks(self, result: Any) -> Dict[str, Any]:
        """Generate subtle upgrade benefits for free users (not pushy)"""
        
        return {
            "additional_analysis_available": [
                "Room-by-room load breakdown",
                "Complete duct sizing calculations",
                "Zone control system design",
                "Equipment specification sheets"
            ],
            "professional_features": [
                "ACCA Manual J compliance reports",
                "Installation cost estimates", 
                "Energy efficiency projections"
            ],
            "note": "Professional contractors use detailed analysis for accurate installations"
        }
    
    def _generate_premium_sections(self, result: Any) -> Dict[str, Any]:
        """Generate premium content for paid users"""
        
        return {
            "room_by_room_loads": "Available in detailed zone analysis",
            "duct_sizing": "Complete CFM calculations per room",
            "compliance_documentation": "Full ACCA Manual J documentation",
            "installation_guide": "Step-by-step installation considerations",
            "energy_projections": "Annual operating cost estimates"
        }
    
    def _generate_share_features(self, result: Any, report_context: str) -> Dict[str, Any]:
        """Generate viral sharing capabilities"""
        
        # Generate shareable report ID
        report_id = str(uuid.uuid4())[:8]
        
        share_data = {
            "shareable_url": f"https://autohvac.com/shared-report/{report_id}",
            "pdf_download": True,
            "social_preview": {
                "title": f"HVAC Load Calculation - {result.total_conditioned_area_sqft:,.0f} sq ft",
                "description": f"{result.heating_tons:.1f} ton heating, {result.cooling_tons:.1f} ton cooling - Professional analysis",
                "image_url": "https://autohvac.com/assets/report-preview.png"
            },
            "branding": {
                "generated_by": "AutoHVAC.com - Professional HVAC Load Calculations",
                "logo_url": "https://autohvac.com/assets/logo.png"
            }
        }
        
        # Context-specific features
        if report_context == "shared":
            share_data["viral_cta"] = {
                "headline": "Generate Your Own Professional HVAC Report",
                "description": "Get accurate load calculations for any building in minutes",
                "button_text": "Upload Your Blueprint",
                "link": "https://autohvac.com/upload"
            }
        
        return share_data
    
    def _generate_viral_elements(self, result: Any) -> Dict[str, Any]:
        """Generate viral growth elements for shared reports"""
        
        return {
            "credibility_indicators": [
                "ACCA Manual J Compliant",
                "Professional Engineering Analysis",
                "Climate-Adaptive Safety Factors",
                f"{result.confidence_score:.0%} Analysis Confidence"
            ],
            "call_to_action": {
                "primary": "Generate Your Own Professional HVAC Report",
                "secondary": "Upload your blueprint and get instant load calculations",
                "benefits": [
                    "Instant professional analysis",
                    "Climate-adaptive calculations", 
                    "Equipment recommendations",
                    "Industry-standard compliance"
                ]
            },
            "social_proof": {
                "message": "Trusted by HVAC professionals nationwide",
                "features": ["Professional contractors", "Engineers", "Building designers"]
            }
        }
    
    def _generate_metadata(self, result: Any, user_status: str, context: str) -> Dict[str, Any]:
        """Generate report metadata"""
        
        return {
            "report_id": str(uuid.uuid4())[:8],
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": "professional" if user_status == "paid" else "standard",
            "context": context,
            "version": "1.0",
            "standards": ["ACCA Manual J", "IECC 2021"],
            "disclaimer": "This report is generated by automated analysis. Professional verification recommended for critical applications."
        }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert confidence score to descriptive level"""
        if confidence >= 0.9:
            return "Very High"
        elif confidence >= 0.8:
            return "High" 
        elif confidence >= 0.7:
            return "Good"
        elif confidence >= 0.6:
            return "Moderate"
        else:
            return "Requires Verification"
    
    def _benchmark_value(self, value: float, range_dict: Dict[str, float]) -> str:
        """Compare value against industry range"""
        if value < range_dict["min"]:
            return "Below Typical"
        elif value > range_dict["max"]:
            return "Above Typical"
        else:
            return "Normal Range"