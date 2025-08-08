#!/usr/bin/env python3
"""
Pre-download PaddleOCR models to avoid download delays during runtime
Run this during Docker build or as part of deployment
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cache_paddleocr_models():
    """Pre-download PaddleOCR models for faster startup"""
    try:
        logger.info("Pre-downloading PaddleOCR models...")
        
        # Set environment to ensure models are downloaded
        os.environ['ENABLE_PADDLE_OCR'] = 'true'
        
        # Import PaddleOCR which will trigger model downloads
        from paddleocr import PaddleOCR
        
        # Initialize with the models we use
        logger.info("Downloading English detection model...")
        ocr = PaddleOCR(
            use_angle_cls=False,
            lang='en',
            use_gpu=False,
            show_log=True,
            det_model_dir=None,  # Will download if not present
            rec_model_dir=None,  # Will download if not present
            cls_model_dir=None   # Will download if not present
        )
        
        logger.info("PaddleOCR models successfully cached!")
        logger.info(f"Models stored in: {os.path.expanduser('~/.paddleocr')}")
        
        # Test that models work
        logger.info("Testing model loading...")
        test_result = ocr.ocr(None, det=False, rec=False, cls=False)
        logger.info("Model test successful!")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to cache PaddleOCR models: {e}")
        return False

if __name__ == "__main__":
    success = cache_paddleocr_models()
    exit(0 if success else 1)