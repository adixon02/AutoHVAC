"""
Pipeline Context - Single source of truth for pipeline state
Ensures consistency across all stages by locking critical values
"""

import logging
from typing import Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """
    Thread-safe context that maintains pipeline state.
    Once values are set, they cannot be changed to prevent conflicts.
    """
    
    def __init__(self):
        self.selected_page: Optional[int] = None
        self.scale_px_per_ft: Optional[float] = None
        self.pdf_path: Optional[str] = None
        self.zip_code: Optional[str] = None
        self.project_id: Optional[str] = None
        self._lock = Lock()
        
    def set_page(self, page_num: int, source: str = "unknown") -> None:
        """
        Set the selected page number (0-indexed).
        Raises error if already set to a different value.
        """
        with self._lock:
            if self.selected_page is not None and self.selected_page != page_num:
                from services.error_types import NeedsInputError
                raise NeedsInputError(
                    input_type='plan_quality',
                    message=f"Page selection conflict! Already using page {self.selected_page + 1}, "
                            f"attempted to use page {page_num + 1}",
                    details={
                        'current_page': self.selected_page + 1,
                        'attempted_page': page_num + 1,
                        'source': source,
                        'recommendation': 'Internal error - please report this issue'
                    }
                )
            
            if self.selected_page is None:
                self.selected_page = page_num
                logger.info(f"[CONTEXT] Locked page selection: {page_num} (0-indexed) from {source}")
    
    def get_page(self) -> int:
        """Get the selected page, raising error if not set."""
        with self._lock:
            if self.selected_page is None:
                raise ValueError("Page not set in context! Call set_page() first.")
            return self.selected_page
    
    def set_scale(self, px_per_ft: float, source: str = "unknown") -> None:
        """
        Set the scale factor.
        Raises error if already set to a different value.
        """
        with self._lock:
            if self.scale_px_per_ft is not None and abs(self.scale_px_per_ft - px_per_ft) > 1.0:
                from services.error_types import NeedsInputError
                raise NeedsInputError(
                    input_type='scale',
                    message=f"Scale conflict! Already using {self.scale_px_per_ft:.1f} px/ft, "
                            f"attempted to use {px_per_ft:.1f} px/ft",
                    details={
                        'current_scale': self.scale_px_per_ft,
                        'attempted_scale': px_per_ft,
                        'source': source,
                        'recommendation': 'Use SCALE_OVERRIDE to force a specific scale'
                    }
                )
            
            if self.scale_px_per_ft is None:
                self.scale_px_per_ft = px_per_ft
                logger.info(f"[CONTEXT] Locked scale: {px_per_ft:.1f} px/ft from {source}")
    
    def get_scale(self) -> float:
        """Get the scale factor, raising error if not set."""
        with self._lock:
            if self.scale_px_per_ft is None:
                raise ValueError("Scale not set in context! Call set_scale() first.")
            return self.scale_px_per_ft
    
    def set_pdf_path(self, pdf_path: str) -> None:
        """Set the PDF path being processed."""
        with self._lock:
            self.pdf_path = pdf_path
            logger.info(f"[CONTEXT] Set PDF path: {pdf_path}")
    
    def set_project_info(self, project_id: str, zip_code: str) -> None:
        """Set project information."""
        with self._lock:
            self.project_id = project_id
            self.zip_code = zip_code
            logger.info(f"[CONTEXT] Set project: {project_id}, ZIP: {zip_code}")
    
    def reset(self) -> None:
        """Reset context for new pipeline run."""
        with self._lock:
            self.selected_page = None
            self.scale_px_per_ft = None
            self.pdf_path = None
            self.zip_code = None
            self.project_id = None
            logger.info("[CONTEXT] Context reset")
    
    def summary(self) -> dict:
        """Get current context state."""
        with self._lock:
            return {
                'selected_page': self.selected_page,
                'scale_px_per_ft': self.scale_px_per_ft,
                'pdf_path': self.pdf_path,
                'zip_code': self.zip_code,
                'project_id': self.project_id
            }


# Global singleton instance
pipeline_context = PipelineContext()