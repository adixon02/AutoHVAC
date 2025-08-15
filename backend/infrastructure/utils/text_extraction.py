"""
Text Extraction Utilities
Extracts text blocks from PDF files
"""

import logging
from typing import List, Dict, Any
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text blocks from PDF with location information.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of text blocks with text, bbox, and page info
    """
    text_blocks = []
    
    try:
        # Open PDF with proper error handling
        doc = fitz.open(pdf_path)
        
        # Get page count safely
        page_count = doc.page_count
        logger.info(f"PDF has {page_count} pages")
        
        for page_num in range(page_count):
            try:
                page = doc[page_num]
                
                # Try simple text extraction first
                simple_text = page.get_text()
                if simple_text.strip():
                    # Split into words and create basic blocks
                    words = simple_text.split()
                    for i, word in enumerate(words):
                        word = word.strip()
                        if word and len(word) > 1:  # Skip single characters
                            text_blocks.append({
                                'text': word,
                                'bbox': [0, 0, 100, 20],  # Default bbox
                                'page': page_num,
                                'font': '',
                                'size': 12
                            })
                
                # Try detailed extraction if simple worked
                if simple_text.strip():
                    try:
                        blocks = page.get_text("dict")
                        detailed_blocks = []
                        
                        for block in blocks.get("blocks", []):
                            if block.get("type") == 0:  # Text block
                                for line in block.get("lines", []):
                                    for span in line.get("spans", []):
                                        text = span.get("text", "").strip()
                                        if text:
                                            detailed_blocks.append({
                                                'text': text,
                                                'bbox': span.get("bbox", [0, 0, 100, 20]),
                                                'page': page_num,
                                                'font': span.get("font", ""),
                                                'size': span.get("size", 12)
                                            })
                        
                        # Use detailed blocks if we got them
                        if detailed_blocks:
                            # Remove the simple blocks for this page
                            text_blocks = [b for b in text_blocks if b['page'] != page_num]
                            text_blocks.extend(detailed_blocks)
                            
                    except Exception as detail_error:
                        logger.warning(f"Detailed extraction failed for page {page_num}: {detail_error}")
                        # Keep the simple text blocks
                        
            except Exception as page_error:
                logger.warning(f"Error processing page {page_num}: {page_error}")
                continue
        
        doc.close()
        logger.info(f"Extracted {len(text_blocks)} text blocks from {page_count} pages")
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        
        # Fallback: try alternative PDF libraries
        try:
            logger.info("Trying alternative PDF extraction...")
            import PyPDF2
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        words = text.split()
                        for word in words:
                            word = word.strip()
                            if word and len(word) > 1:
                                text_blocks.append({
                                    'text': word,
                                    'bbox': [0, 0, 100, 20],
                                    'page': page_num,
                                    'font': '',
                                    'size': 12
                                })
            
            logger.info(f"Alternative extraction found {len(text_blocks)} text blocks")
            
        except ImportError:
            logger.warning("PyPDF2 not available for fallback")
        except Exception as fallback_error:
            logger.error(f"Fallback extraction failed: {fallback_error}")
    
    return text_blocks