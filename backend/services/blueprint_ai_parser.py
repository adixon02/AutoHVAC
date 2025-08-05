"""
GPT-4 Vision Blueprint Parser for AutoHVAC
Converts PDF blueprints to structured JSON using OpenAI's Vision API
"""

import os
import json
import base64
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4, UUID
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    
from openai import AsyncOpenAI
from app.parser.schema import (
    BlueprintSchema, Room, ParsingMetadata, ParsingStatus
)

logger = logging.getLogger(__name__)

# Import new modules for enhanced parsing
try:
    from services.ocr_extractor import ocr_extractor, TextRegion
    from services.page_classifier import page_classifier
    ENHANCED_PARSING = True
except ImportError as e:
    logger.warning(f"Enhanced parsing modules not available: {e}")
    ENHANCED_PARSING = False


class BlueprintAIParsingError(Exception):
    """Custom exception for AI blueprint parsing failures"""
    pass


class BlueprintAIParser:
    """
    AI-powered blueprint parser using GPT-4 Vision
    
    This service converts PDF blueprints to structured JSON by:
    1. Converting PDF pages to images
    2. Sending images to GPT-4V with specialized prompts
    3. Parsing the response into BlueprintSchema format
    4. Handling errors gracefully with fallbacks
    """
    
    def __init__(self):
        # Set default configuration values first
        self.max_image_size = 5 * 1024 * 1024   # 5MB max - much smaller for speed
        self.target_image_size = 2 * 1024 * 1024  # Target 2MB for optimal balance
        self.max_pages = 10  # Increased to ensure complete parsing
        self.min_resolution = 1024  # Increased minimum for better OCR
        self.max_resolution = 2048  # Cap maximum resolution to control size
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here" or api_key.strip() == "":
            logger.error("OPENAI_API_KEY not configured! AI blueprint parsing will fail.")
            logger.error("Please set OPENAI_API_KEY in your environment variables")
            logger.error("Get your API key from: https://platform.openai.com/api-keys")
            # Don't raise exception immediately - allow fallback to traditional parsing
            self.client = None
            self.api_key_valid = False
            return
        
        # Validate API key format (should start with sk-)
        if not api_key.startswith(('sk-', 'sk_test_', 'sk_live_')):
            logger.error(f"Invalid OpenAI API key format. Key should start with 'sk-' but got: {api_key[:10]}...")
            self.client = None
            self.api_key_valid = False
            return
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.api_key_valid = True
        logger.info("OpenAI API key validated successfully - AI parsing enabled")
        
    async def parse_pdf_with_gpt4v(
        self, 
        pdf_path: str, 
        filename: str, 
        zip_code: str, 
        project_id: Optional[str] = None
    ) -> BlueprintSchema:
        """
        Parse PDF blueprint using GPT-4 Vision
        
        Args:
            pdf_path: Path to PDF file
            filename: Original filename
            zip_code: Project location
            project_id: Optional project ID
            
        Returns:
            BlueprintSchema with extracted room data
            
        Raises:
            BlueprintAIParsingError: If parsing fails
        """
        start_time = time.time()
        
        # Initialize metadata
        parsing_metadata = ParsingMetadata(
            parsing_timestamp=datetime.utcnow(),
            processing_time_seconds=0.0,
            pdf_filename=filename,
            pdf_page_count=0,
            selected_page=1,
            geometry_status=ParsingStatus.FAILED,
            text_status=ParsingStatus.FAILED,
            ai_status=ParsingStatus.FAILED,
            overall_confidence=0.0,
            geometry_confidence=0.0,
            text_confidence=0.0
        )
        
        logger.info("="*60)
        logger.info(f"GPT-4V BLUEPRINT PARSING: {filename}")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Zip Code: {zip_code}")
        logger.info("="*60)
        
        try:
            # Step 1: Convert PDF to images
            logger.info("\n[STEP 1] Converting PDF to images...")
            images = self._convert_pdf_to_images(pdf_path)
            parsing_metadata.pdf_page_count = len(images)
            logger.info(f"Converted PDF to {len(images)} images")
            
            # Step 2: Preprocess and classify pages
            logger.info("\n[STEP 2] Preprocessing and classifying pages...")
            preprocessed_images = []
            page_classifications = []
            ocr_results = []
            
            if ENHANCED_PARSING:
                for idx, img_bytes in enumerate(images):
                    # Preprocess with OpenCV
                    preprocessed = self._preprocess_image_opencv(img_bytes, idx + 1)
                    preprocessed_images.append(preprocessed)
                    
                    # Convert to numpy for classification and OCR
                    nparr = np.frombuffer(preprocessed, np.uint8)
                    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Extract text with OCR
                    text_regions = ocr_extractor.extract_all_text(img_cv)
                    ocr_text = [region.text for region in text_regions]
                    ocr_results.append(text_regions)
                    
                    # Classify page
                    classification = page_classifier.classify_page(img_cv, ocr_text)
                    page_classifications.append(classification)
                    logger.info(f"Page {idx + 1}: {classification.page_type} (confidence: {classification.confidence:.2f})")
                    
                    # Log floor level if detected
                    if classification.floor_level:
                        logger.info(f"Page {idx + 1}: Detected floor level - {classification.floor_level}")
            else:
                # Fallback to original images if enhanced parsing not available
                preprocessed_images = images
                page_classifications = [None] * len(images)
                ocr_results = [None] * len(images)
            
            # Step 3: Try different pages with GPT-4V (prioritize floor plans)
            logger.info("\n[STEP 3] Analyzing pages with GPT-4V...")
            all_page_results = []
            successful_pages = []
            failed_pages = []
            
            # Prioritize floor plan pages based on classification
            if ENHANCED_PARSING and page_classifications:
                # Sort pages by floor plan confidence
                floor_plan_pages = [(idx, cls.confidence) for idx, cls in enumerate(page_classifications) 
                                  if cls.page_type == 'floor_plan']
                floor_plan_pages.sort(key=lambda x: x[1], reverse=True)
                
                other_pages = [idx for idx in range(len(images)) 
                             if idx not in [p[0] for p in floor_plan_pages]]
                
                # Try floor plans first, then others
                page_order = [p[0] for p in floor_plan_pages] + other_pages
                logger.info(f"Page processing order: {page_order} (floor plans first)")
            else:
                # Original order if no classification available
                page_order = [1, 0, 2, 3, 4, 5] if len(images) > 1 else [0]
            
            # First pass: try each page individually
            for page_idx in page_order:
                if page_idx < len(images):
                    try:
                        # Skip non-floor-plan pages if classification available
                        if ENHANCED_PARSING and page_idx < len(page_classifications):
                            if page_classifications[page_idx].page_type != 'floor_plan' and page_classifications[page_idx].confidence > 0.7:
                                logger.info(f"Skipping page {page_idx + 1} - classified as {page_classifications[page_idx].page_type}")
                                continue
                        
                        logger.info(f"Trying page {page_idx + 1} ({len(preprocessed_images[page_idx])} bytes)")
                        
                        # Pass OCR results to GPT-4V if available
                        ocr_data = None
                        if ENHANCED_PARSING and page_idx < len(ocr_results) and ocr_results[page_idx]:
                            # Extract dimensions from OCR
                            dimensions = ocr_extractor.extract_dimensions_from_regions(ocr_results[page_idx])
                            room_labels = [r for r in ocr_results[page_idx] if r.region_type == 'room_label']
                            ocr_data = {
                                'dimensions': dimensions,
                                'room_labels': room_labels,
                                'floor_level': page_classifications[page_idx].floor_level if page_idx < len(page_classifications) else None
                            }
                        
                        page_data = await self._extract_blueprint_data(preprocessed_images[page_idx], ocr_data=ocr_data)
                        
                        # Check if this page has substantial content
                        if page_data and 'rooms' in page_data and len(page_data['rooms']) > 0:
                            total_area_parsed = sum(r.get('area', 0) for r in page_data['rooms'])
                            logger.info(f"✅ Page {page_idx + 1}: Found {len(page_data['rooms'])} rooms, {total_area_parsed:.0f} sqft")
                            
                            all_page_results.append({
                                'page': page_idx + 1,
                                'data': page_data,
                                'room_count': len(page_data['rooms']),
                                'total_area': total_area_parsed
                            })
                            successful_pages.append(page_idx)
                        else:
                            logger.warning(f"❌ Page {page_idx + 1}: No rooms found")
                            failed_pages.append((page_idx, "no_rooms"))
                            
                    except BlueprintAIParsingError as e:
                        logger.warning(f"❌ Page {page_idx + 1} failed: {str(e)}")
                        failed_pages.append((page_idx, str(e)))
                        continue
            
            # Second pass: retry failed pages with different image processing
            if failed_pages and len(all_page_results) < 2:
                logger.info(f"Retrying {len(failed_pages)} failed pages with enhanced processing...")
                for page_idx, failure_reason in failed_pages:
                    if "Unable to identify floor plan" in failure_reason:
                        try:
                            # Try with enhanced image processing
                            enhanced_image = self._enhance_image_for_retry(images[page_idx], page_idx + 1)
                            logger.info(f"Retrying page {page_idx + 1} with enhanced image ({len(enhanced_image)} bytes)")
                            page_data = await self._extract_blueprint_data(enhanced_image, retry_count=1)
                            
                            if page_data and 'rooms' in page_data and len(page_data['rooms']) > 0:
                                total_area_parsed = sum(r.get('area', 0) for r in page_data['rooms'])
                                logger.info(f"✅ Page {page_idx + 1} (retry): Found {len(page_data['rooms'])} rooms, {total_area_parsed:.0f} sqft")
                                
                                all_page_results.append({
                                    'page': page_idx + 1,
                                    'data': page_data,
                                    'room_count': len(page_data['rooms']),
                                    'total_area': total_area_parsed,
                                    'retried': True
                                })
                                successful_pages.append(page_idx)
                        except Exception as e:
                            logger.warning(f"Page {page_idx + 1} retry failed: {str(e)}")
                            continue
            
            if not all_page_results:
                raise BlueprintAIParsingError("Failed to extract data from any page")
            
            # Select best result or combine if needed
            # Sort by total area parsed (descending)
            all_page_results.sort(key=lambda x: x['total_area'], reverse=True)
            best_result = all_page_results[0]
            
            # Check if we need to combine results from multiple pages
            # More aggressive combination strategy for completeness
            total_area_all_pages = sum(result['total_area'] for result in all_page_results)
            
            # Combine pages if:
            # 1. Best single page < 1500 sqft (likely incomplete)
            # 2. Best page has < 70% of total area across all pages
            # 3. Multiple pages have substantial content (> 500 sqft each)
            # 4. Only one page succeeded but area < 1500 sqft (NEW)
            should_combine = False
            combine_reason = ""
            
            # Enhanced combination logic for better area detection
            should_augment_with_fallback = False
            
            # Check if we have floor level information from OCR
            floors_detected = set()
            if ENHANCED_PARSING and page_classifications:
                for idx, result in enumerate(all_page_results):
                    page_idx = result['page'] - 1
                    if page_idx < len(page_classifications) and page_classifications[page_idx].floor_level:
                        floors_detected.add(page_classifications[page_idx].floor_level)
                        result['floor_level'] = page_classifications[page_idx].floor_level
            
            # Force combination if total area < 2000 sqft (typical minimum for residential)
            if total_area_all_pages < 2000:
                should_combine = True
                combine_reason = f"total area only {total_area_all_pages:.0f} sqft (below residential minimum)"
                logger.warning(f"⚠️  Total detected area {total_area_all_pages:.0f} sqft - forcing combination")
            
            # Special case: only one page succeeded but area is suspiciously low
            elif len(all_page_results) == 1 and best_result['total_area'] < 1800:
                logger.warning(f"⚠️  Only one page parsed with {best_result['total_area']:.0f} sqft - likely incomplete!")
                parsing_metadata.warnings.append(f"Only partial floor plan detected ({best_result['total_area']:.0f} sqft) - augmenting with estimated rooms")
                should_augment_with_fallback = True
                blueprint_data = best_result['data']
                parsing_metadata.selected_page = best_result['page']
            elif best_result['total_area'] < 2000 and len(all_page_results) > 1:
                should_combine = True
                combine_reason = f"best page only {best_result['total_area']:.0f} sqft"
            elif len(all_page_results) > 1 and best_result['total_area'] < 0.8 * total_area_all_pages:
                should_combine = True
                combine_reason = f"best page has only {best_result['total_area']/total_area_all_pages:.0%} of total area"
            elif len([r for r in all_page_results if r['total_area'] > 300]) >= 2:
                should_combine = True
                combine_reason = "multiple pages have substantial room data"
            
            if should_combine:
                logger.info(f"Combining pages ({combine_reason}): {best_result['total_area']:.0f} sqft best vs {total_area_all_pages:.0f} sqft total")
                blueprint_data = self._combine_page_results(all_page_results)
                parsing_metadata.selected_page = best_result['page']
                parsing_metadata.warnings.append(f"Combined {len(all_page_results)} pages ({combine_reason})")
            elif not should_augment_with_fallback:
                blueprint_data = best_result['data']
                parsing_metadata.selected_page = best_result['page']
                logger.info(f"Using page {best_result['page']} with {best_result['room_count']} rooms, {best_result['total_area']:.0f} sqft")
            
            # Augment with fallback rooms if parsing was incomplete
            if should_augment_with_fallback:
                blueprint_data = self._augment_with_fallback_rooms(blueprint_data, best_result['total_area'])
                parsing_metadata.warnings.append(f"Added estimated rooms to reach typical home size")
            
            parsing_metadata.ai_status = ParsingStatus.SUCCESS
            parsing_metadata.overall_confidence = 0.85
            total_rooms = len(blueprint_data.get('rooms', []))
            logger.info(f"Successfully extracted {total_rooms} rooms")
            
            # Step 4: Create BlueprintSchema
            blueprint_schema = self._create_blueprint_schema(
                blueprint_data, 
                project_id or str(uuid4()),
                zip_code,
                parsing_metadata
            )
            
            # Update final metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            blueprint_schema.parsing_metadata = parsing_metadata
            
            logger.info(f"GPT-4V parsing completed successfully in {parsing_metadata.processing_time_seconds:.2f}s")
            return blueprint_schema
            
        except Exception as e:
            # Record error in metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            parsing_metadata.errors_encountered.append({
                'stage': 'gpt4v_parsing',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': time.time()
            })
            
            logger.error(f"GPT-4V parsing failed for {filename}: {type(e).__name__}: {str(e)}")
            
            # Return minimal fallback blueprint
            return self._create_fallback_blueprint(zip_code, project_id, parsing_metadata, str(e))
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF pages to high-quality images using PyMuPDF (no poppler needed)"""
        try:
            import fitz  # PyMuPDF
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if total_pages == 0:
                raise BlueprintAIParsingError("PDF has no pages")
            
            logger.info(f"Converting {total_pages} pages to images using PyMuPDF")
            
            # Limit pages to process
            last_page = min(self.max_pages, total_pages)
            
            images = []
            for page_num in range(last_page):
                try:
                    page = doc[page_num]
                    
                    # Optimized resolution - target higher quality for better OCR
                    # Target ~1600-2000px on longest side for optimal GPT-4V text reading
                    page_rect = page.rect
                    max_dimension = max(page_rect.width, page_rect.height)
                    
                    # Calculate optimal zoom to target 1800px on longest side
                    target_size = 1800
                    zoom_factor = target_size / max_dimension
                    zoom_factor = min(zoom_factor, 3.0)  # Allow up to 3x zoom for clarity
                    zoom_factor = max(zoom_factor, 1.0)  # Minimum 1x zoom for quality
                    
                    mat = fitz.Matrix(zoom_factor, zoom_factor)
                    logger.info(f"Page {page_num + 1}: Using {zoom_factor:.2f}x zoom (target: {target_size}px)")
                    
                    # Render page as pixmap
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Use JPEG with higher quality for better text readability
                    img_bytes = pix.tobytes("jpeg", jpg_quality=95)
                    logger.info(f"Page {page_num + 1}: JPEG format ({len(img_bytes) / 1024 / 1024:.1f}MB)")
                    
                    # If still too large, try PNG with compression
                    if len(img_bytes) > self.target_image_size:
                        png_bytes = pix.tobytes("png")
                        if len(png_bytes) < len(img_bytes):
                            img_bytes = png_bytes
                            logger.info(f"Page {page_num + 1}: Switched to PNG ({len(img_bytes) / 1024 / 1024:.1f}MB)")
                    
                    # Compress if still too large
                    if len(img_bytes) > self.max_image_size:
                        img_bytes = self._compress_image_for_gpt4v(img_bytes, page_num + 1, pix.width, pix.height)
                    
                    images.append(img_bytes)
                    logger.info(f"Page {page_num + 1} ready: {len(img_bytes) / 1024 / 1024:.1f}MB")
                    
                except Exception as e:
                    logger.error(f"Failed to convert page {page_num+1}: {str(e)}")
                    continue
            
            doc.close()
            
            if not images:
                raise BlueprintAIParsingError("Failed to convert any pages to images")
            
            # Log total conversion metrics
            total_size = sum(len(img) for img in images)
            logger.info(f"[METRICS] Converted {len(images)} pages, total size: {total_size / 1024 / 1024:.1f}MB")
            logger.info(f"Successfully converted {len(images)} pages to images")
            
            return images
            
        except Exception as e:
            raise BlueprintAIParsingError(f"Failed to convert PDF to images with PyMuPDF: {str(e)}")
    
    def _compress_image_for_gpt4v(self, img_bytes: bytes, page_num: int, orig_width: int, orig_height: int) -> bytes:
        """Aggressively compress image for optimal GPT-4V performance"""
        logger.info(f"Compressing page {page_num} (original: {len(img_bytes) / 1024 / 1024:.1f}MB)")
        
        img = Image.open(BytesIO(img_bytes))
        
        # Target the smaller size for better API performance
        target_size = self.target_image_size
        
        # First try quality reduction with progressive compression
        for quality in [75, 65, 55, 45, 35]:
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
            compressed = buffer.getvalue()
            
            if len(compressed) <= target_size:
                logger.info(f"Compressed page {page_num} to {len(compressed) / 1024 / 1024:.1f}MB with JPEG quality {quality}")
                return compressed
        
        # If still too large, reduce resolution more aggressively
        return self._reduce_resolution_aggressive(img, page_num, target_size)
    
    def _reduce_resolution_aggressive(self, img: Image.Image, page_num: int, target_size: int) -> bytes:
        """Aggressively reduce resolution to hit target size for optimal GPT-4V performance"""
        orig_width, orig_height = img.size
        logger.info(f"Aggressively reducing resolution from {orig_width}x{orig_height}")
        
        # Calculate target dimensions for optimal GPT-4V performance
        # GPT-4V works well with images around 1024-1500px on longest side
        max_dimension = max(orig_width, orig_height)
        
        # Try progressively smaller sizes until we hit target file size
        target_dimensions = [1400, 1200, 1000, 800, 600]
        
        for target_dim in target_dimensions:
            if target_dim >= max_dimension:
                continue
                
            scale = target_dim / max_dimension
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            
            # Ensure minimum readable size
            if min(new_width, new_height) < 600:
                continue
            
            # Resize with high-quality resampling
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Try different qualities to hit target size
            for quality in [70, 60, 50, 40]:
                buffer = BytesIO()
                resized.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
                result = buffer.getvalue()
                
                if len(result) <= target_size:
                    logger.info(f"Reduced page {page_num} to {new_width}x{new_height} JPEG Q{quality} ({len(result) / 1024 / 1024:.1f}MB)")
                    return result
        
        # Final fallback: 800px longest side, low quality
        final_scale = 800 / max_dimension
        final_width = max(int(orig_width * final_scale), 600)
        final_height = max(int(orig_height * final_scale), 600)
        
        final_resized = img.resize((final_width, final_height), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        final_resized.save(buffer, format='JPEG', quality=35, optimize=True, progressive=True)
        result = buffer.getvalue()
        
        logger.warning(f"Page {page_num} final compression: {final_width}x{final_height} Q35 ({len(result) / 1024 / 1024:.1f}MB)")
        return result
    
    def _enhance_image_for_retry(self, image_bytes: bytes, page_num: int) -> bytes:
        """Enhance image for retry with different processing settings"""
        try:
            # Open image
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            orig_width, orig_height = img.size
            logger.info(f"Enhancing page {page_num} for retry: original {orig_width}x{orig_height}")
            
            # Try different processing approaches
            # 1. Increase contrast and brightness
            from PIL import ImageEnhance
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)  # Increase contrast by 30%
            
            # Enhance brightness slightly
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)  # Increase brightness by 10%
            
            # Enhance sharpness for text clarity
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)  # Increase sharpness by 50%
            
            # Resize to optimal resolution for GPT-4V (2000px on longest side)
            max_dimension = max(orig_width, orig_height)
            if max_dimension > 2000:
                scale = 2000 / max_dimension
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized to {new_width}x{new_height} for optimal GPT-4V processing")
            
            # Save as high-quality PNG for better text recognition
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            result = buffer.getvalue()
            
            logger.info(f"Enhanced page {page_num}: {len(result) / 1024 / 1024:.1f}MB PNG")
            return result
            
        except Exception as e:
            logger.error(f"Failed to enhance image for page {page_num}: {str(e)}")
            return image_bytes  # Return original on failure
    
    def _preprocess_image_opencv(self, image_bytes: bytes, page_num: int) -> bytes:
        """Preprocess image using OpenCV for better OCR and parsing"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error(f"Failed to decode image for page {page_num}")
                return image_bytes
            
            orig_height, orig_width = img.shape[:2]
            logger.info(f"Preprocessing page {page_num}: {orig_width}x{orig_height}")
            
            # 1. Denoise the image
            denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            
            # 2. Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 3. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            
            # 4. Merge channels back
            enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # 5. Sharpen the image for better text clarity
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # 6. Resize if needed (max 2500px on longest side for processing efficiency)
            max_dimension = max(orig_width, orig_height)
            if max_dimension > 2500:
                scale = 2500 / max_dimension
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                sharpened = cv2.resize(sharpened, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                logger.info(f"Resized to {new_width}x{new_height} for processing")
            
            # Convert back to bytes (high quality PNG)
            _, encoded = cv2.imencode('.png', sharpened)
            result = encoded.tobytes()
            
            logger.info(f"Preprocessed page {page_num}: {len(result) / 1024 / 1024:.1f}MB")
            return result
            
        except Exception as e:
            logger.error(f"OpenCV preprocessing failed for page {page_num}: {str(e)}")
            return image_bytes
    
    async def _extract_blueprint_data(self, image_bytes: bytes, retry_count: int = 0, ocr_data: Dict = None) -> Dict[str, Any]:
        """Extract blueprint data using GPT-4V with retry logic and OCR assistance"""
        # Check if API key is valid before attempting call
        if not self.api_key_valid or not self.client:
            raise BlueprintAIParsingError("OpenAI API key not configured - cannot use GPT-4V parsing")
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create the prompt
            prompt = self._create_blueprint_prompt()
            
            # Call GPT-4V (using gpt-4o which has vision capabilities)
            logger.info(f"Making GPT-4V API call with image size: {len(image_base64)} base64 chars")
            logger.info(f"Prompt length: {len(prompt)} chars")
            
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}",
                                        "detail": "high"  # Use high detail for accurate room detection
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,  # Increased for comprehensive room lists
                    temperature=0.1,  # Lower temperature for consistent JSON
                    timeout=60  # 60 second timeout to prevent hanging
                )
                logger.info("GPT-4V API call completed successfully")
                
            except Exception as api_error:
                logger.error(f"GPT-4V API call failed: {type(api_error).__name__}: {str(api_error)}")
                raise BlueprintAIParsingError(f"GPT-4V API call failed: {str(api_error)}")
            
            # Parse response
            response_text = response.choices[0].message.content
            logger.info(f"GPT-4V response length: {len(response_text) if response_text else 0}")
            logger.info(f"GPT-4V response preview: {repr(response_text[:200]) if response_text else 'None'}")
            
            if not response_text or not response_text.strip():
                raise BlueprintAIParsingError("GPT-4V returned empty response")
            
            # Check for common error responses that indicate vision issues
            if any(phrase in response_text.lower() for phrase in [
                "i'm unable to analyze",
                "cannot analyze",
                "unable to identify", 
                "cannot see",
                "unable to read",
                "cannot process"
            ]):
                logger.warning(f"GPT-4V indicated vision/analysis issues: {response_text[:100]}...")
                raise BlueprintAIParsingError(f"GPT-4V unable to analyze image: {response_text[:200]}")
            
            # Extract JSON from response (handle markdown code blocks)
            json_text = self._extract_json_from_response(response_text)
            logger.info(f"Extracted JSON preview: {repr(json_text[:200])}")
            blueprint_data = json.loads(json_text)
            
            # Check for error response in JSON
            if blueprint_data.get('error'):
                logger.warning(f"GPT-4V returned error: {blueprint_data['error']}")
                raise BlueprintAIParsingError(f"GPT-4V error: {blueprint_data['error']}")
            
            # Validate response structure
            if not isinstance(blueprint_data, dict) or 'rooms' not in blueprint_data:
                raise BlueprintAIParsingError("Invalid response structure from GPT-4V")
            
            # Log verification data if present
            if 'verification' in blueprint_data:
                v = blueprint_data['verification']
                logger.info(f"GPT-4V parsing verification: {v.get('room_count', 0)} rooms, "
                           f"{v.get('total_area_calculated', 0):.0f} sqft calculated, "
                           f"{v.get('missing_area', 0):.0f} sqft unaccounted")
            
            return blueprint_data
            
        except json.JSONDecodeError as e:
            raise BlueprintAIParsingError(f"Failed to parse GPT-4V response as JSON: {str(e)}")
        except Exception as e:
            raise BlueprintAIParsingError(f"GPT-4V API call failed: {str(e)}")
    
    def _create_blueprint_prompt(self) -> str:
        """Create optimized prompt for fast, accurate HVAC data extraction"""
        return """
You are analyzing a floor plan image for residential HVAC load calculations. Extract room dimensions and details systematically.

CRITICAL: This image may show:
- FIRST FLOOR ONLY (look for "First Floor", "1st Floor", "Level 1" labels)
- SECOND FLOOR ONLY (look for "Second Floor", "2nd Floor", "Level 2" labels) 
- BASEMENT/LOWER LEVEL (look for "Basement", "Lower Level" labels)
- A SECTION/WING of a larger building
- MULTIPLE FLOORS on one page (stacked or side-by-side)

Extract ALL visible rooms regardless of which floor/section they're on!

STEP 1 - IMAGE ANALYSIS:
First, describe what you see in the image:
- Is this a floor plan drawing? (walls, rooms, labels)
- What floor/level is shown? (check for floor labels)
- Can you identify room boundaries and labels?
- Are there dimension lines or measurements?
- Is there a scale notation visible?
- Is there a north arrow or compass? Which way is north?
- Are there stairs shown? (indicates multi-story building)

If you see NO floor plan elements AT ALL (only title page, elevation, section, or details), return: {"error": "Unable to identify floor plan in image", "rooms": []}

IMPORTANT: If you see ANY rooms, extract them ALL - even partial views!

STEP 2 - ROOM EXTRACTION:
For each identifiable space (room, closet, hallway), extract:
- Room name/label (or describe location if unlabeled)
- Dimensions if shown (e.g., "15'-0\" x 12'-6\"")
- Estimated area in square feet
- Number of windows (count window symbols)
- Number of exterior walls (walls on building perimeter)
- Orientation (N, S, E, W, NE, NW, SE, SW based on which direction windows/walls face)

STEP 3 - SYSTEMATIC COVERAGE:
Work through the floor plan methodically:
1. Start at entry/front door if visible
2. Move clockwise through all rooms
3. Include ALL spaces: bedrooms, bathrooms, kitchen, living areas, dining, hallways, closets, utility rooms, garage
4. Don't skip small spaces - closets and hallways matter for HVAC
5. CRITICAL: Check floor labels and set floor=1 for first/main floor, floor=2 for second floor, floor=0 for basement
6. If you see stairs, this indicates a multi-story building - extract all visible rooms

RETURN JSON FORMAT:
{
  "image_type": "floor_plan",
  "can_read_text": true,
  "scale_found": false,
  "scale_notation": "not found",
  "total_area": 0,
  "stories": 1,
  "north_arrow_found": false,
  "building_orientation": "",
  "partial_floor_plan": false,
  "floor_level": 1,
  "floor_label": "First Floor",
  "has_stairs": false,
  "appears_complete": true,
  "rooms": [
    {
      "name": "Master Bedroom",
      "raw_dimensions": "16' x 14'",
      "dimensions_ft": [16.0, 14.0],
      "area": 224.0,
      "floor": 1,
      "windows": 2,
      "exterior_walls": 2,
      "orientation": "S",
      "room_type": "bedroom",
      "confidence": 0.8,
      "location_description": "upper right corner"
    }
  ],
  "verification": {
    "room_count": 0,
    "total_area_calculated": 0,
    "missing_area": 0,
    "parsing_notes": ""
  }
}

ROOM TYPE OPTIONS: bedroom, bathroom, kitchen, living, dining, hallway, closet, laundry, office, garage, utility, storage, entry, other

DIMENSION PARSING:
- "15'-6\" x 12'-0\"" → [15.5, 12.0]
- "15x12" → [15.0, 12.0]
- If no dimensions shown, estimate based on typical residential scale (8-10 ft ceilings, 10-20 ft room widths)

CONFIDENCE LEVELS:
- 0.9-1.0: Dimensions clearly labeled
- 0.7-0.8: Room identified, dimensions estimated from scale
- 0.5-0.6: Room assumed from layout
- Below 0.5: Uncertain

FLOOR DETECTION RULES:
- If labeled "Second Floor", "2nd Floor", "Upper Level" → floor=2 for all rooms
- If labeled "First Floor", "1st Floor", "Main Level" → floor=1 for all rooms  
- If labeled "Basement", "Lower Level" → floor=0 for all rooms
- If no floor label but has bedrooms → likely upper floor (floor=2)
- If no floor label but has kitchen/living → likely main floor (floor=1)

Return valid JSON even if you can only partially read the floor plan. Include all rooms you can identify."""
    
    def _combine_page_results(self, page_results: List[Dict]) -> Dict[str, Any]:
        """Combine room data from multiple pages, removing duplicates"""
        combined_data = {
            'scale_found': False,
            'scale_notation': 'unknown',
            'scale_factor': 48,
            'total_area': 0,
            'stories': 1,
            'rooms': [],
            'parsing_completeness': 'multi-page',
            'verification': {
                'pages_combined': len(page_results),
                'original_room_count': 0,
                'deduplicated_room_count': 0
            }
        }
        
        # Collect all rooms from all pages
        all_rooms = []
        seen_rooms = set()  # Track room names to avoid duplicates
        
        for result in page_results:
            data = result['data']
            
            # Update scale information if found
            if data.get('scale_found', False):
                combined_data['scale_found'] = True
                combined_data['scale_notation'] = data.get('scale_notation', 'unknown')
                combined_data['scale_factor'] = data.get('scale_factor', 48)
            
            # Update stories if higher
            combined_data['stories'] = max(combined_data['stories'], data.get('stories', 1))
            
            # Add rooms, checking for duplicates
            for room in data.get('rooms', []):
                room_key = f"{room['name']}_{room.get('floor', 1)}"
                
                # Skip if we've seen this room (by name and floor)
                if room_key not in seen_rooms:
                    seen_rooms.add(room_key)
                    all_rooms.append(room)
                else:
                    # Check if this is a better version of the same room
                    existing_idx = next((i for i, r in enumerate(all_rooms) 
                                       if f"{r['name']}_{r.get('floor', 1)}" == room_key), None)
                    if existing_idx is not None:
                        # Keep the one with higher confidence
                        if room.get('confidence', 0) > all_rooms[existing_idx].get('confidence', 0):
                            all_rooms[existing_idx] = room
        
        combined_data['rooms'] = all_rooms
        combined_data['total_area'] = sum(r.get('area', 0) for r in all_rooms)
        combined_data['verification']['original_room_count'] = sum(result['room_count'] for result in page_results)
        combined_data['verification']['deduplicated_room_count'] = len(all_rooms)
        
        logger.info(f"Combined {len(page_results)} pages: {combined_data['verification']['original_room_count']} → "
                   f"{combined_data['verification']['deduplicated_room_count']} unique rooms, "
                   f"{combined_data['total_area']:.0f} sqft total")
        
        return combined_data
    
    def _augment_with_fallback_rooms(self, blueprint_data: Dict[str, Any], detected_area: float) -> Dict[str, Any]:
        """Augment incomplete blueprint data with estimated rooms to reach typical home size"""
        logger.warning(f"Augmenting partial blueprint data ({detected_area:.0f} sqft detected)")
        
        # Target typical home size based on detected floors
        # Multi-story homes are typically larger
        floors_count = blueprint_data.get('stories', 1)
        if floors_count > 1:
            target_area = 2800  # Multi-story home
        else:
            target_area = 2400  # Single-story home
        missing_area = target_area - detected_area
        
        if missing_area <= 0:
            return blueprint_data  # No augmentation needed
        
        logger.info(f"Adding estimated rooms for {missing_area:.0f} sqft missing area")
        
        # Typical rooms that might be missing
        fallback_rooms = [
            # Common missing rooms in partial floor plans
            {"name": "Kitchen", "dims": [15.0, 12.0], "area": 180, "type": "kitchen", "windows": 2},
            {"name": "Master Bedroom", "dims": [16.0, 14.0], "area": 224, "type": "bedroom", "windows": 2},
            {"name": "Living Room", "dims": [18.0, 16.0], "area": 288, "type": "living", "windows": 3},
            {"name": "Dining Room", "dims": [12.0, 12.0], "area": 144, "type": "dining", "windows": 2},
            {"name": "Bedroom 2", "dims": [12.0, 11.0], "area": 132, "type": "bedroom", "windows": 1},
            {"name": "Bedroom 3", "dims": [11.0, 11.0], "area": 121, "type": "bedroom", "windows": 1},
            {"name": "Family Room", "dims": [16.0, 14.0], "area": 224, "type": "living", "windows": 2},
            {"name": "Bathroom 2", "dims": [8.0, 7.0], "area": 56, "type": "bathroom", "windows": 1},
            {"name": "Bathroom 3", "dims": [7.0, 6.0], "area": 42, "type": "bathroom", "windows": 0},
            {"name": "Hallway", "dims": [20.0, 5.0], "area": 100, "type": "hallway", "windows": 0},
            {"name": "Office", "dims": [11.0, 10.0], "area": 110, "type": "office", "windows": 1},
            {"name": "Laundry", "dims": [8.0, 8.0], "area": 64, "type": "laundry", "windows": 1},
        ]
        
        # Check which rooms are already detected
        existing_room_types = set()
        for room in blueprint_data.get('rooms', []):
            room_type = room.get('room_type', '')
            if room_type:
                existing_room_types.add(room_type)
        
        # Add missing rooms until we reach target area
        added_area = 0
        added_rooms = []
        
        for fallback in fallback_rooms:
            # Skip if we already have this type of room (except bedrooms/bathrooms)
            if fallback['type'] in existing_room_types and fallback['type'] not in ['bedroom', 'bathroom']:
                continue
            
            # Skip if we've added enough area
            if added_area >= missing_area * 0.85:  # 85% of missing area
                break
            
            # Create augmented room
            augmented_room = {
                "name": f"{fallback['name']} (Estimated)",
                "raw_dimensions": f"{fallback['dims'][0]}' x {fallback['dims'][1]}'",
                "dimensions_ft": fallback['dims'],
                "area": fallback['area'],
                "floor": 1,
                "windows": fallback['windows'],
                "exterior_walls": 1 if fallback['windows'] > 0 else 0,
                "orientation": "unknown",
                "room_type": fallback['type'],
                "confidence": 0.3,  # Low confidence for estimated rooms
                "location_description": "estimated location",
                "augmented": True
            }
            
            added_rooms.append(augmented_room)
            added_area += fallback['area']
        
        # Update blueprint data
        if 'rooms' not in blueprint_data:
            blueprint_data['rooms'] = []
        
        blueprint_data['rooms'].extend(added_rooms)
        blueprint_data['total_area'] = sum(r.get('area', 0) for r in blueprint_data['rooms'])
        blueprint_data['augmentation_info'] = {
            'original_area': detected_area,
            'added_area': added_area,
            'added_rooms': len(added_rooms),
            'target_area': target_area
        }
        
        logger.info(f"Added {len(added_rooms)} estimated rooms ({added_area:.0f} sqft) to reach {blueprint_data['total_area']:.0f} sqft total")
        
        return blueprint_data
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from GPT response, handling markdown code blocks"""
        response_text = response_text.strip()
        
        # Remove markdown code block markers if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        return response_text.strip()
    
    def _create_blueprint_schema(
        self, 
        blueprint_data: Dict[str, Any], 
        project_id: str, 
        zip_code: str,
        parsing_metadata: ParsingMetadata
    ) -> BlueprintSchema:
        """Create BlueprintSchema from enhanced GPT-4V extracted data"""
        try:
            # Log scale information for debugging
            scale_found = blueprint_data.get('scale_found', False)
            scale_notation = blueprint_data.get('scale_notation', 'unknown')
            scale_factor = blueprint_data.get('scale_factor', 48)  # Default to 1/4" scale
            
            logger.info(f"Scale detection: found={scale_found}, notation={scale_notation}, factor={scale_factor}")
            
            # Extract rooms with enhanced data
            rooms = []
            suspicious_rooms = []
            
            for room_data in blueprint_data.get('rooms', []):
                # Extract and validate dimensions
                raw_dims = room_data.get('raw_dimensions', '')
                dims_ft = room_data.get('dimensions_ft', [12.0, 12.0])
                area = room_data.get('area', 144.0)
                area_matches = room_data.get('area_matches_dimensions', True)
                
                # Validate room area against typical sizes
                room_name = room_data.get('name', 'Unknown Room')
                room_type = room_data.get('room_type', self._classify_room_type(room_name))
                
                # Check for suspicious areas
                if area > 800 and room_type not in ['great_room', 'warehouse', 'garage']:
                    logger.warning(f"Suspicious room area: {room_name} = {area} sq ft (type: {room_type})")
                    suspicious_rooms.append(f"{room_name}: {area} sq ft")
                    # Reduce confidence for suspicious dimensions
                    room_data['confidence'] = min(room_data.get('confidence', 0.5), 0.3)
                
                # Extract confidence and validate
                confidence = room_data.get('confidence', 0.5)
                if confidence < 0.3:
                    logger.warning(f"Low confidence ({confidence}) for room: {room_name}")
                
                # Handle orientation with confidence tracking
                orientation = room_data.get('orientation', 'unknown')
                if orientation == 'unknown' or not blueprint_data.get('north_arrow_found', False):
                    orientation = 'unknown'
                    orientation_confidence = 0.0
                else:
                    orientation_confidence = blueprint_data.get('orientation_confidence', 0.5)
                
                room = Room(
                    name=room_name,
                    dimensions_ft=tuple(dims_ft),
                    floor=room_data.get('floor', 1),
                    windows=room_data.get('windows', 1),
                    orientation=orientation,
                    area=area,
                    room_type=room_type,
                    confidence=confidence,
                    center_position=(0.0, 0.0),  # Not available from vision
                    label_found=True,  # GPT-4V identified the room
                    dimensions_source=room_data.get('dimension_source', 'estimated'),
                    # Store enhanced HVAC data in source_elements for load calculations
                    source_elements={
                        "raw_dimensions": raw_dims,
                        "area_matches_dimensions": area_matches,
                        "exterior_doors": room_data.get('exterior_doors', 0),
                        "exterior_walls": room_data.get('exterior_walls', 1),
                        "corner_room": room_data.get('corner_room', False),
                        "ceiling_height": room_data.get('ceiling_height', 9.0),
                        "notes": room_data.get('notes', ''),
                        "scale_found": scale_found,
                        "scale_notation": scale_notation,
                        "scale_factor": scale_factor,
                        "north_arrow_found": blueprint_data.get('north_arrow_found', False),
                        "north_direction": blueprint_data.get('north_direction', 'unknown'),
                        "orientation_confidence": orientation_confidence,
                        "dimension_source": room_data.get('dimension_source', 'estimated'),
                        "thermal_exposure": self._calculate_thermal_exposure(room_data),
                        "augmented": room_data.get('augmented', False)
                    }
                )
                rooms.append(room)
            
            # Calculate totals and validate
            total_area_calculated = sum(room.area for room in rooms)
            total_area_declared = blueprint_data.get('total_area', 0)
            
            # Use calculated total if declared is 0 or missing
            if total_area_declared == 0:
                total_area_final = total_area_calculated
                total_area_source = 'calculated'
            else:
                total_area_final = total_area_declared
                total_area_source = blueprint_data.get('total_area_source', 'declared')
            
            # Validation: Check if total area is reasonable
            if total_area_final < 1000:
                logger.warning(f"⚠️  Total area {total_area_final:.0f} sqft is unusually small for residential!")
                parsing_metadata.warnings.append(f"Total area {total_area_final:.0f} sqft below typical residential minimum")
            elif total_area_final > 5000:
                logger.warning(f"⚠️  Total area {total_area_final:.0f} sqft is unusually large for residential!")
                parsing_metadata.warnings.append(f"Total area {total_area_final:.0f} sqft above typical residential maximum")
            
            # Count augmented rooms
            augmented_count = sum(1 for r in rooms if r.source_elements.get('augmented', False))
            if augmented_count > 0:
                logger.info(f"Total area: {total_area_final:.0f} sqft ({total_area_source}), "
                           f"{len(rooms)} rooms ({augmented_count} augmented)")
            else:
                logger.info(f"Total area: {total_area_final:.0f} sqft ({total_area_source}), "
                           f"calculated: {total_area_calculated:.0f} sqft, "
                           f"{len(rooms)} rooms extracted")
            
            stories = blueprint_data.get('stories', 1)
            
            # Validate total area
            if total_area_final > 10000:
                logger.warning(f"Suspicious total area: {total_area_final} sq ft for residential building")
                if suspicious_rooms:
                    logger.warning(f"Suspicious rooms found: {', '.join(suspicious_rooms)}")
            
            # Check if calculated matches declared
            if total_area_declared > 0 and abs(total_area_calculated - total_area_declared) / total_area_declared > 0.2:
                logger.warning(f"Total area mismatch: calculated={total_area_calculated}, declared={total_area_declared}")
            
            # Store building-level data in raw_geometry for Manual J calculations
            building_data = {
                "building_orientation": blueprint_data.get('building_orientation', ''),
                "total_conditioned_area": total_area_final,
                "total_area_calculated": total_area_calculated,
                "total_area_source": total_area_source,
                "stories": stories,
                "parsing_method": "gpt4v_enhanced",
                "scale_found": scale_found,
                "scale_notation": scale_notation,
                "scale_factor": scale_factor,
                "suspicious_rooms": suspicious_rooms,
                "room_count": len(rooms),
                "hvac_load_factors": {
                    "total_exterior_windows": sum(room.windows for room in rooms),
                    "total_exterior_doors": sum(room.source_elements.get("exterior_doors", 0) for room in rooms),
                    "corner_rooms": len([r for r in rooms if r.source_elements.get("corner_room", False)]),
                    "thermal_zones": len(rooms)
                }
            }
            
            # Add warnings to parsing metadata
            if suspicious_rooms:
                parsing_metadata.warnings.append(f"Suspicious room areas detected: {', '.join(suspicious_rooms)}")
            if not scale_found:
                parsing_metadata.warnings.append("No scale found on blueprint - dimensions are estimated")
            
            return BlueprintSchema(
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                zip_code=zip_code,
                sqft_total=total_area_final,
                stories=stories,
                rooms=rooms,
                raw_geometry=building_data,  # Enhanced building data for HVAC calculations
                raw_text={"ai_analysis_notes": [room.source_elements.get("notes", "") for room in rooms]},
                dimensions=[],  # Integrated into room data
                labels=[],  # Integrated into room data
                geometric_elements=[],  # Vision-based, not geometric
                parsing_metadata=parsing_metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating enhanced BlueprintSchema: {str(e)}")
            raise BlueprintAIParsingError(f"Failed to create blueprint schema: {str(e)}")
    
    def _calculate_thermal_exposure(self, room_data: Dict[str, Any]) -> str:
        """Calculate thermal exposure level for HVAC load calculations"""
        exterior_walls = room_data.get('exterior_walls', 1)
        corner_room = room_data.get('corner_room', False)
        windows = room_data.get('windows', 1)
        
        if corner_room and exterior_walls >= 2:
            return "high"  # Corner rooms with multiple exterior walls
        elif exterior_walls >= 2 or windows >= 3:
            return "medium"  # Multiple exterior walls or many windows
        else:
            return "low"  # Interior or minimally exposed rooms
    
    def _classify_room_type(self, room_name: str) -> str:
        """Classify room type from name"""
        name_lower = room_name.lower()
        
        if any(word in name_lower for word in ['bed', 'br']):
            return 'bedroom'
        elif any(word in name_lower for word in ['bath', 'ba']):
            return 'bathroom'
        elif any(word in name_lower for word in ['kitchen', 'kit']):
            return 'kitchen'
        elif any(word in name_lower for word in ['living', 'lr', 'family']):
            return 'living'
        elif any(word in name_lower for word in ['dining', 'dr']):
            return 'dining'
        elif any(word in name_lower for word in ['office', 'study', 'den']):
            return 'office'
        else:
            return 'other'
    
    def _create_fallback_blueprint(
        self, 
        zip_code: str, 
        project_id: Optional[str], 
        metadata: ParsingMetadata, 
        error: str
    ) -> BlueprintSchema:
        """Create fallback blueprint when GPT-4V parsing fails"""
        logger.error("=" * 60)
        logger.error("GPT-4V PARSING FAILED - Creating fallback room structure")
        logger.error(f"Error: {error}")
        logger.error("This will result in estimated HVAC calculations only!")
        logger.error("=" * 60)
        
        # Create a typical residential layout as fallback
        # Target ~2329 sq ft typical home (conditioned space only)
        typical_rooms = [
            ("Living Room", (20.0, 18.0), "living", 360, 3),
            ("Kitchen", (15.0, 18.0), "kitchen", 270, 2),
            ("Dining Room", (14.0, 12.0), "dining", 168, 2),
            ("Master Bedroom", (16.0, 14.0), "master_bedroom", 224, 2),
            ("Master Bathroom", (10.0, 8.0), "bathroom", 80, 1),
            ("Bedroom 2", (12.0, 12.0), "bedroom", 144, 2),
            ("Bedroom 3", (12.0, 11.0), "bedroom", 132, 2),
            ("Bedroom 4", (11.0, 11.0), "bedroom", 121, 2),
            ("Bathroom 2", (8.0, 7.0), "bathroom", 56, 1),
            ("Bathroom 3", (7.0, 6.0), "bathroom", 42, 0),
            ("Family Room", (18.0, 16.0), "living", 288, 3),
            ("Laundry", (8.0, 8.0), "laundry", 64, 1),
            ("Hallway", (30.0, 5.0), "hallway", 150, 0),
            ("Entry", (10.0, 8.0), "other", 80, 1),
            ("Closets", (10.0, 15.0), "closet", 150, 0),
        ]
        
        rooms = []
        for name, (width, height), room_type, area, window_count in typical_rooms:
            room = Room(
                name=f"{name} (AI Parsing Failed - Estimated)",
                dimensions_ft=(width, height),
                floor=1,
                windows=window_count,
                orientation="unknown",
                area=area,
                room_type=room_type,
                confidence=0.0,  # Zero confidence - complete fallback
                center_position=(0.0, 0.0),
                label_found=False,
                dimensions_source="gpt4v_fallback",
                source_elements={
                    "error": "GPT-4V parsing failed",
                    "reason": str(error),
                    "warning": "Using typical residential layout - results are estimates only"
                }
            )
            rooms.append(room)
        
        total_area = sum(room.area for room in rooms)
        
        # Update metadata
        metadata.warnings.append(f"GPT-4V parsing failed: {error}")
        metadata.errors_encountered.append({
            'stage': 'gpt4v_fallback',
            'error': str(error),
            'error_type': 'GPT4VParsingFailure',
            'impact': 'Using estimated typical layout - HVAC calculations approximate'
        })
        
        return BlueprintSchema(
            project_id=UUID(project_id) if project_id and isinstance(project_id, str) else project_id or uuid4(),
            zip_code=zip_code,
            sqft_total=total_area,
            stories=1,
            rooms=rooms,
            raw_geometry={},
            raw_text={},
            dimensions=[],
            labels=[],
            geometric_elements=[],
            parsing_metadata=metadata
        )


# Global instance
blueprint_ai_parser = BlueprintAIParser()