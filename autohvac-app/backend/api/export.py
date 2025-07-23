from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any, List
from pydantic import BaseModel
from pathlib import Path
import uuid

try:
    from processors.cad_exporter import CADExporter
except ImportError:
    from processors.cad_exporter_simple import CADExporter

router = APIRouter()

# Initialize exporter
cad_exporter = CADExporter()

# Export directory
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

class ExportRequest(BaseModel):
    job_id: str
    format: str  # "dxf", "dwg", "svg", "pdf"
    include_layers: List[str] = ["walls", "hvac", "dimensions", "labels"]
    scale: float = 1.0
    units: str = "inches"

@router.post("/generate")
async def generate_export(request: ExportRequest) -> Dict[str, Any]:
    """
    Generate CAD export file from processed blueprint and HVAC design
    """
    try:
        # Validate format
        supported_formats = ["dxf", "svg", "pdf"]
        if request.format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Choose from: {supported_formats}"
            )
        
        # Check if analysis exists
        processed_file = Path("processed") / f"{request.job_id}.json"
        if not processed_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Blueprint analysis not found. Process blueprint first."
            )
        
        # Load processed data
        import json
        with open(processed_file, "r") as f:
            blueprint_data = json.load(f)
        
        # Generate export
        export_id = str(uuid.uuid4())
        output_file = EXPORT_DIR / f"{export_id}.{request.format}"
        
        # Export based on format
        if request.format == "dxf":
            await cad_exporter.export_dxf(
                blueprint_data,
                output_file,
                layers=request.include_layers,
                scale=request.scale,
                units=request.units
            )
        elif request.format == "svg":
            await cad_exporter.export_svg(
                blueprint_data,
                output_file,
                layers=request.include_layers,
                scale=request.scale
            )
        elif request.format == "pdf":
            await cad_exporter.export_pdf(
                blueprint_data,
                output_file,
                include_calculations=True
            )
        
        return {
            "export_id": export_id,
            "format": request.format,
            "file_size": output_file.stat().st_size,
            "download_url": f"/api/export/download/{export_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{export_id}")
async def download_export(export_id: str):
    """
    Download exported file
    """
    # Find export file
    export_files = list(EXPORT_DIR.glob(f"{export_id}.*"))
    
    if not export_files:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    file_path = export_files[0]
    
    return FileResponse(
        path=file_path,
        filename=f"autohvac_export_{export_id}{file_path.suffix}",
        media_type="application/octet-stream"
    )

@router.get("/formats")
async def get_export_formats() -> Dict[str, Any]:
    """
    Get available export formats and their capabilities
    """
    return {
        "formats": {
            "dxf": {
                "name": "AutoCAD DXF",
                "description": "Industry standard CAD format",
                "supports_layers": True,
                "supports_dimensions": True,
                "recommended_for": ["Contractors", "Engineers", "Permit submission"]
            },
            "svg": {
                "name": "Scalable Vector Graphics",
                "description": "Web-friendly vector format",
                "supports_layers": True,
                "supports_dimensions": False,
                "recommended_for": ["Web viewing", "Reports", "Presentations"]
            },
            "pdf": {
                "name": "PDF Report",
                "description": "Complete report with calculations",
                "supports_layers": False,
                "supports_dimensions": True,
                "recommended_for": ["Clients", "Documentation", "Permits"]
            }
        }
    }