#!/usr/bin/env python3
"""
One-time migration script to organize existing files into new directory structure
Run this after deploying the new storage service

Usage:
    python scripts/migrate_storage.py [--dry-run]
"""

import os
import sys
import shutil
import logging
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import storage_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_storage(dry_run=False):
    """
    Migrate existing files to new directory structure
    
    Current structure:
    /var/data/uploads/{project_id}.pdf
    
    New structure (already created by storage service):
    /var/data/
    ├── uploads/     # Keep PDFs here (no change)
    ├── processed/   # New - for future use
    ├── reports/     # New - for generated reports
    └── temp/        # New - for temporary files
    """
    logger.info("="*60)
    logger.info("Storage Migration Script")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Storage path: {storage_service.storage_path}")
    logger.info("="*60)
    
    # Statistics
    stats = {
        'files_checked': 0,
        'files_migrated': 0,
        'errors': 0,
        'already_organized': 0
    }
    
    try:
        # Check that new directories exist
        for dir_name, dir_path in [
            ('uploads', storage_service.upload_dir),
            ('processed', storage_service.processed_dir),
            ('reports', storage_service.reports_dir),
            ('temp', storage_service.temp_dir)
        ]:
            if not os.path.exists(dir_path):
                logger.error(f"{dir_name} directory does not exist: {dir_path}")
                return False
            else:
                logger.info(f"✓ {dir_name} directory exists: {dir_path}")
        
        # Check for any PDF files in the root storage directory
        root_files = []
        if os.path.exists(storage_service.storage_path):
            for file in os.listdir(storage_service.storage_path):
                file_path = os.path.join(storage_service.storage_path, file)
                if os.path.isfile(file_path) and file.endswith('.pdf'):
                    root_files.append(file)
        
        if root_files:
            logger.info(f"\nFound {len(root_files)} PDF files in root directory to migrate")
            for file in root_files[:10]:  # Show first 10
                logger.info(f"  - {file}")
            if len(root_files) > 10:
                logger.info(f"  ... and {len(root_files) - 10} more")
            
            # Migrate files from root to uploads/
            for file in root_files:
                stats['files_checked'] += 1
                src_path = os.path.join(storage_service.storage_path, file)
                dst_path = os.path.join(storage_service.upload_dir, file)
                
                try:
                    if os.path.exists(dst_path):
                        logger.warning(f"File already exists in uploads/: {file}")
                        stats['already_organized'] += 1
                        continue
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would move: {src_path} -> {dst_path}")
                    else:
                        shutil.move(src_path, dst_path)
                        logger.info(f"Moved: {file} -> uploads/")
                    
                    stats['files_migrated'] += 1
                    
                except Exception as e:
                    logger.error(f"Error moving {file}: {e}")
                    stats['errors'] += 1
        else:
            logger.info("\nNo PDF files found in root directory - migration may not be needed")
        
        # Check uploads directory
        upload_files = []
        if os.path.exists(storage_service.upload_dir):
            upload_files = [f for f in os.listdir(storage_service.upload_dir) if f.endswith('.pdf')]
            logger.info(f"\nFiles in uploads/ directory: {len(upload_files)}")
            stats['already_organized'] = len(upload_files)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Migration Summary:")
        logger.info(f"  Files checked:        {stats['files_checked']}")
        logger.info(f"  Files migrated:       {stats['files_migrated']}")
        logger.info(f"  Already organized:    {stats['already_organized']}")
        logger.info(f"  Errors:              {stats['errors']}")
        logger.info("="*60)
        
        if dry_run and stats['files_migrated'] > 0:
            logger.info("\nThis was a dry run. Run without --dry-run to perform actual migration.")
        
        return stats['errors'] == 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate storage to new directory structure')
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be done without making changes'
    )
    args = parser.parse_args()
    
    success = migrate_storage(dry_run=args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()