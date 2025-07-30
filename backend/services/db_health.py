"""
Database Health Check Utilities

Provides runtime checks for database connectivity and table existence
to prevent failures in production when schema changes aren't deployed.
"""

import logging
from typing import Dict, List, Optional, Set
from functools import lru_cache
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from database import SyncSessionLocal

logger = logging.getLogger(__name__)

# Cache results for performance
_table_existence_cache: Dict[str, bool] = {}


def check_database_connection() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with SyncSessionLocal() as session:
            # Simple query to test connection
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {type(e).__name__}: {str(e)}")
        return False


def check_table_exists(table_name: str, use_cache: bool = True) -> bool:
    """
    Check if a specific table exists in the database.
    
    Args:
        table_name: Name of table to check
        use_cache: Whether to use cached results
        
    Returns:
        True if table exists, False otherwise
    """
    # Check cache first
    if use_cache and table_name in _table_existence_cache:
        return _table_existence_cache[table_name]
    
    try:
        with SyncSessionLocal() as session:
            # PostgreSQL specific query to check table existence
            result = session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """),
                {"table_name": table_name}
            )
            exists = result.scalar()
            
            # Cache the result
            _table_existence_cache[table_name] = exists
            
            if not exists:
                logger.warning(f"Table '{table_name}' does not exist in database")
            
            return exists
            
    except Exception as e:
        logger.error(f"Table existence check failed for '{table_name}': {type(e).__name__}: {str(e)}")
        # Conservative approach: assume table doesn't exist if we can't check
        _table_existence_cache[table_name] = False
        return False


def check_audit_tables_exist() -> bool:
    """
    Check if all audit-related tables exist.
    
    Returns:
        True if all audit tables exist, False otherwise
    """
    required_tables = [
        'calculation_audits',
        'room_calculation_details',
        'data_source_metadata',
        'compliance_checks'
    ]
    
    all_exist = True
    for table in required_tables:
        if not check_table_exists(table):
            all_exist = False
            
    return all_exist


def get_missing_tables() -> List[str]:
    """
    Get list of expected tables that are missing from database.
    
    Returns:
        List of missing table names
    """
    expected_tables = [
        # Core tables
        'projects',
        'users',
        'email_verification_tokens',
        
        # Audit tables
        'calculation_audits',
        'room_calculation_details', 
        'data_source_metadata',
        'compliance_checks'
    ]
    
    missing = []
    for table in expected_tables:
        if not check_table_exists(table):
            missing.append(table)
            
    return missing


def clear_table_cache(table_name: Optional[str] = None):
    """
    Clear cached table existence results.
    
    Args:
        table_name: Specific table to clear, or None to clear all
    """
    if table_name:
        _table_existence_cache.pop(table_name, None)
    else:
        _table_existence_cache.clear()


@lru_cache(maxsize=1)
def get_database_info() -> Dict[str, any]:
    """
    Get database connection info and status.
    
    Returns:
        Dictionary with database information
    """
    info = {
        'connected': False,
        'database_name': None,
        'server_version': None,
        'audit_tables_ready': False,
        'missing_tables': []
    }
    
    try:
        with SyncSessionLocal() as session:
            # Get database name
            result = session.execute(text("SELECT current_database()"))
            info['database_name'] = result.scalar()
            
            # Get PostgreSQL version
            result = session.execute(text("SELECT version()"))
            info['server_version'] = result.scalar()
            
            info['connected'] = True
            
    except Exception as e:
        logger.error(f"Failed to get database info: {type(e).__name__}: {str(e)}")
    
    # Check for missing tables
    info['missing_tables'] = get_missing_tables()
    info['audit_tables_ready'] = check_audit_tables_exist()
    
    return info


def log_database_health():
    """Log current database health status."""
    info = get_database_info()
    
    if info['connected']:
        logger.info(f"Database connected: {info['database_name']}")
        logger.info(f"PostgreSQL version: {info['server_version']}")
        
        if info['missing_tables']:
            logger.warning(f"Missing tables: {', '.join(info['missing_tables'])}")
            logger.warning("Run 'alembic upgrade head' to create missing tables")
        else:
            logger.info("All expected tables exist")
            
        if not info['audit_tables_ready']:
            logger.warning("Audit tables not ready - audit logging will use file fallback")
    else:
        logger.error("Database connection failed - all features requiring database will be unavailable")


# Module initialization: log health status
log_database_health()

# Export commonly used checks as module-level constants
AUDIT_TABLES_EXIST = check_audit_tables_exist()
DATABASE_CONNECTED = check_database_connection()