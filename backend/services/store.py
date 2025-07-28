from typing import Dict, Optional, Any
import threading

class InMemoryJobStore:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = job_data
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)
    
    def delete_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
    
    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return self._jobs.copy()

job_store = InMemoryJobStore()