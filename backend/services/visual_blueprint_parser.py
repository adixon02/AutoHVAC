"""
Visual Blueprint Parser - Simple, Accurate, Human-like Approach
Treats blueprints as visual documents, not structured data
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import fitz  # PyMuPDF for rendering
import cv2

# Import our existing working components
from services.ocr_extractor import OCRExtractor
from services.scale_extractor import scale_extractor
from services.page_classifier import page_classifier

logger = logging.getLogger(__name__)


@dataclass
class VisualRoom:
    """Room detected visually from blueprint"""
    name: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2 in pixels
    area_pixels: float
    area_sqft: float
    confidence: float
    center: Tuple[int, int]


class VisualBlueprintParser:
    """
    Parse blueprints the way humans do - visually!
    Much simpler and more accurate than complex PDF structure parsing.
    """
    
    def __init__(self):
        self.ocr = OCRExtractor(use_gpu=False)
        self.render_dpi = 150  # Good balance of quality and speed
        
    def parse_blueprint(
        self,
        pdf_path: str,
        page_num: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - parse blueprint visually
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to parse (None = auto-detect floor plan)
            
        Returns:
            Dictionary with rooms, scale, and metadata
        """
        start_time = time.time()
        
        # Step 1: Find the floor plan page if not specified
        if page_num is None:
            logger.info("Auto-detecting floor plan page...")
            page_num = page_classifier.find_best_floor_plan_page(pdf_path)
            if page_num is None:
                page_num = 0  # Default to first page
                logger.warning("No floor plan detected, using first page")
            else:
                logger.info(f"Found floor plan on page {page_num + 1}")
        
        # Step 2: Render page to image
        logger.info(f"Rendering page {page_num + 1} to image at {self.render_dpi} DPI...")
        image = self._render_page_to_image(pdf_path, page_num)
        logger.info(f"Rendered image size: {image.shape[1]}x{image.shape[0]}")
        
        # Step 3: Extract text via OCR
        logger.info("Extracting text via OCR...")
        text_regions = self.ocr.extract_all_text(image)
        all_text = " ".join([r.text for r in text_regions])
        logger.info(f"Extracted {len(text_regions)} text regions")
        
        # Step 4: Extract scale
        logger.info("Detecting scale from text...")
        scale_result = scale_extractor.extract_scale(all_text, page_num)
        pixels_per_foot = scale_result.pixels_per_foot * (self.render_dpi / 72.0)  # Adjust for render DPI
        logger.info(f"Scale: {scale_result.scale_notation} = {pixels_per_foot:.1f} pixels/foot at {self.render_dpi} DPI")
        
        # Step 5: Extract room labels
        room_labels = self._extract_room_labels(text_regions)
        logger.info(f"Found {len(room_labels)} room labels")
        
        # Step 6: Detect rooms visually
        logger.info("Detecting rooms visually...")
        rooms = self._detect_rooms_visually(image, room_labels, pixels_per_foot)
        logger.info(f"Detected {len(rooms)} rooms")
        
        # Step 7: Calculate total area
        total_sqft = sum(room.area_sqft for room in rooms)
        
        # Compile results
        result = {
            'success': True,
            'rooms': [
                {
                    'name': room.name,
                    'area_sqft': round(room.area_sqft, 1),
                    'bbox': room.bbox,
                    'confidence': room.confidence
                }
                for room in rooms
            ],
            'total_sqft': round(total_sqft, 0),
            'scale': {
                'notation': scale_result.scale_notation,
                'pixels_per_foot': pixels_per_foot,
                'confidence': scale_result.confidence
            },
            'metadata': {
                'page_number': page_num + 1,
                'image_size': (image.shape[1], image.shape[0]),
                'render_dpi': self.render_dpi,
                'processing_time': time.time() - start_time,
                'room_labels_found': len(room_labels),
                'rooms_detected': len(rooms)
            }
        }
        
        return result
    
    def _render_page_to_image(self, pdf_path: str, page_num: int) -> np.ndarray:
        """Render PDF page to numpy array image"""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at specified DPI
        mat = fitz.Matrix(self.render_dpi / 72.0, self.render_dpi / 72.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array
        img_data = pix.samples
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img_array = img_array.reshape(pix.height, pix.width, pix.n)
        
        # Convert to BGR for OpenCV
        if pix.n == 4:  # RGBA
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:  # RGB
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        doc.close()
        return img_array
    
    def _extract_room_labels(self, text_regions) -> List[Dict[str, Any]]:
        """Extract room labels from OCR text"""
        room_keywords = [
            'bedroom', 'bathroom', 'kitchen', 'living', 'dining',
            'closet', 'garage', 'entry', 'foyer', 'hallway',
            'master', 'guest', 'office', 'laundry', 'pantry',
            'family', 'great room', 'den', 'study', 'utility'
        ]
        
        room_labels = []
        for region in text_regions:
            text_lower = region.text.lower()
            for keyword in room_keywords:
                if keyword in text_lower:
                    # Get center of text region
                    bbox = region.bbox
                    if len(bbox) >= 4:
                        center_x = (bbox[0][0] + bbox[2][0]) / 2
                        center_y = (bbox[0][1] + bbox[2][1]) / 2
                    else:
                        center_x, center_y = 0, 0
                    
                    room_labels.append({
                        'text': region.text,
                        'type': keyword,
                        'center': (center_x, center_y),
                        'confidence': region.confidence
                    })
                    break
        
        return room_labels
    
    def _detect_rooms_visually(
        self,
        image: np.ndarray,
        room_labels: List[Dict],
        pixels_per_foot: float
    ) -> List[VisualRoom]:
        """
        Detect rooms using line detection to find walls
        Rooms in blueprints are spaces enclosed by walls (lines), not filled regions
        """
        rooms = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Edge detection + morphology to find closed regions
        # This works better for blueprints where rooms are defined by walls
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detect edges (walls)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to connect nearby lines (close gaps in walls)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Close gaps to form complete room boundaries
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Invert to get white rooms on black background
        inverted = cv2.bitwise_not(closed)
        
        # Find contours of enclosed spaces (rooms)
        contours, hierarchy = cv2.findContours(
            inverted,
            cv2.RETR_TREE,  # Get hierarchy to filter out nested contours
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter contours to find actual rooms
        min_room_area_pixels = (8 * pixels_per_foot) ** 2   # 8 sq ft minimum (closets)
        max_room_area_pixels = (1000 * pixels_per_foot) ** 2  # 1000 sq ft maximum
        min_room_width = 3 * pixels_per_foot  # Minimum 3 feet width
        
        # Track which contours are rooms to avoid duplicates
        room_contours = []
        
        for i, contour in enumerate(contours):
            area_pixels = cv2.contourArea(contour)
            
            # Skip if area is outside reasonable range
            if not (min_room_area_pixels <= area_pixels <= max_room_area_pixels):
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Skip if too narrow (likely a hallway or artifact)
            if w < min_room_width or h < min_room_width:
                continue
            
            # Skip if aspect ratio is extreme (likely a corridor)
            aspect_ratio = max(w, h) / min(w, h)
            if aspect_ratio > 5:  # Too elongated
                continue
            
            # Check if this contour is inside another (using hierarchy)
            if hierarchy is not None and hierarchy[0][i][3] != -1:
                # Has a parent contour, might be a room inside the building outline
                parent_idx = hierarchy[0][i][3]
                parent_area = cv2.contourArea(contours[parent_idx])
                # Only skip if parent is much larger (building outline)
                if parent_area > area_pixels * 10:
                    continue
            
            room_contours.append((contour, area_pixels, (x, y, w, h)))
        
        # Sort by area to process larger rooms first
        room_contours.sort(key=lambda x: x[1], reverse=True)
        
        # Remove overlapping rooms (keep larger ones)
        final_rooms = []
        for contour, area_pixels, bbox in room_contours:
            x, y, w, h = bbox
            
            # Check if this room overlaps significantly with existing rooms
            overlaps = False
            for existing in final_rooms:
                ex, ey, ew, eh = existing[2]
                # Calculate intersection
                ix = max(x, ex)
                iy = max(y, ey)
                iw = min(x + w, ex + ew) - ix
                ih = min(y + h, ey + eh) - iy
                
                if iw > 0 and ih > 0:
                    intersection_area = iw * ih
                    # If intersection is more than 50% of smaller room, skip
                    smaller_area = min(w * h, ew * eh)
                    if intersection_area > smaller_area * 0.5:
                        overlaps = True
                        break
            
            if not overlaps:
                final_rooms.append((contour, area_pixels, (x, y, w, h)))
        
        # Convert to VisualRoom objects
        for contour, area_pixels, bbox in final_rooms:
            x, y, w, h = bbox
            
            # Calculate area in square feet
            area_sqft = area_pixels / (pixels_per_foot ** 2)
            
            # Find center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            
            # Match with room label if possible
            room_name = self._match_room_label(
                (cx, cy),
                room_labels,
                max_distance=pixels_per_foot * 5  # Within 5 feet
            )
            
            if not room_name:
                # Guess based on size and shape
                if area_sqft < 30:
                    room_name = "Closet"
                elif area_sqft < 60 and aspect_ratio < 2:
                    room_name = "Bathroom"
                elif area_sqft < 150:
                    room_name = "Bedroom"
                elif area_sqft < 250:
                    room_name = "Master Bedroom"
                else:
                    room_name = "Living Space"
            
            rooms.append(VisualRoom(
                name=room_name,
                bbox=(x, y, x + w, y + h),
                area_pixels=area_pixels,
                area_sqft=area_sqft,
                confidence=0.8,  # Higher confidence with better method
                center=(cx, cy)
            ))
        
        # If we still don't have enough rooms, try alternative parameters
        if len(rooms) < 3:
            logger.warning(f"Only found {len(rooms)} rooms with edge detection")
            # Try with different edge detection parameters
            edges2 = cv2.Canny(blurred, 30, 100)  # Lower thresholds
            kernel2 = np.ones((5, 5), np.uint8)
            dilated2 = cv2.dilate(edges2, kernel2, iterations=3)  # More dilation
            closed2 = cv2.morphologyEx(dilated2, cv2.MORPH_CLOSE, kernel2, iterations=3)
            inverted2 = cv2.bitwise_not(closed2)
            
            contours2, _ = cv2.findContours(inverted2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours2:
                area_pixels = cv2.contourArea(contour)
                if min_room_area_pixels <= area_pixels <= max_room_area_pixels:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Check if this is a new room not already found
                    is_new = True
                    for existing_room in rooms:
                        ex1, ey1, ex2, ey2 = existing_room.bbox
                        if abs(x - ex1) < 50 and abs(y - ey1) < 50:
                            is_new = False
                            break
                    
                    if is_new and w >= min_room_width and h >= min_room_width:
                        area_sqft = area_pixels / (pixels_per_foot ** 2)
                        rooms.append(VisualRoom(
                            name=f"Room {len(rooms) + 1}",
                            bbox=(x, y, x + w, y + h),
                            area_pixels=area_pixels,
                            area_sqft=area_sqft,
                            confidence=0.6,  # Lower confidence for fallback
                            center=(x + w // 2, y + h // 2)
                        ))
        
        logger.info(f"Detected {len(rooms)} rooms using edge-based detection")
        return rooms
    
    def _match_room_label(
        self,
        room_center: Tuple[int, int],
        room_labels: List[Dict],
        max_distance: float
    ) -> Optional[str]:
        """Match a room to its closest label"""
        best_label = None
        best_distance = max_distance
        
        for label in room_labels:
            label_center = label['center']
            distance = np.sqrt(
                (room_center[0] - label_center[0]) ** 2 +
                (room_center[1] - label_center[1]) ** 2
            )
            
            if distance < best_distance:
                best_distance = distance
                best_label = label['text']
        
        return best_label


# Global instance
visual_parser = VisualBlueprintParser()