"""
Artifact Manager
Manages versioned saving of processing artifacts for debugging and analysis
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import pickle
import gzip

logger = logging.getLogger(__name__)


class ArtifactManager:
    """
    Manages versioned artifacts from blueprint processing pipeline
    Saves intermediate results for debugging and recovery
    """
    
    def __init__(self, base_dir: str = "/tmp/autohvac_artifacts"):
        """
        Initialize artifact manager
        
        Args:
            base_dir: Base directory for artifact storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Artifact types and their formats
        self.artifact_types = {
            'vector_data': 'pickle',  # Binary data
            'scale_result': 'json',
            'north_arrow': 'json',
            'room_graph': 'pickle',  # NetworkX graph
            'geometry_raw': 'json',
            'text_raw': 'json',
            'gpt_response': 'json',
            'blueprint_schema': 'json',
            'manualj_results': 'json',
            'error_log': 'json'
        }
        
        self.current_session = None
        self.artifacts = {}
    
    def start_session(self, project_id: str, job_id: str) -> str:
        """
        Start a new artifact collection session
        
        Args:
            project_id: Project identifier
            job_id: Job identifier
            
        Returns:
            Session ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = f"{project_id}_{job_id}_{timestamp}"
        
        # Create session directory
        session_dir = self.base_dir / self.current_session
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize session manifest
        manifest = {
            'session_id': self.current_session,
            'project_id': project_id,
            'job_id': job_id,
            'start_time': datetime.now().isoformat(),
            'artifacts': {}
        }
        
        self._save_manifest(manifest)
        logger.info(f"Started artifact session: {self.current_session}")
        
        return self.current_session
    
    def save_artifact(
        self,
        artifact_type: str,
        data: Any,
        version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save an artifact with optional versioning
        
        Args:
            artifact_type: Type of artifact (e.g., 'scale_result')
            data: Data to save
            version: Optional version number (auto-incremented if None)
            metadata: Optional metadata about the artifact
            
        Returns:
            Path to saved artifact
        """
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        # Determine version
        if version is None:
            version = self._get_next_version(artifact_type)
        
        # Create artifact filename
        filename = f"{artifact_type}_v{version:03d}"
        
        # Determine format
        format_type = self.artifact_types.get(artifact_type, 'json')
        
        # Save based on format
        session_dir = self.base_dir / self.current_session
        
        if format_type == 'json':
            filepath = session_dir / f"{filename}.json"
            self._save_json(filepath, data)
        elif format_type == 'pickle':
            filepath = session_dir / f"{filename}.pkl.gz"
            self._save_pickle(filepath, data)
        else:
            filepath = session_dir / f"{filename}.txt"
            self._save_text(filepath, str(data))
        
        # Update manifest
        self._update_manifest(artifact_type, version, str(filepath), metadata)
        
        # Store in memory for quick access
        if artifact_type not in self.artifacts:
            self.artifacts[artifact_type] = {}
        self.artifacts[artifact_type][version] = data
        
        logger.debug(f"Saved artifact: {artifact_type} v{version} to {filepath}")
        
        return str(filepath)
    
    def get_artifact(
        self,
        artifact_type: str,
        version: Optional[int] = None
    ) -> Optional[Any]:
        """
        Retrieve an artifact
        
        Args:
            artifact_type: Type of artifact
            version: Version to retrieve (latest if None)
            
        Returns:
            Artifact data or None if not found
        """
        # Check memory cache first
        if artifact_type in self.artifacts:
            if version is None:
                # Get latest version
                if self.artifacts[artifact_type]:
                    version = max(self.artifacts[artifact_type].keys())
            
            if version in self.artifacts[artifact_type]:
                return self.artifacts[artifact_type][version]
        
        # Load from disk if not in memory
        if not self.current_session:
            return None
        
        manifest = self._load_manifest()
        if not manifest or artifact_type not in manifest.get('artifacts', {}):
            return None
        
        artifact_info = manifest['artifacts'][artifact_type]
        
        if version is None:
            # Get latest version
            version = max(artifact_info.keys()) if artifact_info else None
        
        if version is None or str(version) not in artifact_info:
            return None
        
        filepath = artifact_info[str(version)]['path']
        
        # Load based on format
        format_type = self.artifact_types.get(artifact_type, 'json')
        
        try:
            if format_type == 'json':
                return self._load_json(filepath)
            elif format_type == 'pickle':
                return self._load_pickle(filepath)
            else:
                return self._load_text(filepath)
        except Exception as e:
            logger.error(f"Failed to load artifact {artifact_type} v{version}: {e}")
            return None
    
    def save_checkpoint(self, stage: str, data: Dict[str, Any]) -> None:
        """
        Save a pipeline checkpoint for recovery
        
        Args:
            stage: Pipeline stage name
            data: Checkpoint data
        """
        checkpoint = {
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self.save_artifact(
            f'checkpoint_{stage}',
            checkpoint,
            metadata={'stage': stage}
        )
    
    def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint"""
        manifest = self._load_manifest()
        if not manifest:
            return None
        
        # Find all checkpoint artifacts
        checkpoints = []
        for artifact_type, versions in manifest.get('artifacts', {}).items():
            if artifact_type.startswith('checkpoint_'):
                for version, info in versions.items():
                    checkpoints.append({
                        'type': artifact_type,
                        'version': int(version),
                        'timestamp': info.get('timestamp', ''),
                        'stage': info.get('metadata', {}).get('stage', '')
                    })
        
        if not checkpoints:
            return None
        
        # Sort by timestamp and get latest
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        latest = checkpoints[0]
        
        return self.get_artifact(latest['type'], latest['version'])
    
    def list_artifacts(self) -> Dict[str, List[int]]:
        """List all artifacts in current session"""
        manifest = self._load_manifest()
        if not manifest:
            return {}
        
        result = {}
        for artifact_type, versions in manifest.get('artifacts', {}).items():
            result[artifact_type] = sorted([int(v) for v in versions.keys()])
        
        return result
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        manifest = self._load_manifest()
        if not manifest:
            return {}
        
        artifact_count = sum(
            len(versions) 
            for versions in manifest.get('artifacts', {}).values()
        )
        
        return {
            'session_id': self.current_session,
            'project_id': manifest.get('project_id'),
            'job_id': manifest.get('job_id'),
            'start_time': manifest.get('start_time'),
            'artifact_count': artifact_count,
            'artifact_types': list(manifest.get('artifacts', {}).keys())
        }
    
    def cleanup_old_sessions(self, keep_days: int = 7) -> int:
        """
        Clean up old artifact sessions
        
        Args:
            keep_days: Number of days to keep artifacts
            
        Returns:
            Number of sessions cleaned up
        """
        import shutil
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cleaned = 0
        
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            # Check session age
            try:
                # Parse timestamp from directory name
                parts = session_dir.name.split('_')
                if len(parts) >= 3:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    session_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if session_date < cutoff_date:
                        shutil.rmtree(session_dir)
                        cleaned += 1
                        logger.info(f"Cleaned up old session: {session_dir.name}")
            except Exception as e:
                logger.warning(f"Failed to clean session {session_dir.name}: {e}")
        
        return cleaned
    
    # Private helper methods
    
    def _get_next_version(self, artifact_type: str) -> int:
        """Get next version number for artifact type"""
        manifest = self._load_manifest()
        if not manifest:
            return 1
        
        artifacts = manifest.get('artifacts', {})
        if artifact_type not in artifacts:
            return 1
        
        versions = [int(v) for v in artifacts[artifact_type].keys()]
        return max(versions) + 1 if versions else 1
    
    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save session manifest"""
        if not self.current_session:
            return
        
        manifest_path = self.base_dir / self.current_session / "manifest.json"
        self._save_json(manifest_path, manifest)
    
    def _load_manifest(self) -> Optional[Dict[str, Any]]:
        """Load session manifest"""
        if not self.current_session:
            return None
        
        manifest_path = self.base_dir / self.current_session / "manifest.json"
        if not manifest_path.exists():
            return None
        
        return self._load_json(manifest_path)
    
    def _update_manifest(
        self,
        artifact_type: str,
        version: int,
        filepath: str,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Update manifest with new artifact"""
        manifest = self._load_manifest()
        if not manifest:
            return
        
        if 'artifacts' not in manifest:
            manifest['artifacts'] = {}
        
        if artifact_type not in manifest['artifacts']:
            manifest['artifacts'][artifact_type] = {}
        
        manifest['artifacts'][artifact_type][str(version)] = {
            'path': filepath,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self._save_manifest(manifest)
    
    def _save_json(self, filepath: Path, data: Any) -> None:
        """Save data as JSON"""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_json(self, filepath: str) -> Any:
        """Load JSON data"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _save_pickle(self, filepath: Path, data: Any) -> None:
        """Save data as compressed pickle"""
        with gzip.open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def _load_pickle(self, filepath: str) -> Any:
        """Load compressed pickle data"""
        with gzip.open(filepath, 'rb') as f:
            return pickle.load(f)
    
    def _save_text(self, filepath: Path, data: str) -> None:
        """Save text data"""
        with open(filepath, 'w') as f:
            f.write(data)
    
    def _load_text(self, filepath: str) -> str:
        """Load text data"""
        with open(filepath, 'r') as f:
            return f.read()


# Singleton instance
_artifact_manager = None

def get_artifact_manager() -> ArtifactManager:
    """Get or create the global artifact manager"""
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager()
    return _artifact_manager