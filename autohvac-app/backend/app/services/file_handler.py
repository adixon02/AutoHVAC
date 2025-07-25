"""
File handling service for secure upload processing
"""
import os
import tempfile
import aiofiles
from pathlib import Path
from typing import AsyncIterator
import uuid

from fastapi import UploadFile
from ..core import settings, get_logger, FileSizeError, FileUploadError

logger = get_logger(__name__)


class FileHandler:
    """Service for handling file uploads securely"""
    
    def __init__(self):
        self.upload_dir = Path(settings.temp_dir) / "autohvac_uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = settings.upload_chunk_size_mb * 1024 * 1024  # Convert to bytes
        self.max_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
    
    async def save_upload_file(self, upload_file: UploadFile) -> tuple[str, int]:
        """
        Save uploaded file to disk with streaming and size limits.
        
        Returns:
            tuple: (file_path, file_size_bytes)
        
        Raises:
            FileSizeError: If file exceeds size limit
            FileUploadError: If upload fails
        """
        if not upload_file.filename:
            raise FileUploadError("No filename provided")
        
        # Generate unique filename to prevent conflicts
        file_id = str(uuid.uuid4())
        safe_filename = self._sanitize_filename(upload_file.filename)
        file_path = self.upload_dir / f"{file_id}_{safe_filename}"
        
        total_size = 0
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                while True:
                    chunk = await upload_file.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    total_size += len(chunk)
                    
                    # Check size limit
                    if total_size > self.max_size:
                        # Clean up partial file
                        await self._cleanup_file(file_path)
                        raise FileSizeError(
                            f"File size {total_size / 1024 / 1024:.1f}MB exceeds limit of {settings.max_file_size_mb}MB"
                        )
                    
                    await f.write(chunk)
            
            logger.info(f"File saved: {file_path} ({total_size} bytes)")
            return str(file_path), total_size
            
        except FileSizeError:
            raise
        except Exception as e:
            # Clean up on any error
            await self._cleanup_file(file_path)
            raise FileUploadError(f"Failed to save file: {str(e)}")
    
    async def _cleanup_file(self, file_path: Path):
        """Clean up a file safely"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove path separators and limit length
        safe_name = filename.replace('/', '_').replace('\\', '_')
        if len(safe_name) > 100:
            safe_name = safe_name[-100:]  # Keep last 100 chars
        return safe_name
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        path = Path(file_path)
        if not path.exists():
            return {}
        
        stat = path.stat()
        return {
            "size_bytes": stat.st_size,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
            "filename": path.name
        }
    
    async def delete_file(self, file_path: str):
        """Delete a file safely"""
        try:
            path = Path(file_path)
            if path.exists() and path.parent == self.upload_dir:
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")


# Global instance
file_handler = FileHandler()