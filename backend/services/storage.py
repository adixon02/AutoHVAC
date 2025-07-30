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
                "This must be set to the shared disk mount path (e.g., /var/data/uploads)"
            )
        
        logger.info(f"[STORAGE INIT] RENDER_DISK_PATH={self.storage_path}")
        
        # Ensure the storage path exists and is writable
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            
            # List current contents for debugging
            try:
                contents = os.listdir(self.storage_path)
                logger.info(f"[STORAGE INIT] Directory contents ({len(contents)} files): {contents[:10]}...")
            except Exception as e:
                logger.warning(f"[STORAGE INIT] Could not list directory contents: {e}")
            
            # Test write permissions
            test_file = os.path.join(self.storage_path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.unlink(test_file)
            
            logger.info(f"[STORAGE INIT] Storage service initialized successfully at {self.storage_path}")
        except Exception as e:
            logger.error(f"[STORAGE INIT] Storage path {self.storage_path} is not accessible: {e}")
            raise RuntimeError(f"Cannot initialize storage at {self.storage_path}: {e}")
    
    async def save_upload(self, project_id: str, content: bytes) -> str:
        """Save uploaded file to persistent storage"""
        file_path = os.path.join(self.storage_path, f"{project_id}.pdf")
        
        logger.info(f"[STORAGE SAVE] Starting save for project {project_id}")
        logger.info(f"[STORAGE SAVE] RENDER_DISK_PATH={self.storage_path}")
        logger.info(f"[STORAGE SAVE] Target path: {file_path}")
        logger.info(f"[STORAGE SAVE] Content size: {len(content)} bytes")
        
        try:
            # List directory contents before save
            try:
                contents = os.listdir(self.storage_path)
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
                contents = os.listdir(self.storage_path)
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
        file_path = os.path.join(self.storage_path, f"{project_id}.pdf")
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
        return os.path.join(self.storage_path, f"{project_id}.pdf")
    
    def file_exists(self, project_id: str) -> bool:
        """Check if file exists for a project"""
        return os.path.exists(self.get_file_path(project_id))

# Singleton instance
storage_service = StorageService()