"""
S3 Storage Service for AutoHVAC
Handles all file operations using AWS S3 instead of local disk
"""
import os
import io
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

logger = logging.getLogger(__name__)

class S3StorageService:
    """
    AWS S3-based storage service for AutoHVAC
    Replaces local disk storage with cloud storage
    """
    
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
        
        # Configure boto3 with retry logic and connection pooling
        config = Config(
            region_name=self.aws_region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50  # For high throughput
        )
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=config
        )
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Verify bucket exists and is accessible
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"[S3 STORAGE] Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise RuntimeError(f"S3 bucket does not exist: {self.bucket_name}")
            elif error_code == '403':
                raise RuntimeError(f"Access denied to S3 bucket: {self.bucket_name}")
            else:
                raise RuntimeError(f"Failed to access S3 bucket: {e}")
        
        logger.info(f"[S3 STORAGE] Storage service initialized with bucket: {self.bucket_name}")
        logger.info(f"[S3 STORAGE] AWS Region: {self.aws_region}")
    
    def _get_s3_key(self, prefix: str, filename: str) -> str:
        """Generate S3 key from prefix and filename"""
        return f"{prefix}/{filename}"
    
    async def save_upload(self, project_id: str, content: bytes) -> str:
        """
        Save uploaded file to S3 using job-based folder structure
        
        Args:
            project_id: Unique project identifier
            content: File content as bytes
            
        Returns:
            str: S3 key of the uploaded file
        """
        # Use new job-based folder structure
        s3_key = f"jobs/{project_id}/blueprint.pdf"
        
        logger.info(f"[S3 SAVE] Starting upload for project {project_id}")
        logger.info(f"[S3 SAVE] S3 key: {s3_key}")
        logger.info(f"[S3 SAVE] Content size: {len(content)} bytes")
        
        try:
            # Use thread pool for blocking S3 operation
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType='application/pdf',
                    Metadata={
                        'project_id': project_id,
                        'upload_type': 'blueprint'
                    }
                )
            )
            
            # Verify upload
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            )
            
            actual_size = response['ContentLength']
            if actual_size != len(content):
                raise IOError(f"Upload size mismatch: expected {len(content)}, got {actual_size}")
            
            logger.info(f"[S3 SAVE] Successfully uploaded file for project {project_id}")
            logger.info(f"[S3 SAVE] S3 key: {s3_key}, size: {actual_size} bytes")
            
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload file to S3 for project {project_id}: {e}")
            raise
    
    def cleanup(self, project_id: str):
        """
        Remove entire job folder from S3
        
        Args:
            project_id: Project identifier
        """
        prefix = f"jobs/{project_id}/"
        
        try:
            logger.info(f"[S3 CLEANUP] Starting cleanup for project {project_id}")
            logger.info(f"[S3 CLEANUP] Removing all files under: {prefix}")
            
            # List all objects in the job folder
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # Collect all keys to delete
            keys_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        keys_to_delete.append({'Key': obj['Key']})
            
            # Delete all objects
            if keys_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': keys_to_delete}
                )
                logger.info(f"[S3 CLEANUP] Successfully deleted {len(keys_to_delete)} files for project {project_id}")
            else:
                logger.info(f"[S3 CLEANUP] No files found for project {project_id}")
            
        except Exception as e:
            logger.error(f"[S3 CLEANUP] Failed to cleanup files for project {project_id}: {e}")
            # Don't raise - cleanup failures shouldn't break the flow
    
    def save_json(self, project_id: str, filename: str, data: Dict[str, Any]) -> str:
        """
        Save JSON data to S3 in the job folder
        
        Args:
            project_id: Project identifier
            filename: JSON filename (e.g., 'analysis.json', 'hvac_results.json')
            data: Dictionary to save as JSON
            
        Returns:
            str: S3 key of the saved file
        """
        s3_key = f"jobs/{project_id}/{filename}"
        
        try:
            # Convert data to JSON string
            json_content = json.dumps(data, indent=2, default=str)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'project_id': project_id,
                    'file_type': 'json',
                    'json_type': filename.replace('.json', '')
                }
            )
            logger.info(f"[S3 JSON] Saved JSON file: {s3_key} ({len(json_content)} bytes)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save JSON for project {project_id}/{filename}: {e}")
            raise
    
    def get_json(self, project_id: str, filename: str) -> Dict[str, Any]:
        """
        Retrieve JSON data from S3
        
        Args:
            project_id: Project identifier
            filename: JSON filename to retrieve
            
        Returns:
            Dict containing the JSON data
        """
        s3_key = f"jobs/{project_id}/{filename}"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            json_content = response['Body'].read().decode('utf-8')
            return json.loads(json_content)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"JSON file not found: {s3_key}")
            raise
    
    def list_job_files(self, project_id: str) -> List[str]:
        """
        List all files for a specific job
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of file paths relative to the job folder
        """
        prefix = f"jobs/{project_id}/"
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Remove the prefix to get relative path
                        relative_path = obj['Key'].replace(prefix, '')
                        files.append(relative_path)
            
            logger.info(f"[S3 LIST] Found {len(files)} files for project {project_id}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files for project {project_id}: {e}")
            raise
    
    def save_debug_json(self, project_id: str, filename: str, data: Dict[str, Any]) -> str:
        """
        Save debug JSON data to the debug subfolder
        
        Args:
            project_id: Project identifier
            filename: Debug JSON filename
            data: Debug data to save
            
        Returns:
            str: S3 key of the saved file
        """
        s3_key = f"jobs/{project_id}/debug/{filename}"
        
        try:
            json_content = json.dumps(data, indent=2, default=str)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'project_id': project_id,
                    'file_type': 'debug',
                    'debug_type': filename.replace('.json', '')
                }
            )
            logger.debug(f"[S3 DEBUG] Saved debug file: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save debug JSON for project {project_id}/{filename}: {e}")
            # Don't raise for debug files - they're non-critical
            return ""
    
    def get_file_content(self, project_id: str) -> bytes:
        """
        Get file content from S3 (checks both new and old locations)
        
        Args:
            project_id: Project identifier
            
        Returns:
            bytes: File content
        """
        # Try new location first
        s3_key = f"jobs/{project_id}/blueprint.pdf"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Fallback to old location for backward compatibility
                s3_key = self._get_s3_key("uploads", f"{project_id}.pdf")
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {s3_key}")
            raise
    
    def file_exists(self, project_id: str) -> bool:
        """
        Check if file exists in S3 (checks both new and old locations)
        
        Args:
            project_id: Project identifier
            
        Returns:
            bool: True if file exists
        """
        # Try new location first
        s3_key = f"jobs/{project_id}/blueprint.pdf"
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Try old location
                s3_key = self._get_s3_key("uploads", f"{project_id}.pdf")
                try:
                    self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=s3_key
                    )
                    return True
                except ClientError as e2:
                    if e2.response['Error']['Code'] == '404':
                        return False
                    raise
            else:
                raise
    
    def save_processed_data(self, project_id: str, filename: str, content: bytes) -> str:
        """
        Save processed data files to S3
        
        Args:
            project_id: Project identifier
            filename: Name of the file
            content: File content as bytes
            
        Returns:
            str: S3 key of the saved file
        """
        s3_key = self._get_s3_key(f"processed/{project_id}", filename)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                Metadata={
                    'project_id': project_id,
                    'file_type': 'processed'
                }
            )
            logger.info(f"[S3 STORAGE] Saved processed file: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save processed file for project {project_id}: {e}")
            raise
    
    def save_report(self, project_id: str, content: bytes) -> str:
        """
        Save generated PDF report to S3
        
        Args:
            project_id: Project identifier
            content: PDF content as bytes
            
        Returns:
            str: Relative path for database storage
        """
        s3_key = self._get_s3_key("reports", f"{project_id}_report.pdf")
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType='application/pdf',
                Metadata={
                    'project_id': project_id,
                    'file_type': 'report'
                }
            )
            logger.info(f"[S3 STORAGE] Saved report: {s3_key}")
            # Return relative path for database storage (maintains compatibility)
            return f"reports/{project_id}_report.pdf"
            
        except Exception as e:
            logger.error(f"Failed to save report for project {project_id}: {e}")
            raise
    
    def save_temp_file(self, project_id: str, filename: str, content: bytes) -> str:
        """
        Save temporary file to S3
        
        Args:
            project_id: Project identifier
            filename: Name of the temporary file
            content: File content as bytes
            
        Returns:
            str: S3 key of the saved file
        """
        s3_key = self._get_s3_key(f"temp/{project_id}", filename)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                Metadata={
                    'project_id': project_id,
                    'file_type': 'temp'
                }
            )
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save temp file for project {project_id}: {e}")
            raise
    
    def cleanup_temp(self, project_id: str):
        """
        Clean up temporary files for a project from S3
        
        Args:
            project_id: Project identifier
        """
        prefix = f"temp/{project_id}/"
        
        try:
            # List all objects with the prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # Collect all keys to delete
            keys_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        keys_to_delete.append({'Key': obj['Key']})
            
            # Delete all objects
            if keys_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': keys_to_delete}
                )
                logger.info(f"[S3 CLEANUP] Removed {len(keys_to_delete)} temp files for project {project_id}")
            
        except Exception as e:
            logger.error(f"[S3 CLEANUP] Failed to cleanup temp files for project {project_id}: {e}")
            # Don't raise - cleanup failures shouldn't break the flow
    
    def get_download_url(self, project_id: str, file_type: str = "report", expiry_seconds: int = 3600) -> str:
        """
        Generate pre-signed URL for secure file download
        
        Args:
            project_id: Project identifier
            file_type: Type of file ("report", "upload", etc.)
            expiry_seconds: URL expiry time in seconds (default: 1 hour)
            
        Returns:
            str: Pre-signed URL for download
        """
        if file_type == "report":
            s3_key = self._get_s3_key("reports", f"{project_id}_report.pdf")
        elif file_type == "upload":
            s3_key = self._get_s3_key("uploads", f"{project_id}.pdf")
        else:
            raise ValueError(f"Unknown file type: {file_type}")
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiry_seconds
            )
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL for project {project_id}: {e}")
            raise
    
    def get_report_content(self, project_id: str) -> bytes:
        """
        Get report content from S3
        
        Args:
            project_id: Project identifier
            
        Returns:
            bytes: Report content
        """
        s3_key = self._get_s3_key("reports", f"{project_id}_report.pdf")
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Report not found in S3: {s3_key}")
            raise
    
    def download_to_temp_file(self, project_id: str) -> str:
        """
        Download file from S3 to a temporary local file
        Used by workers that need local file access
        
        Args:
            project_id: Project identifier
            
        Returns:
            str: Path to temporary file
        """
        import tempfile
        
        # Try new location first
        s3_key = f"jobs/{project_id}/blueprint.pdf"
        
        # Check if file exists in new location
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
        except ClientError:
            # Fallback to old location
            s3_key = self._get_s3_key("uploads", f"{project_id}.pdf")
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                temp_path = tmp_file.name
                
                # Download from S3 to temp file
                self.s3_client.download_file(
                    self.bucket_name,
                    s3_key,
                    temp_path
                )
                
                logger.info(f"[S3 DOWNLOAD] Downloaded {s3_key} to temporary file: {temp_path}")
                return temp_path
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {s3_key}")
            raise
    
    # Compatibility methods to match the old interface
    def get_file_path(self, project_id: str) -> str:
        """
        For compatibility - returns S3 key instead of file path
        Workers should use download_to_temp_file() for local access
        """
        return self._get_s3_key("uploads", f"{project_id}.pdf")
    
    def get_temp_dir(self, project_id: str) -> str:
        """
        For compatibility - returns S3 prefix for temp files
        """
        return f"temp/{project_id}"
    
    def get_processed_file_path(self, project_id: str, filename: str) -> str:
        """
        For compatibility - returns S3 key
        """
        return self._get_s3_key(f"processed/{project_id}", filename)
    
    def get_report_path(self, project_id: str) -> str:
        """
        For compatibility - returns S3 key
        """
        return self._get_s3_key("reports", f"{project_id}_report.pdf")

# Singleton instance
storage_service = S3StorageService()