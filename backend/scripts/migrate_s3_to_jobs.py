#!/usr/bin/env python3
"""
Migration script to move S3 files from old structure to new job-based structure
Old: /uploads/{project_id}.pdf
New: /jobs/{project_id}/blueprint.pdf
"""

import os
import sys
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class S3Migration:
    def __init__(self):
        # Get AWS configuration from environment
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
        self.bucket_name = os.getenv("S3_BUCKET", "autohvac-uploads")
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key]):
            raise RuntimeError(
                "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
            )
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        logger.info(f"Connected to S3 bucket: {self.bucket_name}")
    
    def list_uploads_folder(self) -> List[Dict]:
        """List all files in the uploads folder"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='uploads/'
            )
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
            
            logger.info(f"Found {len(files)} files in uploads folder")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list uploads folder: {e}")
            return []
    
    def migrate_file(self, old_key: str, dry_run: bool = False) -> bool:
        """
        Migrate a single file from old structure to new
        
        Args:
            old_key: The current S3 key (e.g., 'uploads/abc123.pdf')
            dry_run: If True, only log what would be done without making changes
        """
        try:
            # Extract project_id from old key
            if not old_key.startswith('uploads/') or not old_key.endswith('.pdf'):
                logger.warning(f"Skipping non-PDF or incorrectly formatted file: {old_key}")
                return False
            
            # Extract project_id
            filename = old_key.replace('uploads/', '')
            project_id = filename.replace('.pdf', '')
            
            # New key in job-based structure
            new_key = f"jobs/{project_id}/blueprint.pdf"
            
            if dry_run:
                logger.info(f"[DRY RUN] Would copy: {old_key} -> {new_key}")
                return True
            
            # Check if destination already exists
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=new_key)
                logger.info(f"Destination already exists, skipping: {new_key}")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Copy the file to new location
            logger.info(f"Copying: {old_key} -> {new_key}")
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': old_key},
                Key=new_key
            )
            
            # Verify the copy
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=new_key)
            if response['ContentLength'] > 0:
                logger.info(f"✅ Successfully migrated: {project_id}")
                
                # Optionally delete the old file (disabled by default for safety)
                if os.getenv('DELETE_OLD_FILES', 'false').lower() == 'true':
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_key)
                    logger.info(f"Deleted old file: {old_key}")
                
                return True
            else:
                logger.error(f"Copy verification failed for: {new_key}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to migrate {old_key}: {e}")
            return False
    
    def migrate_all(self, dry_run: bool = False):
        """Migrate all files from uploads to jobs structure"""
        files = self.list_uploads_folder()
        
        if not files:
            logger.info("No files to migrate")
            return
        
        logger.info(f"Starting migration of {len(files)} files...")
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
        
        success_count = 0
        fail_count = 0
        
        for file_info in files:
            if self.migrate_file(file_info['key'], dry_run):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Migration {'(DRY RUN) ' if dry_run else ''}Complete:")
        logger.info(f"  ✅ Successful: {success_count}")
        logger.info(f"  ❌ Failed: {fail_count}")
        logger.info(f"  📁 Total: {len(files)}")
        logger.info(f"{'='*50}")
    
    def verify_migration(self):
        """Verify that all files have been migrated correctly"""
        uploads_files = self.list_uploads_folder()
        
        logger.info("Verifying migration...")
        all_migrated = True
        
        for file_info in uploads_files:
            old_key = file_info['key']
            if not old_key.startswith('uploads/') or not old_key.endswith('.pdf'):
                continue
            
            filename = old_key.replace('uploads/', '')
            project_id = filename.replace('.pdf', '')
            new_key = f"jobs/{project_id}/blueprint.pdf"
            
            try:
                # Check if new file exists
                self.s3_client.head_object(Bucket=self.bucket_name, Key=new_key)
                logger.info(f"✅ {project_id}: Migrated successfully")
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.error(f"❌ {project_id}: Not migrated")
                    all_migrated = False
                else:
                    raise
        
        if all_migrated:
            logger.info("\n✅ All files have been successfully migrated!")
        else:
            logger.info("\n⚠️ Some files have not been migrated. Run migration again.")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate S3 files to job-based structure')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verify', action='store_true', help='Verify migration status')
    parser.add_argument('--delete-old', action='store_true', help='Delete old files after successful migration')
    
    args = parser.parse_args()
    
    # Set environment variable for deletion if requested
    if args.delete_old:
        os.environ['DELETE_OLD_FILES'] = 'true'
        logger.warning("⚠️ DELETE MODE ENABLED - Old files will be deleted after migration")
    
    try:
        migration = S3Migration()
        
        if args.verify:
            migration.verify_migration()
        else:
            migration.migrate_all(dry_run=args.dry_run)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()