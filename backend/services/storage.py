"""
Storage service abstraction for handling file uploads
Supports Render disk mounts and fallback to temporary storage
"""
import os
import aiofiles
from typing import Optional
import logging
import traceback
import time

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        # REQUIRE RENDER_DISK_PATH to be set - no hardcoded defaults
        self.storage_path = os.getenv("RENDER_DISK_PATH")
        
        if not self.storage_path:
            raise RuntimeError(
                "RENDER_DISK_PATH environment variable is not set. "
                "This must be set to the shared disk mount path (e.g., /var/data)"
            )
        
        logger.info(f"[STORAGE INIT] RENDER_DISK_PATH={self.storage_path}")
        
        # Check if the storage path exists (mount point should already exist)
        if not os.path.exists(self.storage_path):
            raise RuntimeError(
                f"Storage path does not exist: {self.storage_path}. "
                "Ensure the persistent disk is properly mounted."
            )
        
        # Check if it's a directory
        if not os.path.isdir(self.storage_path):
            raise RuntimeError(f"Storage path is not a directory: {self.storage_path}")
        
        # Define all directory paths
        self.upload_dir = os.path.join(self.storage_path, "uploads")
        self.processed_dir = os.path.join(self.storage_path, "processed")
        self.reports_dir = os.path.join(self.storage_path, "reports")
        self.temp_dir = os.path.join(self.storage_path, "temp")
        
        # Initialize all directories
        self._initialize_directories()
        
        logger.info(f"[STORAGE INIT] Storage service initialized successfully")
        logger.info(f"[STORAGE INIT] Mount point: {self.storage_path}")
        logger.info(f"[STORAGE INIT] Directories: uploads/, processed/, reports/, temp/")
    
    def _initialize_directories(self):
        """Create all required directories with proper permissions"""
        dirs = [
            ("uploads", self.upload_dir),
            ("processed", self.processed_dir),
            ("reports", self.reports_dir),
            ("temp", self.temp_dir)
        ]
        
        for dir_name, dir_path in dirs:
            try:
                # Create directory if it doesn't exist
                if not os.path.exists(dir_path):
                    logger.info(f"[STORAGE INIT] Creating {dir_name} directory: {dir_path}")
                    os.makedirs(dir_path, mode=0o755, exist_ok=True)
                
                # Test write permissions
                test_file = os.path.join(dir_path, ".write_test")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.unlink(test_file)
                
                # List current contents for debugging (only for uploads)
                if dir_name == "uploads":
                    try:
                        contents = os.listdir(dir_path)
                        logger.info(f"[STORAGE INIT] {dir_name} directory contents ({len(contents)} files): {contents[:10]}...")
                    except Exception as e:
                        logger.warning(f"[STORAGE INIT] Could not list {dir_name} directory contents: {e}")
                
            except Exception as e:
                logger.error(f"[STORAGE INIT] Cannot initialize {dir_name} directory: {e}")
                raise RuntimeError(f"{dir_name} directory is not writable: {e}")
    
    async def save_upload(self, project_id: str, content: bytes) -> str:
        """Save uploaded file to persistent storage"""
        file_path = os.path.join(self.upload_dir, f"{project_id}.pdf")
        
        logger.info(f"[STORAGE SAVE] Starting save for project {project_id}")
        logger.info(f"[STORAGE SAVE] RENDER_DISK_PATH={self.storage_path}")
        logger.info(f"[STORAGE SAVE] Target path: {file_path}")
        logger.info(f"[STORAGE SAVE] Content size: {len(content)} bytes")
        
        try:
            # List directory contents before save
            try:
                contents = os.listdir(self.upload_dir)
                logger.info(f"[STORAGE SAVE] Pre-save directory contents ({len(contents)} files): {contents[:10]}...")
            except Exception as e:
                logger.warning(f"[STORAGE SAVE] Could not list directory: {e}")
            
            # Ensure directory exists (in case it was deleted)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Verify file was written correctly
            if not os.path.exists(file_path):
                raise IOError(f"File not found after write: {file_path}")
            
            actual_size = os.path.getsize(file_path)
            if actual_size != len(content):
                raise IOError(f"File size mismatch: expected {len(content)}, got {actual_size}")
            
            # List directory contents after save
            try:
                contents = os.listdir(self.upload_dir)
                logger.info(f"[STORAGE SAVE] Post-save directory contents ({len(contents)} files): {contents[:10]}...")
            except Exception as e:
                logger.warning(f"[STORAGE SAVE] Could not list directory: {e}")
            
            logger.info(f"[STORAGE SAVE] Successfully saved file for project {project_id}")
            logger.info(f"[STORAGE SAVE] File path: {file_path}, size: {actual_size} bytes")
            
            # Log file verification for debugging
            with open(file_path, 'rb') as f:
                first_bytes = f.read(16)
                logger.info(f"[STORAGE SAVE] File verification - first_16_bytes: {first_bytes.hex()}")
            
            # Return only the project_id, not the full path
            # The worker will reconstruct the path from its own RENDER_DISK_PATH
            return file_path
        except Exception as e:
            logger.error(f"Failed to save file for project {project_id}: {e}")
            logger.error(f"Storage path: {self.storage_path}, File path: {file_path}")
            raise
    
    def cleanup(self, project_id: str):
        """Remove processed file - ONLY call after all processing complete"""
        file_path = os.path.join(self.upload_dir, f"{project_id}.pdf")
        try:
            if os.path.exists(file_path):
                # Log detailed cleanup info
                logger.info(f"[CLEANUP] Starting cleanup for project {project_id}")
                logger.info(f"[CLEANUP] File path: {file_path}")
                logger.info(f"[CLEANUP] File size: {os.path.getsize(file_path)} bytes")
                logger.info(f"[CLEANUP] Caller stack trace:")
                for line in traceback.format_stack()[:-1]:
                    logger.debug(f"[CLEANUP]   {line.strip()}")
                
                os.unlink(file_path)
                logger.info(f"[CLEANUP] Successfully cleaned up file for project {project_id}")
            else:
                logger.warning(f"[CLEANUP] File not found for cleanup: {file_path}")
        except Exception as e:
            logger.error(f"[CLEANUP] Failed to cleanup file for project {project_id}: {e}")
            # Don't raise - cleanup failures shouldn't break the flow
    
    def get_file_path(self, project_id: str) -> str:
        """Get the file path for a project"""
        return os.path.join(self.upload_dir, f"{project_id}.pdf")
    
    def file_exists(self, project_id: str) -> bool:
        """Check if file exists for a project"""
        return os.path.exists(self.get_file_path(project_id))
    
    def save_processed_data(self, project_id: str, filename: str, content: bytes) -> str:
        """Save processed data files (images, JSON, etc)"""
        # Create project subdirectory
        project_dir = os.path.join(self.processed_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        file_path = os.path.join(project_dir, filename)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"[STORAGE] Saved processed file: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save processed file for project {project_id}: {e}")
            raise
    
    def save_report(self, project_id: str, content: bytes) -> str:
        """Save generated PDF report"""
        file_path = os.path.join(self.reports_dir, f"{project_id}_report.pdf")
        
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"[STORAGE] Saved report: {file_path}")
            # Return relative path for database storage
            return f"reports/{project_id}_report.pdf"
        except Exception as e:
            logger.error(f"Failed to save report for project {project_id}: {e}")
            raise
    
    def get_temp_dir(self, project_id: str) -> str:
        """Get temporary directory for a project, creating if needed"""
        temp_project_dir = os.path.join(self.temp_dir, project_id)
        os.makedirs(temp_project_dir, exist_ok=True)
        return temp_project_dir
    
    def cleanup_temp(self, project_id: str):
        """Clean up temporary files for a project"""
        import shutil
        temp_project_dir = os.path.join(self.temp_dir, project_id)
        try:
            if os.path.exists(temp_project_dir):
                shutil.rmtree(temp_project_dir)
                logger.info(f"[CLEANUP] Removed temp directory for project {project_id}")
        except Exception as e:
            logger.error(f"[CLEANUP] Failed to cleanup temp files for project {project_id}: {e}")
            # Don't raise - cleanup failures shouldn't break the flow
    
    def get_processed_file_path(self, project_id: str, filename: str) -> str:
        """Get path to a processed file"""
        return os.path.join(self.processed_dir, project_id, filename)
    
    def get_report_path(self, project_id: str) -> str:
        """Get path to report file"""
        return os.path.join(self.reports_dir, f"{project_id}_report.pdf")

# Singleton instance
storage_service = StorageService()