"""
JSON serialization utilities for handling UUID and other non-serializable types
"""

import json
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict
import logging

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
        # Pydantic model with dict method
        if hasattr(obj, 'Config') and hasattr(obj.Config, 'json_encoders'):
            # Use the model's json_encoders if available
            return json.loads(obj.json())
        else:
            # Fallback to manual conversion
            return json.loads(json.dumps(obj.dict(), cls=SafeJSONEncoder))
    elif isinstance(obj, dict):
        # Already a dict, but may contain UUIDs
        return json.loads(json.dumps(obj, cls=SafeJSONEncoder))
    else:
        # Try to convert to dict
        try:
            return json.loads(json.dumps(obj, cls=SafeJSONEncoder))
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
    elif isinstance(data, dict):
        return {k: ensure_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, tuple):
        return [ensure_json_serializable(item) for item in data]
    elif hasattr(data, 'dict'):
        # Pydantic model
        return ensure_json_serializable(data.dict())
    elif hasattr(data, '__dict__'):
        # Regular object
        return ensure_json_serializable(data.__dict__)
    else:
        return data