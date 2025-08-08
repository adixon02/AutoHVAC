"""
PDF to Images Converter - Multi-page PDF processing for GPT-5 Vision
Handles conversion of PDF pages to high-quality images for vision analysis
"""

import fitz  # PyMuPDF
import base64
import io
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from dataclasses import dataclass

from services.vision_config import vision_config

logger = logging.getLogger(__name__)


@dataclass
class PageImage:
    """Represents a single PDF page as an image"""
    page_num: int  # 0-indexed
    image_base64: str
    width_px: int
    height_px: int
    dpi: int
    has_text: bool  # Whether page contains extractable text
    text_preview: str  # First 200 chars of text for classification
    
    @property
    def page_number(self) -> int:
        """1-indexed page number for display"""
        return self.page_num + 1
    
    @property
    def aspect_ratio(self) -> float:
        return self.width_px / self.height_px if self.height_px > 0 else 1.0


class PDFToImages:
    """Convert PDF pages to images for vision processing"""
    
    def __init__(self, dpi: int = None):
        """
        Initialize PDF to image converter
        
        Args:
            dpi: Dots per inch for rendering (default from config)
        """
        self.dpi = dpi or vision_config.pdf_dpi
        self.max_dimension = 4096  # Max dimension for vision models
        
    def convert_all_pages(
        self,
        pdf_path: str,
        page_range: Optional[Tuple[int, int]] = None
    ) -> List[PageImage]:
        """
        Convert all or specified pages of PDF to images
        
        Args:
            pdf_path: Path to PDF file
            page_range: Optional (start, end) tuple for page range (0-indexed)
            
        Returns:
            List of PageImage objects
        """
        logger.info(f"Converting PDF to images: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Determine pages to process
            if page_range:
                start_page = max(0, page_range[0])
                end_page = min(total_pages, page_range[1])
            else:
                start_page = 0
                end_page = total_pages
            
            logger.info(f"Processing pages {start_page + 1} to {end_page} of {total_pages}")
            
            page_images = []
            for page_num in range(start_page, end_page):
                page_image = self._convert_page(doc, page_num)
                if page_image:
                    page_images.append(page_image)
            
            doc.close()
            
            logger.info(f"Successfully converted {len(page_images)} pages to images")
            return page_images
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
    
    def convert_specific_pages(
        self,
        pdf_path: str,
        page_numbers: List[int]
    ) -> List[PageImage]:
        """
        Convert specific pages of PDF to images
        
        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers to convert (0-indexed)
            
        Returns:
            List of PageImage objects
        """
        logger.info(f"Converting specific pages from PDF: {page_numbers}")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            page_images = []
            for page_num in page_numbers:
                if 0 <= page_num < total_pages:
                    page_image = self._convert_page(doc, page_num)
                    if page_image:
                        page_images.append(page_image)
                else:
                    logger.warning(f"Page {page_num + 1} out of range (total: {total_pages})")
            
            doc.close()
            
            return page_images
            
        except Exception as e:
            logger.error(f"Error converting specific pages: {e}")
            raise
    
    def _convert_page(self, doc: fitz.Document, page_num: int) -> Optional[PageImage]:
        """
        Convert a single PDF page to image
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number to convert (0-indexed)
            
        Returns:
            PageImage object or None if conversion fails
        """
        try:
            page = doc[page_num]
            
            # Extract text for classification
            text = page.get_text()
            text_preview = text[:200] if text else ""
            has_text = len(text.strip()) > 10
            
            # Calculate optimal DPI to stay within max dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Calculate scale factor
            scale = self.dpi / 72.0  # 72 DPI is PDF default
            
            # Check if scaled dimensions exceed max
            scaled_width = page_width * scale
            scaled_height = page_height * scale
            
            if max(scaled_width, scaled_height) > self.max_dimension:
                # Reduce DPI to fit within max dimension
                max_scale = self.max_dimension / max(page_width, page_height)
                actual_dpi = int(max_scale * 72)
                logger.debug(f"Reducing DPI from {self.dpi} to {actual_dpi} for page {page_num + 1}")
            else:
                actual_dpi = self.dpi
            
            # Render page to pixmap
            mat = fitz.Matrix(actual_dpi / 72.0, actual_dpi / 72.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Optimize image if needed
            img = self._optimize_image(img)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Create PageImage object
            page_image = PageImage(
                page_num=page_num,
                image_base64=img_base64,
                width_px=img.width,
                height_px=img.height,
                dpi=actual_dpi,
                has_text=has_text,
                text_preview=text_preview
            )
            
            logger.debug(f"Converted page {page_num + 1}: {img.width}x{img.height}px @ {actual_dpi} DPI")
            
            return page_image
            
        except Exception as e:
            logger.error(f"Error converting page {page_num + 1}: {e}")
            return None
    
    def _optimize_image(self, img: Image.Image) -> Image.Image:
        """
        Optimize image for vision model processing
        
        Args:
            img: PIL Image object
            
        Returns:
            Optimized PIL Image
        """
        # Convert RGBA to RGB if needed (removes transparency)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Additional optimization could be added here:
        # - Contrast enhancement for faded blueprints
        # - Noise reduction
        # - Sharpening
        
        return img
    
    def identify_floor_plan_pages(self, page_images: List[PageImage]) -> List[int]:
        """
        Identify which pages likely contain floor plans
        Based on text content and image characteristics
        
        Args:
            page_images: List of PageImage objects
            
        Returns:
            List of page numbers (0-indexed) that likely contain floor plans
        """
        floor_plan_pages = []
        
        # Keywords that indicate floor plan pages
        floor_plan_keywords = [
            'floor plan', 'floor layout', 'level', 'first floor', 'second floor',
            'basement', 'ground floor', 'upper level', 'lower level',
            'sq ft', 'square feet', 'scale', "1/4", "1/8", "1:50", "1:100"
        ]
        
        # Keywords that indicate non-floor-plan pages
        exclude_keywords = [
            'elevation', 'section', 'detail', 'electrical', 'plumbing',
            'hvac', 'mechanical', 'structural', 'site plan', 'roof plan'
        ]
        
        for page_image in page_images:
            text_lower = page_image.text_preview.lower()
            
            # Check for floor plan indicators
            has_floor_plan_keyword = any(keyword in text_lower for keyword in floor_plan_keywords)
            has_exclude_keyword = any(keyword in text_lower for keyword in exclude_keywords)
            
            # Page is likely a floor plan if:
            # 1. Has floor plan keywords and no exclude keywords
            # 2. Has very little text (typical for floor plans)
            # 3. Has landscape orientation (wider than tall)
            if (has_floor_plan_keyword and not has_exclude_keyword) or \
               (not page_image.has_text) or \
               (page_image.aspect_ratio > 1.2):  # Landscape
                floor_plan_pages.append(page_image.page_num)
                logger.info(f"Page {page_image.page_number} identified as potential floor plan")
        
        # If no pages identified, include all pages for GPT-5 to analyze
        if not floor_plan_pages:
            logger.warning("No floor plan pages identified, including all pages")
            floor_plan_pages = [p.page_num for p in page_images]
        
        return floor_plan_pages
    
    def prepare_for_vision_api(
        self,
        page_images: List[PageImage],
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Prepare images for vision API request
        
        Args:
            page_images: List of PageImage objects
            max_pages: Maximum number of pages to include
            
        Returns:
            List of image content blocks for API
        """
        max_pages = max_pages or vision_config.max_pages_per_request
        
        # Limit number of pages if needed
        selected_pages = page_images[:max_pages] if len(page_images) > max_pages else page_images
        
        image_contents = []
        for page_image in selected_pages:
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{page_image.image_base64}",
                    "detail": vision_config.models[0].image_detail
                }
            })
        
        logger.info(f"Prepared {len(image_contents)} images for vision API")
        
        return image_contents


# Global converter instance
pdf_converter = PDFToImages()