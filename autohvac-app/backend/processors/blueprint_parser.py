import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image
import pdf2image

class BlueprintParser:
    """
    Parse blueprint files and extract structural information
    """
    
    def __init__(self):
        self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg", ".dwg", ".dxf"]
    
    async def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse blueprint file and extract key information
        """
        file_ext = file_path.suffix.lower()
        
        if file_ext == ".pdf":
            image = await self._pdf_to_image(file_path)
        elif file_ext in [".png", ".jpg", ".jpeg"]:
            image = cv2.imread(str(file_path))
        elif file_ext in [".dwg", ".dxf"]:
            # For now, we'll need specialized libraries for CAD files
            raise NotImplementedError(f"CAD file parsing coming soon")
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Extract features
        preprocessed = await self._preprocess_image(image)
        walls = await self._detect_walls(preprocessed)
        dimensions = await self._extract_dimensions(preprocessed)
        text_elements = await self._extract_text(image)
        
        return {
            "dimensions": dimensions,
            "walls": walls,
            "text_elements": text_elements,
            "image_shape": image.shape[:2],
            "metadata": {
                "file_type": file_ext,
                "file_name": file_path.name
            }
        }
    
    async def _pdf_to_image(self, pdf_path: Path) -> np.ndarray:
        """
        Convert PDF to image
        """
        images = pdf2image.convert_from_path(pdf_path, dpi=300)
        # Use first page for now
        image = np.array(images[0])
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    async def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess blueprint image for analysis
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Binary threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    async def _detect_walls(self, binary_image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect walls using line detection
        """
        walls = []
        
        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            binary_image,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=50,
            maxLineGap=10
        )
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # Classify as horizontal or vertical
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                orientation = "horizontal" if angle < 45 or angle > 135 else "vertical"
                
                walls.append({
                    "start": (x1, y1),
                    "end": (x2, y2),
                    "orientation": orientation,
                    "length": np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                })
        
        return walls
    
    async def _extract_dimensions(self, image: np.ndarray) -> Dict[str, float]:
        """
        Extract building dimensions from blueprint
        """
        # Find contours
        contours, _ = cv2.findContours(
            image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return {"width": 0, "height": 0, "scale": 1.0}
        
        # Find largest contour (building outline)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Estimate scale (this would need calibration with known dimensions)
        # For now, assume 1 pixel = 0.25 inches
        scale = 0.25
        
        return {
            "width": w * scale,
            "height": h * scale,
            "scale": scale,
            "bounding_box": {"x": x, "y": y, "w": w, "h": h}
        }
    
    async def _extract_text(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract text elements from blueprint (room labels, dimensions)
        """
        # This would use OCR (like Tesseract) in a full implementation
        # For now, return placeholder
        return [
            {"text": "Living Room", "location": (100, 100), "type": "room_label"},
            {"text": "Kitchen", "location": (300, 100), "type": "room_label"},
            {"text": "Master Bedroom", "location": (100, 300), "type": "room_label"}
        ]