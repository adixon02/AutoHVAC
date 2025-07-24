"""
Extraction Storage Service
Handles persistence, retrieval, and management of JSON extraction data
"""
import json
import gzip
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from uuid import uuid4

from models.extraction_schema import (
    CompleteExtractionResult, 
    ExtractionStorageInfo,
    ExtractionVersion
)

logger = logging.getLogger(__name__)

class ExtractionStorageService:
    """Service for managing JSON extraction data storage"""
    
    def __init__(
        self, 
        storage_root: str = "./extractions",
        compression_threshold_mb: float = 1.0,
        default_retention_days: int = 30,
        enable_compression: bool = True
    ):
        self.storage_root = Path(storage_root)
        self.compression_threshold_mb = compression_threshold_mb
        self.default_retention_days = default_retention_days
        self.enable_compression = enable_compression
        
        # Ensure storage directory exists
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.storage_root / "active").mkdir(exist_ok=True)
        (self.storage_root / "archive").mkdir(exist_ok=True)
        (self.storage_root / "test_cases").mkdir(exist_ok=True)
        
        logger.info(f"ExtractionStorageService initialized with root: {self.storage_root}")
    
    def save_extraction(
        self, 
        extraction_data: CompleteExtractionResult,
        custom_retention_days: Optional[int] = None
    ) -> ExtractionStorageInfo:
        """
        Save extraction data to storage
        
        Args:
            extraction_data: Complete extraction result to save
            custom_retention_days: Override default retention period
            
        Returns:
            Storage information object
        """
        try:
            retention_days = custom_retention_days or self.default_retention_days
            
            # Generate filename
            filename = f"{extraction_data.job_id}_extraction_{extraction_data.extraction_id}.json"
            file_path = self.storage_root / "active" / filename
            
            # Serialize to JSON (Pydantic V2 compatible)
            json_data = extraction_data.model_dump_json(indent=2)
            json_bytes = json_data.encode('utf-8')
            
            # Determine if compression is needed
            size_mb = len(json_bytes) / (1024 * 1024)
            should_compress = (
                self.enable_compression and 
                size_mb > self.compression_threshold_mb
            )
            
            # Save file
            if should_compress:
                compressed_filename = filename + ".gz"
                compressed_path = self.storage_root / "active" / compressed_filename
                with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
                    f.write(json_data)
                final_path = compressed_path
                final_filename = compressed_filename
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                final_path = file_path
                final_filename = filename
            
            # Calculate retention expiration
            retention_expires_at = datetime.now() + timedelta(days=retention_days)
            
            # Create storage info
            storage_info = ExtractionStorageInfo(
                extraction_id=extraction_data.extraction_id,
                job_id=extraction_data.job_id,
                storage_path=str(final_path),
                file_size_bytes=final_path.stat().st_size,
                created_at=datetime.now(),
                retention_expires_at=retention_expires_at,
                is_compressed=should_compress
            )
            
            # Save storage metadata
            self._save_storage_metadata(storage_info)
            
            logger.info(f"Saved extraction data: {extraction_data.extraction_id} "
                       f"({size_mb:.2f}MB, compressed: {should_compress})")
            
            return storage_info
            
        except Exception as e:
            logger.error(f"Failed to save extraction data {extraction_data.extraction_id}: {e}")
            raise
    
    def load_extraction(self, job_id: str) -> Optional[CompleteExtractionResult]:
        """
        Load extraction data by job ID
        
        Args:
            job_id: Blueprint job ID
            
        Returns:
            Complete extraction result or None if not found
        """
        try:
            # Find the extraction file
            storage_info = self._find_storage_info(job_id)
            if not storage_info:
                logger.warning(f"No extraction data found for job_id: {job_id}")
                return None
            
            file_path = Path(storage_info.storage_path)
            if not file_path.exists():
                logger.error(f"Extraction file not found: {file_path}")
                return None
            
            # Update access tracking
            self._update_access_tracking(storage_info)
            
            # Load and parse file
            if storage_info.is_compressed:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    json_data = f.read()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = f.read()
            
            extraction_data = CompleteExtractionResult.model_validate_json(json_data)
            
            logger.info(f"Loaded extraction data for job_id: {job_id}")
            return extraction_data
            
        except Exception as e:
            logger.error(f"Failed to load extraction data for job_id {job_id}: {e}")
            return None
    
    def list_extractions(
        self, 
        include_expired: bool = False,
        limit: Optional[int] = None
    ) -> List[ExtractionStorageInfo]:
        """
        List stored extractions
        
        Args:
            include_expired: Include expired extractions
            limit: Maximum number of results
            
        Returns:
            List of storage info objects
        """
        try:
            storage_infos = []
            metadata_files = list((self.storage_root / "active").glob("*.metadata.json"))
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        storage_info = ExtractionStorageInfo.model_validate_json(f.read())
                    
                    # Filter expired if requested
                    if not include_expired and self._is_expired(storage_info):
                        continue
                        
                    storage_infos.append(storage_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse metadata file {metadata_file}: {e}")
                    continue
            
            # Sort by creation date (newest first)
            storage_infos.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply limit
            if limit:
                storage_infos = storage_infos[:limit]
            
            return storage_infos
            
        except Exception as e:
            logger.error(f"Failed to list extractions: {e}")
            return []
    
    def delete_extraction(self, job_id: str) -> bool:
        """
        Delete extraction data and metadata
        
        Args:
            job_id: Blueprint job ID
            
        Returns:
            True if deleted successfully
        """
        try:
            storage_info = self._find_storage_info(job_id)
            if not storage_info:
                logger.warning(f"No extraction to delete for job_id: {job_id}")
                return False
            
            # Delete data file
            file_path = Path(storage_info.storage_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete metadata file
            metadata_path = self._get_metadata_path(storage_info.extraction_id)
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Deleted extraction data for job_id: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete extraction for job_id {job_id}: {e}")
            return False
    
    def cleanup_expired(self) -> Dict[str, int]:
        """
        Clean up expired extraction data
        
        Returns:
            Cleanup statistics
        """
        try:
            stats = {"deleted": 0, "archived": 0, "errors": 0}
            
            storage_infos = self.list_extractions(include_expired=True)
            
            for storage_info in storage_infos:
                if self._is_expired(storage_info):
                    try:
                        # Archive before deletion (optional)
                        if self._should_archive(storage_info):
                            self._archive_extraction(storage_info)
                            stats["archived"] += 1
                        
                        # Delete
                        if self.delete_extraction(storage_info.job_id):
                            stats["deleted"] += 1
                        else:
                            stats["errors"] += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to cleanup extraction {storage_info.extraction_id}: {e}")
                        stats["errors"] += 1
            
            logger.info(f"Cleanup completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired extractions: {e}")
            return {"deleted": 0, "archived": 0, "errors": 1}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics"""
        try:
            stats = {
                "total_extractions": 0,
                "total_size_mb": 0.0,
                "compressed_count": 0,
                "active_count": 0,
                "expired_count": 0,
                "oldest_extraction": None,
                "newest_extraction": None
            }
            
            storage_infos = self.list_extractions(include_expired=True)
            
            for storage_info in storage_infos:
                stats["total_extractions"] += 1
                stats["total_size_mb"] += storage_info.file_size_bytes / (1024 * 1024)
                
                if storage_info.is_compressed:
                    stats["compressed_count"] += 1
                
                if self._is_expired(storage_info):
                    stats["expired_count"] += 1
                else:
                    stats["active_count"] += 1
                
                # Track oldest/newest
                if not stats["oldest_extraction"] or storage_info.created_at < stats["oldest_extraction"]:
                    stats["oldest_extraction"] = storage_info.created_at
                
                if not stats["newest_extraction"] or storage_info.created_at > stats["newest_extraction"]:
                    stats["newest_extraction"] = storage_info.created_at
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    # === Private Methods ===
    
    def _save_storage_metadata(self, storage_info: ExtractionStorageInfo):
        """Save storage metadata to a separate file"""
        metadata_path = self._get_metadata_path(storage_info.extraction_id)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(storage_info.model_dump_json(indent=2))
    
    def _get_metadata_path(self, extraction_id: str) -> Path:
        """Get path for metadata file"""
        return self.storage_root / "active" / f"{extraction_id}.metadata.json"
    
    def _find_storage_info(self, job_id: str) -> Optional[ExtractionStorageInfo]:
        """Find storage info by job_id"""
        metadata_files = list((self.storage_root / "active").glob("*.metadata.json"))
        
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    storage_info = ExtractionStorageInfo.model_validate_json(f.read())
                
                if storage_info.job_id == job_id:
                    return storage_info
                    
            except Exception as e:
                logger.warning(f"Failed to parse metadata file {metadata_file}: {e}")
                continue
        
        return None
    
    def _update_access_tracking(self, storage_info: ExtractionStorageInfo):
        """Update access tracking for storage info"""
        try:
            storage_info.last_accessed = datetime.now()
            storage_info.access_count += 1
            self._save_storage_metadata(storage_info)
        except Exception as e:
            logger.warning(f"Failed to update access tracking: {e}")
    
    def _is_expired(self, storage_info: ExtractionStorageInfo) -> bool:
        """Check if extraction data is expired"""
        if not storage_info.retention_expires_at:
            return False
        return datetime.now() > storage_info.retention_expires_at
    
    def _should_archive(self, storage_info: ExtractionStorageInfo) -> bool:
        """Determine if extraction should be archived before deletion"""
        # Archive if it's been accessed multiple times or is recent
        return (
            storage_info.access_count > 2 or
            (datetime.now() - storage_info.created_at).days < 7
        )
    
    def _archive_extraction(self, storage_info: ExtractionStorageInfo):
        """Archive extraction data before deletion"""
        try:
            source_path = Path(storage_info.storage_path)
            archive_filename = f"archived_{source_path.name}"
            archive_path = self.storage_root / "archive" / archive_filename
            
            # Move file to archive
            shutil.move(str(source_path), str(archive_path))
            
            # Update storage info
            storage_info.storage_path = str(archive_path)
            
            # Save archived metadata
            archived_metadata_path = self.storage_root / "archive" / f"{storage_info.extraction_id}.metadata.json"
            with open(archived_metadata_path, 'w', encoding='utf-8') as f:
                f.write(storage_info.model_dump_json(indent=2))
            
            logger.info(f"Archived extraction: {storage_info.extraction_id}")
            
        except Exception as e:
            logger.error(f"Failed to archive extraction {storage_info.extraction_id}: {e}")
            raise

# === Singleton Instance ===
_storage_service_instance: Optional[ExtractionStorageService] = None

def get_extraction_storage() -> ExtractionStorageService:
    """Get singleton instance of extraction storage service"""
    global _storage_service_instance
    
    if _storage_service_instance is None:
        # Get configuration from environment or use defaults
        storage_root = os.getenv("EXTRACTION_STORAGE_ROOT", "./extractions")
        compression_threshold = float(os.getenv("COMPRESSION_THRESHOLD_MB", "1.0"))
        retention_days = int(os.getenv("EXTRACTION_RETENTION_DAYS", "30"))
        enable_compression = os.getenv("ENABLE_COMPRESSION", "true").lower() == "true"
        
        _storage_service_instance = ExtractionStorageService(
            storage_root=storage_root,
            compression_threshold_mb=compression_threshold,
            default_retention_days=retention_days,
            enable_compression=enable_compression
        )
    
    return _storage_service_instance