import ezdxf
from pathlib import Path
from typing import Dict, Any, List
import json

class CADExporter:
    """
    Export HVAC designs to various CAD formats
    """
    
    def __init__(self):
        self.layer_config = {
            "walls": {"color": 7, "lineweight": 50},  # White
            "hvac": {"color": 1, "lineweight": 30},   # Red
            "ducts": {"color": 4, "lineweight": 25},  # Cyan
            "equipment": {"color": 2, "lineweight": 35}, # Yellow
            "dimensions": {"color": 3, "lineweight": 13}, # Green
            "labels": {"color": 7, "lineweight": 13}  # White
        }
    
    async def export_dxf(
        self,
        blueprint_data: Dict[str, Any],
        output_path: Path,
        layers: List[str],
        scale: float = 1.0,
        units: str = "inches"
    ):
        """
        Export design to DXF format
        """
        # Create new DXF document
        doc = ezdxf.new("R2018")
        doc.units = ezdxf.units.IN if units == "inches" else ezdxf.units.MM
        
        # Set up layers
        for layer_name, config in self.layer_config.items():
            if layer_name in layers:
                doc.layers.add(
                    name=layer_name.upper(),
                    color=config["color"],
                    lineweight=config["lineweight"]
                )
        
        # Get modelspace
        msp = doc.modelspace()
        
        # Draw walls if available
        if "walls" in layers and "data" in blueprint_data:
            await self._draw_walls(msp, blueprint_data["data"], scale)
        
        # Draw HVAC components
        if "hvac" in layers and "data" in blueprint_data:
            await self._draw_hvac_layout(msp, blueprint_data["data"], scale)
        
        # Add dimensions
        if "dimensions" in layers:
            await self._add_dimensions(msp, blueprint_data["data"], scale)
        
        # Add labels
        if "labels" in layers:
            await self._add_labels(msp, blueprint_data["data"], scale)
        
        # Save document
        doc.saveas(output_path)
    
    async def _draw_walls(self, msp, data: Dict[str, Any], scale: float):
        """
        Draw walls in modelspace
        """
        # Draw building outline
        if "dimensions" in data:
            bbox = data["dimensions"].get("bounding_box", {})
            if bbox:
                # Draw rectangle for building outline
                points = [
                    (bbox["x"] * scale, bbox["y"] * scale),
                    ((bbox["x"] + bbox["w"]) * scale, bbox["y"] * scale),
                    ((bbox["x"] + bbox["w"]) * scale, (bbox["y"] + bbox["h"]) * scale),
                    (bbox["x"] * scale, (bbox["y"] + bbox["h"]) * scale),
                    (bbox["x"] * scale, bbox["y"] * scale)  # Close polygon
                ]
                
                msp.add_lwpolyline(
                    points,
                    dxfattribs={"layer": "WALLS", "closed": True}
                )
        
        # Draw room divisions (simplified)
        if "rooms" in data:
            for room in data["rooms"]:
                if "boundary" in room:
                    # This would draw actual room boundaries
                    pass
    
    async def _draw_hvac_layout(self, msp, data: Dict[str, Any], scale: float):
        """
        Draw HVAC equipment and ductwork
        """
        # Draw equipment location (simplified example)
        equipment_x, equipment_y = 100 * scale, 100 * scale
        equipment_size = 48 * scale  # 48 inch unit
        
        # Draw furnace/air handler as rectangle
        msp.add_lwpolyline(
            [
                (equipment_x, equipment_y),
                (equipment_x + equipment_size, equipment_y),
                (equipment_x + equipment_size, equipment_y + equipment_size * 0.75),
                (equipment_x, equipment_y + equipment_size * 0.75),
                (equipment_x, equipment_y)
            ],
            dxfattribs={"layer": "EQUIPMENT", "closed": True}
        )
        
        # Add equipment label
        msp.add_text(
            "3-TON AC/FURNACE",
            dxfattribs={
                "layer": "LABELS",
                "height": 6 * scale,
                "style": "STANDARD"
            }
        ).set_placement((equipment_x + 10 * scale, equipment_y - 10 * scale))
        
        # Draw main trunk duct (example)
        trunk_start = (equipment_x + equipment_size, equipment_y + equipment_size * 0.375)
        trunk_end = (equipment_x + 200 * scale, equipment_y + equipment_size * 0.375)
        
        msp.add_line(
            trunk_start,
            trunk_end,
            dxfattribs={"layer": "DUCTS", "lineweight": 50}
        )
        
        # Draw branch ducts to rooms
        if "rooms" in data:
            for i, room in enumerate(data["rooms"][:3]):  # Example: first 3 rooms
                branch_start = (
                    trunk_start[0] + (50 + i * 50) * scale,
                    trunk_start[1]
                )
                branch_end = (
                    branch_start[0],
                    branch_start[1] + 100 * scale
                )
                
                msp.add_line(
                    branch_start,
                    branch_end,
                    dxfattribs={"layer": "DUCTS"}
                )
                
                # Add register symbol at end
                msp.add_circle(
                    branch_end,
                    radius=6 * scale,
                    dxfattribs={"layer": "HVAC"}
                )
    
    async def _add_dimensions(self, msp, data: Dict[str, Any], scale: float):
        """
        Add dimension annotations
        """
        if "dimensions" in data:
            dim = data["dimensions"]
            
            # Add overall building dimensions
            if "width" in dim and "height" in dim:
                # Horizontal dimension
                msp.add_aligned_dim(
                    p1=(0, -20 * scale),
                    p2=(dim["width"], -20 * scale),
                    distance=10 * scale,
                    dimstyle="EZDXF",
                    dxfattribs={"layer": "DIMENSIONS"}
                )
                
                # Vertical dimension
                msp.add_aligned_dim(
                    p1=(-20 * scale, 0),
                    p2=(-20 * scale, dim["height"]),
                    distance=10 * scale,
                    dimstyle="EZDXF",
                    dxfattribs={"layer": "DIMENSIONS"}
                )
    
    async def _add_labels(self, msp, data: Dict[str, Any], scale: float):
        """
        Add room labels and annotations
        """
        if "rooms" in data:
            for room in data["rooms"]:
                if "name" in room and "center" in room:
                    msp.add_text(
                        room["name"].upper(),
                        dxfattribs={
                            "layer": "LABELS",
                            "height": 8 * scale,
                            "style": "STANDARD"
                        }
                    ).set_placement(
                        (room["center"][0] * scale, room["center"][1] * scale),
                        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
                    )
    
    async def export_svg(
        self,
        blueprint_data: Dict[str, Any],
        output_path: Path,
        layers: List[str],
        scale: float = 1.0
    ):
        """
        Export design to SVG format for web viewing
        """
        # This would create an SVG representation
        # Placeholder for now
        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="700" height="500" fill="none" stroke="black" stroke-width="2"/>
    <text x="400" y="30" text-anchor="middle" font-size="24">HVAC Layout - Job {blueprint_data.get('job_id', 'Unknown')}</text>
</svg>"""
        
        with open(output_path, "w") as f:
            f.write(svg_content)
    
    async def export_pdf(
        self,
        blueprint_data: Dict[str, Any],
        output_path: Path,
        include_calculations: bool = True
    ):
        """
        Export complete PDF report with layout and calculations
        """
        # This would generate a PDF report
        # For now, create a simple JSON summary
        report_data = {
            "project_id": blueprint_data.get("job_id"),
            "timestamp": blueprint_data.get("timestamp"),
            "summary": {
                "total_area": blueprint_data.get("data", {}).get("total_area", 0),
                "num_rooms": blueprint_data.get("data", {}).get("num_rooms", 0),
                "recommended_tonnage": 3.0,
                "duct_design": "Trunk and branch system"
            },
            "calculations_included": include_calculations
        }
        
        # Save as JSON for now (would be PDF in production)
        with open(output_path.with_suffix(".json"), "w") as f:
            json.dump(report_data, f, indent=2)