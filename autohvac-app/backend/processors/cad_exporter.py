import ezdxf
from pathlib import Path
from typing import Dict, Any, List, Union
import json
import math

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
    
    def export_dxf(
        self,
        blueprint_data: Dict[str, Any],
        hvac_layout: Dict[str, Any] = None,
        output_path: Path = None,
        layers: List[str] = None,
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
            if layers is None or layer_name in layers:
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
        if "hvac" in layers:
            if hvac_layout:
                await self._draw_hvac_systems(msp, hvac_layout, scale)
            elif "data" in blueprint_data:
                await self._draw_hvac_layout(msp, blueprint_data["data"], scale)
        
        # Add dimensions
        if "dimensions" in layers and "data" in blueprint_data:
            await self._add_dimensions(msp, blueprint_data["data"], scale)
        
        # Add labels
        if "labels" in layers:
            if "rooms" in blueprint_data:
                await self._add_room_labels(msp, blueprint_data["rooms"], scale)
            elif "data" in blueprint_data:
                await self._add_labels(msp, blueprint_data["data"], scale)
        
        # Save document
        if output_path:
            doc.saveas(output_path)
        
        return doc
    
    async def _draw_hvac_systems(self, msp, hvac_layout: Dict[str, Any], scale: float):
        """
        Draw complete HVAC systems from layout data
        """
        if "systems" not in hvac_layout:
            return
            
        for system in hvac_layout["systems"]:
            if system["type"] == "ducted":
                await self._draw_ducted_system(msp, system, scale)
            elif system["type"] == "ductless":
                await self._draw_ductless_system(msp, system, scale)
    
    async def _draw_ducted_system(self, msp, system: Dict[str, Any], scale: float):
        """
        Draw ducted HVAC system with equipment, trunk, and branches
        """
        # Draw main equipment
        eq_loc = system["location"]
        eq_x, eq_y = eq_loc["x"] * scale, eq_loc["y"] * scale
        equipment_size = 48 * scale  # 4 feet equipment
        
        # Equipment rectangle
        msp.add_lwpolyline(
            [
                (eq_x, eq_y),
                (eq_x + equipment_size, eq_y),
                (eq_x + equipment_size, eq_y + equipment_size * 0.75),
                (eq_x, eq_y + equipment_size * 0.75),
                (eq_x, eq_y)
            ],
            dxfattribs={"layer": "EQUIPMENT", "closed": True}
        )
        
        # Equipment label
        capacity_tons = round(system["capacity"]["cooling"] / 12000, 1)
        msp.add_text(
            f"{capacity_tons}-TON {system.get('equipmentType', 'UNIT').upper()}",
            dxfattribs={
                "layer": "LABELS",
                "height": 6 * scale,
                "style": "STANDARD"
            }
        ).set_placement((eq_x + 10 * scale, eq_y - 10 * scale))
        
        # Draw main trunk
        if "mainTrunk" in system:
            trunk = system["mainTrunk"]
            start = (trunk["startPoint"]["x"] * scale, trunk["startPoint"]["y"] * scale)
            end = (trunk["endPoint"]["x"] * scale, trunk["endPoint"]["y"] * scale)
            
            # Draw trunk as thick line
            msp.add_line(start, end, dxfattribs={"layer": "DUCTS", "lineweight": 50})
            
            # Add trunk size label
            if "size" in trunk:
                size = trunk["size"]
                if "width" in size:
                    size_text = f"{size['width']}×{size['height']}\""
                else:
                    size_text = f"{size['diameter']}\" ⌀"
                
                mid_x = (start[0] + end[0]) / 2
                mid_y = (start[1] + end[1]) / 2
                msp.add_text(
                    size_text,
                    dxfattribs={"layer": "LABELS", "height": 4 * scale}
                ).set_placement((mid_x, mid_y + 5 * scale))
        
        # Draw branch ducts
        if "branches" in system:
            for branch in system["branches"]:
                start = (branch["startPoint"]["x"] * scale, branch["startPoint"]["y"] * scale)
                end = (branch["endPoint"]["x"] * scale, branch["endPoint"]["y"] * scale)
                
                # Draw branch line
                msp.add_line(start, end, dxfattribs={"layer": "DUCTS"})
                
                # Add register symbol at end
                msp.add_circle(end, radius=6 * scale, dxfattribs={"layer": "HVAC"})
                
                # Add branch size if available
                if "size" in branch and "diameter" in branch["size"]:
                    size_text = f"{branch['size']['diameter']}\""
                    msp.add_text(
                        size_text,
                        dxfattribs={"layer": "LABELS", "height": 3 * scale}
                    ).set_placement((end[0] + 8 * scale, end[1]))
        
        # Draw return ducts
        if "returns" in system:
            for return_duct in system["returns"]:
                loc = return_duct["location"]
                ret_x, ret_y = loc["x"] * scale, loc["y"] * scale
                
                # Draw return grille as rectangle
                size = return_duct["size"]
                width = size["width"] * scale / 12  # Convert to feet
                height = size["height"] * scale / 12
                
                msp.add_lwpolyline(
                    [
                        (ret_x, ret_y),
                        (ret_x + width, ret_y),
                        (ret_x + width, ret_y + height),
                        (ret_x, ret_y + height),
                        (ret_x, ret_y)
                    ],
                    dxfattribs={"layer": "HVAC", "closed": True}
                )
                
                # Add "R" label for return
                msp.add_text(
                    "R",
                    dxfattribs={"layer": "LABELS", "height": 8 * scale}
                ).set_placement((ret_x + width/2, ret_y + height/2))
    
    async def _draw_ductless_system(self, msp, system: Dict[str, Any], scale: float):
        """
        Draw ductless HVAC system with outdoor unit, indoor units, and linesets
        """
        # Draw outdoor unit
        if "outdoorUnit" in system:
            outdoor = system["outdoorUnit"]
            ou_x, ou_y = outdoor["location"]["x"] * scale, outdoor["location"]["y"] * scale
            ou_size = 36 * scale  # 3 feet outdoor unit
            
            # Outdoor unit rectangle
            msp.add_lwpolyline(
                [
                    (ou_x, ou_y),
                    (ou_x + ou_size, ou_y),
                    (ou_x + ou_size, ou_y + ou_size),
                    (ou_x, ou_y + ou_size),
                    (ou_x, ou_y)
                ],
                dxfattribs={"layer": "EQUIPMENT", "closed": True}
            )
            
            # Outdoor unit label
            capacity_tons = round(outdoor["capacity"] / 12000, 1)
            msp.add_text(
                f"{capacity_tons}T ODU",
                dxfattribs={"layer": "LABELS", "height": 6 * scale}
            ).set_placement((ou_x + 5 * scale, ou_y + ou_size + 5 * scale))
        
        # Draw indoor units
        if "indoorUnits" in system:
            for unit in system["indoorUnits"]:
                iu_x, iu_y = unit["location"]["x"] * scale, unit["location"]["y"] * scale
                unit_type = unit["type"]
                
                if unit_type == "wall_mount":
                    # Wall mount unit as small rectangle
                    msp.add_lwpolyline(
                        [
                            (iu_x, iu_y),
                            (iu_x + 30 * scale, iu_y),
                            (iu_x + 30 * scale, iu_y + 8 * scale),
                            (iu_x, iu_y + 8 * scale),
                            (iu_x, iu_y)
                        ],
                        dxfattribs={"layer": "HVAC", "closed": True}
                    )
                elif unit_type == "ceiling_cassette":
                    # Ceiling cassette as square
                    msp.add_lwpolyline(
                        [
                            (iu_x, iu_y),
                            (iu_x + 24 * scale, iu_y),
                            (iu_x + 24 * scale, iu_y + 24 * scale),
                            (iu_x, iu_y + 24 * scale),
                            (iu_x, iu_y)
                        ],
                        dxfattribs={"layer": "HVAC", "closed": True}
                    )
                
                # Add capacity label
                capacity_k = round(unit["capacity"] / 1000)
                msp.add_text(
                    f"{capacity_k}K",
                    dxfattribs={"layer": "LABELS", "height": 4 * scale}
                ).set_placement((iu_x, iu_y - 6 * scale))
        
        # Draw linesets
        if "linesets" in system:
            for lineset in system["linesets"]:
                path = lineset["path"]
                
                # Draw lineset path as polyline
                points = [(p["x"] * scale, p["y"] * scale) for p in path]
                msp.add_lwpolyline(
                    points,
                    dxfattribs={"layer": "DUCTS", "lineweight": 25}
                )
                
                # Add lineset size labels
                liquid_size = lineset["liquidLine"]
                suction_size = lineset["suctionLine"]
                
                # Place label at midpoint
                if len(points) >= 2:
                    mid_x = (points[0][0] + points[-1][0]) / 2
                    mid_y = (points[0][1] + points[-1][1]) / 2
                    
                    msp.add_text(
                        f"{liquid_size}\" / {suction_size}\"",
                        dxfattribs={"layer": "LABELS", "height": 3 * scale}
                    ).set_placement((mid_x, mid_y + 3 * scale))
    
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
    
    async def _add_room_labels(self, msp, rooms: List[Dict[str, Any]], scale: float):
        """
        Add room labels from parsed room data
        """
        for i, room in enumerate(rooms):
            if "name" in room:
                # Position labels in a grid pattern for visualization
                x = (i % 5) * 100 * scale + 50 * scale
                y = (i // 5) * 80 * scale + 50 * scale
                
                msp.add_text(
                    f"{room['name'].upper()}\n{room['area']} SF",
                    dxfattribs={
                        "layer": "LABELS",
                        "height": 6 * scale,
                        "style": "STANDARD"
                    }
                ).set_placement((x, y))
    
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
    
    def export_svg(
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