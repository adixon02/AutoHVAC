#!/usr/bin/env python3
"""
Fix missing database tables
Creates email_verification_tokens table if it doesn't exist
"""

import os
import asyncio
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_missing_tables():
    """Create email_verification_tokens table if missing"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS email_verification_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        token VARCHAR(255) NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        used BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_email_tokens_user_id ON email_verification_tokens(user_id);
    CREATE INDEX IF NOT EXISTS idx_email_tokens_token ON email_verification_tokens(token);
    CREATE INDEX IF NOT EXISTS idx_email_tokens_expires ON email_verification_tokens(expires_at);
    """
    
    try:
        async with engine.begin() as conn:
            # Check if table exists
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'email_verification_tokens'
                    )
                """)
            )
            exists = result.scalar()
            
            if not exists:
                logger.info("Creating email_verification_tokens table...")
                await conn.execute(text(create_table_sql))
                logger.info("Table created successfully!")
            else:
                logger.info("Table email_verification_tokens already exists")
                
            # Verify table structure
            result = await conn.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns
                    WHERE table_name = 'email_verification_tokens'
                    ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            
            logger.info("Table structure:")
            for col_name, col_type in columns:
                logger.info(f"  - {col_name}: {col_type}")
                
        return True
        
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        return False

async def main():
    """Main function"""
    success = await create_missing_tables()
    
    if success:
        logger.info("Database fix completed successfully!")
    else:
        logger.error("Database fix failed!")
        
    await engine.dispose()
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)