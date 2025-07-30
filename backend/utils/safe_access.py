"""
Safe Access Utilities for Defensive Programming

Provides safe methods to access object attributes and perform operations
that might fail due to None values or missing attributes.
"""

import logging
from typing import Any, Optional, Callable, TypeVar, Union, List, Dict

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_getattr(obj: Any, attr: str, default: T = None) -> T:
    """
    Safely get attribute from object with default value.
    
    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if attribute doesn't exist or obj is None
        
    Returns:
        Attribute value or default
    """
    if obj is None:
        return default
    try:
        return getattr(obj, attr, default)
    except Exception as e:
        logger.debug(f"safe_getattr failed for {attr}: {type(e).__name__}")
        return default


def safe_len(obj: Any, default: int = 0) -> int:
    """
    Safely get length of object with default value.
    
    Args:
        obj: Object to get length of
        default: Default value if len() fails or obj is None
        
    Returns:
        Length of object or default
    """
    if obj is None:
        return default
    try:
        return len(obj)
    except Exception as e:
        logger.debug(f"safe_len failed: {type(e).__name__}")
        return default


def safe_get(obj: Union[Dict, Any], key: str, default: T = None) -> T:
    """
    Safely get value from dict or object attribute.
    
    Works with both dictionary keys and object attributes.
    
    Args:
        obj: Dictionary or object
        key: Key or attribute name
        default: Default value if not found
        
    Returns:
        Value or default
    """
    if obj is None:
        return default
    
    # Try dictionary access first
    if isinstance(obj, dict):
        return obj.get(key, default)
    
    # Fall back to attribute access
    return safe_getattr(obj, key, default)


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Float value or default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"safe_float conversion failed for {value}: {type(e).__name__}")
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Int value or default
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"safe_int conversion failed for {value}: {type(e).__name__}")
        return default


def safe_call(func: Callable[..., T], *args, default: T = None, **kwargs) -> T:
    """
    Safely call a function with default return value on failure.
    
    Args:
        func: Function to call
        *args: Positional arguments
        default: Default return value if function fails
        **kwargs: Keyword arguments
        
    Returns:
        Function result or default
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.debug(f"safe_call failed for {func.__name__}: {type(e).__name__}: {str(e)}")
        return default


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers with zero check.
    
    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Default if division by zero or error
        
    Returns:
        Division result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception as e:
        logger.debug(f"safe_divide failed: {type(e).__name__}")
        return default


def safe_chain_getattr(obj: Any, attr_chain: str, default: T = None) -> T:
    """
    Safely get nested attributes using dot notation.
    
    Example: safe_chain_getattr(obj, 'schema.rooms.0.name', 'Unknown')
    
    Args:
        obj: Root object
        attr_chain: Dot-separated attribute path
        default: Default if any part of chain fails
        
    Returns:
        Nested attribute value or default
    """
    if obj is None:
        return default
    
    try:
        attrs = attr_chain.split('.')
        current = obj
        
        for attr in attrs:
            # Handle list/array indexing
            if attr.isdigit():
                if hasattr(current, '__getitem__'):
                    current = current[int(attr)]
                else:
                    return default
            else:
                current = getattr(current, attr)
            
            if current is None:
                return default
                
        return current
    except Exception as e:
        logger.debug(f"safe_chain_getattr failed for {attr_chain}: {type(e).__name__}")
        return default


def ensure_list(obj: Any) -> List[Any]:
    """
    Ensure object is a list, converting if necessary.
    
    Args:
        obj: Object to ensure is a list
        
    Returns:
        List version of object
    """
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, dict)):
        return list(obj)
    return [obj]


def ensure_dict(obj: Any) -> Dict[str, Any]:
    """
    Ensure object is a dict, converting if necessary.
    
    Args:
        obj: Object to ensure is a dict
        
    Returns:
        Dict version of object
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return {}