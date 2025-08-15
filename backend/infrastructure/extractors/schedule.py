"""
Schedule Extractor - Pulls window, door, and room finish schedules from blueprints
These schedules contain critical Manual J data like U-values, SHGC, sizes
"""

import logging
import re
import fitz
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowSpec:
    """Window specification from schedule"""
    mark: str  # Window ID (W1, W2, etc)
    width_ft: float
    height_ft: float
    quantity: int
    type: str  # Double Hung, Casement, Fixed, etc
    glazing: str  # Double, Triple, Low-E
    u_value: Optional[float] = None
    shgc: Optional[float] = None
    frame: Optional[str] = None  # Vinyl, Wood, Aluminum


@dataclass
class DoorSpec:
    """Door specification from schedule"""
    mark: str  # Door ID (D1, D2, etc)
    width_ft: float
    height_ft: float
    type: str  # Exterior, Interior, Sliding
    material: str  # Steel, Wood, Fiberglass
    r_value: Optional[float] = None
    glazing_area: Optional[float] = None


class ScheduleExtractor:
    """
    Extracts window and door schedules from architectural drawings
    These are typically in tabular format on the blueprint sheets
    """
    
    def __init__(self):
        # Common schedule headers to look for
        self.schedule_keywords = [
            "WINDOW SCHEDULE",
            "DOOR SCHEDULE", 
            "ROOM FINISH SCHEDULE",
            "OPENING SCHEDULE",
            "FENESTRATION SCHEDULE"
        ]
        
        # Window type patterns
        self.window_types = {
            "DH": "Double Hung",
            "CSMT": "Casement",
            "FX": "Fixed",
            "SL": "Slider",
            "AW": "Awning"
        }
        
        # Default U-values by window type (ACCA defaults)
        self.default_u_values = {
            "single": 1.04,
            "double": 0.48,
            "double_low_e": 0.30,
            "triple": 0.20
        }
        
        # Default SHGC by glazing type
        self.default_shgc = {
            "clear": 0.76,
            "low_e": 0.30,
            "tinted": 0.45
        }
    
    def extract_schedules(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract all schedules from PDF
        
        Returns:
            {
                "windows": [WindowSpec, ...],
                "doors": [DoorSpec, ...],
                "has_schedules": bool,
                "total_window_area": float,
                "average_u_value": float,
                "average_shgc": float
            }
        """
        logger.info(f"Extracting schedules from {pdf_path}")
        
        doc = fitz.open(pdf_path)
        windows = []
        doors = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Check if this page has schedules
            if any(keyword in text.upper() for keyword in self.schedule_keywords):
                logger.info(f"Found schedule on page {page_num + 1}")
                
                # Extract window schedule
                window_specs = self._extract_window_schedule(text)
                windows.extend(window_specs)
                
                # Extract door schedule
                door_specs = self._extract_door_schedule(text)
                doors.extend(door_specs)
        
        doc.close()
        
        # Calculate aggregates
        total_window_area = sum(w.width_ft * w.height_ft * w.quantity for w in windows)
        
        if windows:
            avg_u = sum(w.u_value or 0.30 for w in windows) / len(windows)
            avg_shgc = sum(w.shgc or 0.30 for w in windows) / len(windows)
        else:
            avg_u = 0.30  # Default double low-E
            avg_shgc = 0.30
        
        logger.info(f"Extracted {len(windows)} window types, {len(doors)} door types")
        logger.info(f"Total window area: {total_window_area:.0f} sq ft")
        
        return {
            "windows": windows,
            "doors": doors,
            "has_schedules": len(windows) > 0 or len(doors) > 0,
            "total_window_area": total_window_area,
            "average_u_value": avg_u,
            "average_shgc": avg_shgc
        }
    
    def _extract_window_schedule(self, text: str) -> List[WindowSpec]:
        """Parse window schedule from text"""
        windows = []
        lines = text.split('\n')
        
        in_window_schedule = False
        for i, line in enumerate(lines):
            line_upper = line.upper()
            
            # Start of window schedule
            if "WINDOW SCHEDULE" in line_upper:
                in_window_schedule = True
                continue
            
            # End of window schedule
            if in_window_schedule and any(x in line_upper for x in ["DOOR SCHEDULE", "NOTES", "REMARKS"]):
                break
            
            if in_window_schedule:
                # Look for window entries (W1, W2, W-1, etc)
                window_pattern = r'(W[-\s]?\d+)\s+'
                match = re.search(window_pattern, line_upper)
                
                if match:
                    window = self._parse_window_line(line)
                    if window:
                        windows.append(window)
        
        return windows
    
    def _parse_window_line(self, line: str) -> Optional[WindowSpec]:
        """Parse a single window schedule line"""
        try:
            # Common patterns in window schedules
            # W1  3'-0" x 5'-0"  2  DH  DOUBLE LOW-E
            # W-2  36" x 60"  1  CSMT  DBL PANE
            
            # Extract mark
            mark_match = re.search(r'(W[-\s]?\d+)', line, re.IGNORECASE)
            if not mark_match:
                return None
            mark = mark_match.group(1).replace(' ', '')
            
            # Extract dimensions (various formats)
            dim_patterns = [
                r"(\d+)['\s]+(\d+)[\"']?\s*[xX]\s*(\d+)['\s]+(\d+)",  # 3'-6" x 5'-0"
                r"(\d+)['\s]*[xX]\s*(\d+)['\"']",  # 3' x 5'
                r"(\d+)[\"]\s*[xX]\s*(\d+)[\"]",  # 36" x 60"
            ]
            
            width_ft = 3.0  # Default
            height_ft = 5.0
            
            for pattern in dim_patterns:
                dim_match = re.search(pattern, line)
                if dim_match:
                    groups = dim_match.groups()
                    if len(groups) == 4:  # feet and inches
                        width_ft = float(groups[0]) + float(groups[1])/12
                        height_ft = float(groups[2]) + float(groups[3])/12
                    elif len(groups) == 2:
                        # Check if inches or feet
                        if '"' in dim_match.group():
                            width_ft = float(groups[0]) / 12
                            height_ft = float(groups[1]) / 12
                        else:
                            width_ft = float(groups[0])
                            height_ft = float(groups[1])
                    break
            
            # Extract quantity
            qty_match = re.search(r'\s+(\d+)\s+', line)
            quantity = int(qty_match.group(1)) if qty_match else 1
            
            # Determine glazing type and defaults
            line_upper = line.upper()
            if "TRIPLE" in line_upper:
                glazing = "Triple"
                u_value = 0.20
                shgc = 0.25
            elif "LOW-E" in line_upper or "LOW E" in line_upper:
                glazing = "Double Low-E"
                u_value = 0.30
                shgc = 0.30
            elif "DOUBLE" in line_upper or "DBL" in line_upper:
                glazing = "Double"
                u_value = 0.48
                shgc = 0.45
            else:
                glazing = "Double"  # Assume double as default
                u_value = 0.48
                shgc = 0.45
            
            # Extract U-value if specified
            u_match = re.search(r'U[\s=]+([0-9.]+)', line)
            if u_match:
                u_value = float(u_match.group(1))
            
            # Extract SHGC if specified
            shgc_match = re.search(r'SHGC[\s=]+([0-9.]+)', line)
            if shgc_match:
                shgc = float(shgc_match.group(1))
            
            # Determine window type
            window_type = "Fixed"  # Default
            for code, name in self.window_types.items():
                if code in line_upper:
                    window_type = name
                    break
            
            return WindowSpec(
                mark=mark,
                width_ft=width_ft,
                height_ft=height_ft,
                quantity=quantity,
                type=window_type,
                glazing=glazing,
                u_value=u_value,
                shgc=shgc
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse window line: {line} - {e}")
            return None
    
    def _extract_door_schedule(self, text: str) -> List[DoorSpec]:
        """Parse door schedule from text"""
        doors = []
        lines = text.split('\n')
        
        in_door_schedule = False
        for line in lines:
            line_upper = line.upper()
            
            if "DOOR SCHEDULE" in line_upper:
                in_door_schedule = True
                continue
            
            if in_door_schedule and any(x in line_upper for x in ["WINDOW SCHEDULE", "NOTES"]):
                break
            
            if in_door_schedule:
                door_pattern = r'(D[-\s]?\d+)\s+'
                match = re.search(door_pattern, line_upper)
                
                if match:
                    door = self._parse_door_line(line)
                    if door:
                        doors.append(door)
        
        return doors
    
    def _parse_door_line(self, line: str) -> Optional[DoorSpec]:
        """Parse a single door schedule line"""
        try:
            # Extract door mark
            mark_match = re.search(r'(D[-\s]?\d+)', line, re.IGNORECASE)
            if not mark_match:
                return None
            mark = mark_match.group(1).replace(' ', '')
            
            # Extract dimensions
            dim_match = re.search(r"(\d+)['\s]+(\d+).*[xX].*(\d+)['\s]+(\d+)", line)
            if dim_match:
                width_ft = float(dim_match.group(1)) + float(dim_match.group(2))/12
                height_ft = float(dim_match.group(3)) + float(dim_match.group(4))/12
            else:
                width_ft = 3.0  # Standard door width
                height_ft = 6.67  # Standard 6'-8" door
            
            # Determine door type
            line_upper = line.upper()
            if "EXT" in line_upper or "ENTRY" in line_upper:
                door_type = "Exterior"
                material = "Steel"
                r_value = 5.0  # Insulated steel door
            elif "SLIDING" in line_upper or "PATIO" in line_upper:
                door_type = "Sliding"
                material = "Glass"
                r_value = 2.0
            else:
                door_type = "Interior"
                material = "Wood"
                r_value = 2.0
            
            return DoorSpec(
                mark=mark,
                width_ft=width_ft,
                height_ft=height_ft,
                type=door_type,
                material=material,
                r_value=r_value
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse door line: {line} - {e}")
            return None


# Module instance
_schedule_extractor = None

def get_schedule_extractor():
    global _schedule_extractor
    if _schedule_extractor is None:
        _schedule_extractor = ScheduleExtractor()
    return _schedule_extractor