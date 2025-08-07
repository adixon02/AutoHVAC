"""
JSON serialization utilities for handling UUID and other non-serializable types
"""

import json
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict
from enum import Enum
import logging
from dataclasses import is_dataclass, asdict
import base64

# Optional imports for special type handling
try:
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - numpy may not be installed
    _np = None  # type: ignore

try:
    import fitz as _fitz  # PyMuPDF  # type: ignore
except Exception:  # pragma: no cover - PyMuPDF may not be available in some contexts
    _fitz = None  # type: ignore

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID and other common non-serializable types"""
    
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, Enum):
            # Return the enum's value, not its dict representation
            return obj.value
        # NumPy scalars and arrays
        elif _np is not None and isinstance(obj, (_np.generic,)):
            return obj.item()
        elif _np is not None and isinstance(obj, _np.ndarray):
            return obj.tolist()
        # Dataclasses
        elif is_dataclass(obj):
            return asdict(obj)
        # Sets
        elif isinstance(obj, set):
            return list(obj)
        # Bytes
        elif isinstance(obj, (bytes, bytearray)):
            return base64.b64encode(bytes(obj)).decode('ascii')
        # PyMuPDF types
        elif _fitz is not None:
            try:
                if isinstance(obj, _fitz.Point):
                    return [float(obj.x), float(obj.y)]
            except Exception:
                pass
            try:
                if isinstance(obj, _fitz.Rect):
                    return [float(obj.x0), float(obj.y0), float(obj.x1), float(obj.y1)]
            except Exception:
                pass
        elif hasattr(obj, '__dict__'):
            # For objects with __dict__, try to serialize their attributes
            return obj.__dict__
        return super().default(obj)


def safe_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert a Pydantic model or any object to a dict with UUID handling.
    
    Args:
        obj: The object to convert (Pydantic model, dict, or other)
        
    Returns:
        Dictionary with all UUIDs converted to strings
    """
    if hasattr(obj, 'dict'):
        # Pydantic model with dict method - avoid using obj.json() to bypass pydantic's
        # strict serializer for unknown types; instead, dump the dict through our encoder
        try:
            raw = obj.dict()
        except Exception:
            # Pydantic v2
            try:
                raw = obj.model_dump()  # type: ignore[attr-defined]
            except Exception:
                raw = getattr(obj, '__dict__', {})
        return ensure_json_serializable(raw)
    elif isinstance(obj, dict):
        # Already a dict, but may contain UUIDs
        return ensure_json_serializable(obj)
    elif is_dataclass(obj):
        return ensure_json_serializable(asdict(obj))
    else:
        # Try to convert to dict
        try:
            return ensure_json_serializable(obj)
        except Exception as e:
            logger.error(f"Failed to safely convert object to dict: {e}")
            return {}


def ensure_json_serializable(data: Any) -> Any:
    """
    Recursively ensure all data is JSON serializable.
    
    Args:
        data: The data to process
        
    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, UUID):
        return str(data)
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, Enum):
        # Return the enum's value, not its dict representation
        return data.value
    # PyMuPDF types
    elif _fitz is not None:
        try:
            if isinstance(data, _fitz.Point):
                return [float(data.x), float(data.y)]
        except Exception:
            pass
        try:
            if isinstance(data, _fitz.Rect):
                return [float(data.x0), float(data.y0), float(data.x1), float(data.y1)]
        except Exception:
            pass
    # NumPy types
    if _np is not None and isinstance(data, (_np.generic,)):
        return data.item()
    if _np is not None and isinstance(data, _np.ndarray):
        return [ensure_json_serializable(item) for item in data.tolist()]
    elif isinstance(data, dict):
        # Skip the problematic __objclass__ and other internal attributes
        if '_value_' in data and '_name_' in data and '__objclass__' in data:
            # This looks like an enum that was converted to dict - extract just the value
            logger.warning(f"Found enum dict representation, extracting value: {data.get('_value_')}")
            return data.get('_value_')
        return {k: ensure_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, tuple):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, set):
        return [ensure_json_serializable(item) for item in data]
    elif is_dataclass(data):
        return ensure_json_serializable(asdict(data))
    elif isinstance(data, (bytes, bytearray)):
        return base64.b64encode(bytes(data)).decode('ascii')
    elif hasattr(data, 'dict'):
        # Pydantic model
        try:
            return ensure_json_serializable(data.dict())
        except Exception:
            try:
                return ensure_json_serializable(data.model_dump())  # type: ignore[attr-defined]
            except Exception:
                return ensure_json_serializable(getattr(data, '__dict__', {}))
    elif hasattr(data, '__dict__'):
        # Regular object - but check if it's an Enum first
        if isinstance(data, Enum):
            return data.value
        return ensure_json_serializable(data.__dict__)
    else:
        return data