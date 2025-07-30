"""
Storage service abstraction for handling file uploads
Supports Render disk mounts and fallback to temporary storage
"""
import os
import aiofiles
from typing import Optional
import logging
import traceback

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        # Use Render disk mount or fallback to /tmp
        self.storage_path = os.getenv("RENDER_DISK_PATH", "/tmp")
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"Storage service initialized with path: {self.storage_path}")
    
    async def save_upload(self, project_id: str, content: bytes) -> str:
        """Save uploaded file to persistent storage"""
        file_path = os.path.join(self.storage_path, f"{project_id}.pdf")
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            logger.info(f"Saved file for project {project_id} to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save file for project {project_id}: {e}")
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