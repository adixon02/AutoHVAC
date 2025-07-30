import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from fastapi import HTTPException
from services.s3_storage import storage_service

try:
    import pdfkit
except ModuleNotFoundError:  # local dev without wkhtmltopdf
    pdfkit = None

# Skip PDF generation entirely in local dev if requested
PDF_DISABLED = os.getenv("DISABLE_PDF", "false").lower() == "true"

logger = logging.getLogger(__name__)

class PDFGenerationService:
    """Service for generating PDF reports from job results"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'html_templates')
        self.wkhtmltopdf_path = os.getenv('WKHTMLTOPDF_PATH', '/usr/local/bin/wkhtmltopdf')
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )
        
        # Add custom filters
        self.jinja_env.filters['number_format'] = self._number_format
        
        # PDF generation options
        self.pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None,
        }
    
    def _number_format(self, value):
        """Format numbers with commas"""
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)
    
    def generate_report_pdf(
        self,
        project_id: str,
        project_label: str,
        filename: str,
        job_result: Dict[str, Any]
    ) -> str:
        """
        Generate PDF report from job results
        
        Args:
            project_id: Unique project identifier
            project_label: User-friendly project name
            filename: Original blueprint filename
            job_result: Processed job results
            
        Returns:
            str: Path to generated PDF file
        """
        try:
            # Extract data from job result
            rooms = job_result.get('rooms', [])
            loads = job_result.get('loads', {})
            processing_info = job_result.get('processing_info', {})
            
            # Calculate totals and recommendations
            total_heating_btu = loads.get('total_heating_btu', 0)
            total_cooling_btu = loads.get('total_cooling_btu', 0)
            total_area = sum(room.get('area', 0) for room in rooms)
            
            # Calculate equipment recommendations
            recommended_heating_tons = round(total_heating_btu / 12000, 1)
            recommended_cooling_tons = round(total_cooling_btu / 12000, 1)
            recommended_heating_btu = int(recommended_heating_tons * 12000)
            recommended_cooling_btu = int(recommended_cooling_tons * 12000)
            recommended_cfm = int(total_cooling_btu / 400)  # Rough CFM calculation
            
            # Determine system type based on load
            if total_cooling_btu > 60000:  # > 5 tons
                recommended_system_type = "Commercial Packaged Unit"
            elif total_cooling_btu > 36000:  # > 3 tons
                recommended_system_type = "Central Air with Gas Furnace"
            else:
                recommended_system_type = "Heat Pump System"
            
            # Prepare template context
            context = {
                'project_id': project_id,
                'project_label': project_label,
                'filename': filename,
                'analysis_date': datetime.now().strftime('%B %d, %Y'),
                'generation_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                
                # Load summary
                'total_heating_btu': total_heating_btu,
                'total_cooling_btu': total_cooling_btu,
                'total_area': total_area,
                
                # Room data
                'rooms': rooms,
                
                # Equipment recommendations
                'recommended_heating_tons': recommended_heating_tons,
                'recommended_cooling_tons': recommended_cooling_tons,
                'recommended_heating_btu': recommended_heating_btu,
                'recommended_cooling_btu': recommended_cooling_btu,
                'recommended_system_type': recommended_system_type,
                'recommended_cfm': recommended_cfm,
                
                # Analysis details
                'climate_zone': 'Determined from project location',
                'equipment_notes': self._generate_equipment_notes(total_cooling_btu, rooms),
            }
            
            # Render HTML template
            template = self.jinja_env.get_template('report.html')
            html_content = template.render(**context)
            
            # Generate PDF to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name
            
            try:
                # Generate PDF to temp file
                temp_pdf_path = temp_html_path.replace('.html', '.pdf')
                self._generate_pdf(html_content, temp_pdf_path)
                
                # Read the PDF content
                with open(temp_pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                # Save using storage service
                relative_path = storage_service.save_report(project_id, pdf_content)
                
                logger.info(f"Generated PDF report for project {project_id}")
                return relative_path
            finally:
                # Clean up temp files
                if os.path.exists(temp_html_path):
                    os.unlink(temp_html_path)
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
            
        except Exception as e:
            logger.error(f"Error generating PDF report for project {project_id}: {str(e)}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        import re
        # Remove or replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces with underscores
        safe_name = safe_name.strip('._')  # Remove leading/trailing dots and underscores
        return safe_name[:50]  # Limit length
    
    def _generate_pdf(self, html: str, output_path: str) -> None:
        """Generate PDF from HTML with graceful error handling"""
        if PDF_DISABLED:
            # dev stub — just write HTML so the rest of pipeline continues
            with open(output_path.replace(".pdf", ".html"), "w") as f:
                f.write(html)
            return
        if not pdfkit:
            raise HTTPException(
                status_code=503,
                detail="pdfkit / wkhtmltopdf missing — install wkhtmltopdf or set DISABLE_PDF=true",
            )
        config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
        pdfkit.from_string(html, output_path, options=self.pdf_options, configuration=config)
    
    def _generate_equipment_notes(self, total_cooling_btu: int, rooms: list) -> str:
        """Generate equipment-specific notes based on analysis"""
        notes = []
        
        # System sizing notes
        if total_cooling_btu < 18000:
            notes.append("Consider a single-zone system for optimal efficiency.")
        elif total_cooling_btu > 60000:
            notes.append("Multi-zone or commercial system recommended for optimal comfort.")
        
        # Room-specific notes
        large_rooms = [room for room in rooms if room.get('area', 0) > 400]
        if large_rooms:
            notes.append("Large rooms may benefit from multiple supply vents for even air distribution.")
        
        # Load density notes
        avg_load_density = total_cooling_btu / sum(room.get('area', 0) for room in rooms) if rooms else 0
        if avg_load_density > 25:
            notes.append("High load density detected - verify insulation and window specifications.")
        
        return " ".join(notes) if notes else "Standard residential HVAC system recommended."
    
    def delete_report(self, project_id: str) -> bool:
        """Delete a PDF report file"""
        try:
            report_path = storage_service.get_report_path(project_id)
            if os.path.exists(report_path):
                os.remove(report_path)
                logger.info(f"Deleted PDF report for project {project_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting PDF report for project {project_id}: {str(e)}")
            return False

# Global instance
pdf_service = PDFGenerationService()